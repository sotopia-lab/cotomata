import asyncio
import logging
import time
import os
import sys
from typing import Any, AsyncIterator, Optional

from rich.logging import RichHandler
from dotenv import load_dotenv  # Import the load_dotenv function

from aact import Message, NodeFactory, Node
from aact.messages import Text, DataModel
from aact.messages.commons import DataEntry

from aact_openhands.utils import AgentAction, ActionType

from openhands.core.config import AgentConfig, AppConfig, SandboxConfig
from openhands.core.logger import openhands_logger as logger
from openhands.core.main import create_runtime
from openhands.events.action import (
    BrowseURLAction,
    CmdRunAction,
    FileWriteAction,
    FileReadAction,
    BrowseInteractiveAction,
)
from openhands.runtime.base import Runtime
from openhands.utils.async_utils import call_async_from_sync

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

BASE_CONTAINER_IMAGE = "docker.all-hands.dev/all-hands-ai/runtime:0.14-nikolaik"

load_dotenv()

# Configuration for logging
FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
logging.basicConfig(
    level=logging.WARNING,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler()],
)


@NodeFactory.register("openhands")
class OpenHands(Node[DataModel, Text]):
    def __init__(
        self,
        input_channels: list[str],
        output_channels: list[str],
        modal_session_id: str,
        redis_url: str,
    ):
        super().__init__(
            input_channel_types=[
                (input_channel, AgentAction) for input_channel in input_channels
            ],
            output_channel_types=[
                (output_channel, Text) for output_channel in output_channels
            ],
            redis_url=redis_url,
        )
        self.queue: asyncio.Queue[DataEntry[DataModel]] = asyncio.Queue()
        self.task: asyncio.Task[None] | None = None
        self.runtime: Optional[Runtime] = None
        self.modal_session_id: str = modal_session_id

    async def init_runtime(self) -> None:
        """
        Initializes the runtime environment with the specified configuration.
        """
        start_time = time.time()
        modal_api_token_id = os.getenv("MODAL_API_TOKEN_ID", "")
        modal_api_token_secret = os.getenv("MODAL_API_TOKEN_SECRET", "")
        allhands_api_key = os.getenv("ALLHANDS_API_KEY", None)
        sandbox_remote_runtime_api_url = os.getenv("SANDBOX_REMOTE_RUNTIME_API_URL", "")
        
        if not modal_api_token_id or not modal_api_token_secret:
            logger.warning("Modal API tokens are not set. Check environment variables.")
        
        try:
            config = AppConfig(
                default_agent="CodeActAgent",
                run_as_openhands=False,
                max_iterations=3,
                runtime="modal",
                modal_api_token_id=modal_api_token_id,
                modal_api_token_secret=modal_api_token_secret,
                modal_session_id=self.modal_session_id,
                sandbox=SandboxConfig(
                    base_container_image=BASE_CONTAINER_IMAGE,
                    enable_auto_lint=True,
                    use_host_network=False,
                    timeout=50,
                    platform="linux/amd64",
                    api_key=allhands_api_key,
                    remote_runtime_api_url=sandbox_remote_runtime_api_url,
                    keep_runtime_alive=False,
                ),
                workspace_base=None,
                workspace_mount_path=None,
            )
        except Exception as e:
            logger.error(f"Error creating AppConfig: {e}")

        agent_config = AgentConfig(
            codeact_enable_jupyter=True,
            codeact_enable_browsing=True,
            codeact_enable_llm_editor=True,
        )
        config.set_agent_config(agent_config)

        self.runtime = create_runtime(config)
        if self.runtime:
            try:
                call_async_from_sync(self.runtime.connect)
            except Exception as e:
                logger.error(f"Error connecting to runtime: {e}")
            logger.info("-" * 20)
            logger.info("RUNTIME CONNECTED")
            logger.info("-" * 20)
        else:
            logger.error("Failed to initialize runtime.")
        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time
        logger.info(f"Runtime initialization took {elapsed_time:.2f} seconds.")

    async def __aenter__(self) -> Self:
        self.runtime_init_task = asyncio.create_task(self.init_runtime())
        self.task = asyncio.create_task(self.run_action())
        return await super().__aenter__()

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.runtime:
            self.runtime.close()
        return await super().__aexit__(exc_type, exc_value, traceback)

    async def aact(self, action: AgentAction) -> Optional[Text]:
        """
        Executes an action based on the observation and returns the result as Text.

        Args:
            observation (AgentAction): The action to be executed.

        Returns:
            Optional[Text]: The result of the action, or None if the 
            runtime is not available.
        """
        if not self.runtime:
            logger.warning("Runtime is not initialized.")
            return None

        try:
            action_obj = self._create_action(action)
            logger.info(f"Executing action: {action}", extra={"msg_type": "ACTION"})
            obs = self.runtime.run_action(action_obj)
            logger.info(
                f"Received observation: {str(obs).splitlines()[:10]}",
                extra={"msg_type": "OBSERVATION"},
            )
            return Text(text=str(obs)) # type: ignore[call-arg]
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return None

    def _create_action(self, observation: AgentAction) -> Any:
        """
        Creates an action based on the observation's action type.

        Args:
            observation (AgentAction): The observation containing the action 
            type and arguments.

        Returns:
            Any: The created action.
        """
        action_type = observation.action_type
        argument = observation.argument
        path = observation.path

        if action_type == ActionType.BROWSE:
            return BrowseURLAction(url=argument)
        elif action_type == ActionType.BROWSE_ACTION:
            return BrowseInteractiveAction(browser_actions=argument)
        elif action_type == ActionType.RUN:
            return CmdRunAction(command=argument)
        elif action_type == ActionType.WRITE:
            if path is None:
                raise ValueError("Path cannot be None for WRITE action")
            return FileWriteAction(path=path, content=argument)
        elif action_type == ActionType.READ:
            if path is None:
                raise ValueError("Path cannot be None for READ action")
            return FileReadAction(path=path)
        else:
            raise ValueError(f"Unsupported action type: {action_type}")

    async def send(self, action: Text) -> None:
        """
        Sends the action to all output channels.

        Args:
            action (Text): The action to be sent.
        """
        try:
            for output_channel, _ in self.output_channel_types.items():
                message = Message[Text](data=action).model_dump_json()
                await self.r.publish(output_channel, message)
        except Exception as e:
            logger.error(f"Error sending action: {e}")

    async def run_action(self) -> None:
        """
        Continuously processes actions from the queue.
        """
        while self.task:
            try:
                data_entry = await self.queue.get()
                if isinstance(data_entry.data, AgentAction):
                    obs = await self.aact(data_entry.data)
                    if obs is not None:
                        await self.send(obs)
                else:
                    logger.error("Data is not of type AgentAction")
                self.queue.task_done()
            except Exception as e:
                logger.error(f"Error processing action: {e}")

    async def event_handler(
        self, input_channel: str, input_message: Message[DataModel]
    ) -> AsyncIterator[tuple[str, Message[Text]]]:
        """
        Handles incoming events and adds them to the processing queue.

        Args:
            input_channel (str): The channel from which the message was received.
            input_message (Message[DataModel]): The incoming message.

        Yields:
            Tuple[str, Message[Zero]]: A tuple containing the channel 
            and a zero message if the channel is not recognized.
        """
        try:
            if input_channel in self.input_channel_types:
                # Create a DataEntry instance with the correct type
                data_entry: DataEntry[DataModel] = DataEntry(
                    channel=input_channel, data=input_message.data
                )
                await self.queue.put(data_entry)
            else:
                logger.warning(f"Unrecognized input channel: {input_channel}")
                yield input_channel, \
                    Message[Text](data=Text(text="")) #type:ignore[call-arg]
        except Exception as e:
            logger.error(f"Error handling event: {e}")
            
            
#poetry run aact run-dataflow examples/openhands_node.toml
