import logging
import os
import re
from typing import TypeVar, Any, cast, Callable, ParamSpec

import gin  # type: ignore[import-untyped]
from beartype import beartype
from beartype.typing import Type
from openai import OpenAI

from langchain_core.runnables.base import RunnableSerializable
from langchain_core.messages.base import BaseMessage
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
)
from langchain_core.prompt_values import ChatPromptValue
from langchain.schema import BaseOutputParser, OutputParserException
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from pydantic import BaseModel, Field
from pydantic.v1 import SecretStr
from rich import print
from typing_extensions import Literal

from sotopia.database import EnvironmentProfile, RelationshipProfile
from sotopia.messages import ActionType, AgentAction, ScriptBackground
from sotopia.messages.message_classes import (
    ScriptInteraction,
    ScriptInteractionReturnType,
)
from sotopia.utils import format_docstring

from sotopia.generation_utils.langchain_callback_handler import LoggingCallbackHandler

from dotenv import load_dotenv
load_dotenv()

log = logging.getLogger("generate")
logging_handler = LoggingCallbackHandler("langchain")

LLM_Name = Literal[
    "together_ai/meta-llama/Llama-2-7b-chat-hf",
    "together_ai/meta-llama/Llama-2-70b-chat-hf",
    "together_ai/mistralai/Mixtral-8x22B-Instruct-v0.1",
    "together_ai/meta-llama/Llama-3-8b-chat-hf",
    "together_ai/meta-llama/Llama-3-70b-chat-hf",
    "together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
    "gpt-4o-mini",
    "gpt-3.5-turbo-16k-0613",
    "gpt-3.5-turbo-finetuned",
    "gpt-3.5-turbo-ft-MF",
    "gpt-4",
    "gpt-4-turbo-2024-04-09",
    "gpt-4o-2024-08-06",
    "gpt-4o-mini-2024-07-18",
    "human",
    "redis",
    "groq/llama3-70b-8192",
]
# subject to future OpenAI changes
DEFAULT_BAD_OUTPUT_PROCESS_MODEL = "gpt-4o-mini"

OutputType = TypeVar("OutputType", bound=object)

DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])
P = ParamSpec("P")
T = TypeVar("T")

def gin_configurable(f: Callable[P, T]) -> Callable[P, T]:
    """Type-annotated wrapper for gin.configurable"""
    decorated = gin.configurable(f)
    return cast(Callable[P, T], decorated)


class EnvResponse(BaseModel):
    reasoning: str = Field(
        description="first reiterate agents' social goals and then reason about what agents say/do and whether that aligns with their goals."
    )
    p1_rate: int = Field(description="rating of participant 1, on the scale of 0 to 9")
    p2_rate: int = Field(description="rating of participant 2, on the scale of 0 to 9")


class EnvResponsePydanticOutputParser(PydanticOutputParser[EnvResponse]):
    def __init__(self, pydantic_object: Type[EnvResponse] = EnvResponse) -> None:
        super(EnvResponsePydanticOutputParser, self).__init__(
            pydantic_object=pydantic_object
        )

    def parse(self, text: str) -> EnvResponse:
        # remove trailing commas before ) or ] from text
        text = re.sub(r",\s*(\)|\])", r"\1", text)
        return super().parse(text)

    def get_format_instructions(self) -> str:
        format_instruction = super().get_format_instructions()
        return format_instruction


class ListOfIntOutputParser(BaseOutputParser[list[int]]):
    number_of_int: int | None
    range_of_int: tuple[int, int] | None

    def __init__(
        self,
        number_of_int: int | None = None,
        range_of_int: tuple[int, int] | None = None,
    ):
        """
        Parse the output to a list of integers

        Args:
            number_of_int (int | None): The number of integers in the output. If None, the number of integers is not fixed.
        """
        super().__init__()
        self.number_of_int = number_of_int
        self.range_of_int = range_of_int

    def _get_description_text(self) -> str:
        return f"a list of{' ' + str(self.number_of_int) if self.number_of_int else ''} intergers{' within the range of' + str(self.range_of_int) if self.range_of_int else ''} separated by spaces. Don't output anything else. Format example: 1 2 3 4 5"

    def get_format_instructions(self) -> str:
        return "Please output " + self._get_description_text()

    def parse(self, output: str) -> list[int]:
        try:
            output_loaded = output.split(" ")
            result = [int(x) for x in output_loaded]
            if self.number_of_int and len(result) != self.number_of_int:
                msg = f"Expect {self.number_of_int} integers, got {len(result)}"
                raise OutputParserException(msg)
            if self.range_of_int:
                for x in result:
                    if x < self.range_of_int[0] or x > self.range_of_int[1]:
                        msg = f"Expect integers within the range of {self.range_of_int}, got {result}"
                        raise OutputParserException(msg)
            return result
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            msg = f"Exception {e}: the output format is not correct. Expect {self._get_description_text()}, got {output}"
            raise OutputParserException(msg)

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "list[int]"


class ListOfStrOutputParser(BaseOutputParser[list[str]]):
    number_of_str: int | None

    def __init__(
        self,
        number_of_str: int | None = None,
    ):
        """
        Parse the output to a list of strings

        Args:
            number_of_str (int | None): The number of strings in the output. If None, the number of strings is not fixed.
        """
        super().__init__()
        self.number_of_str = number_of_str

    def _get_description_text(self) -> str:
        return f"a list of{' ' + str(self.number_of_str) if self.number_of_str else ''} strings separated by space"

    def get_format_instructions(self) -> str:
        return "Please output " + self._get_description_text()

    def parse(self, output: str) -> list[str]:
        try:
            result = output.split(" ")
            if self.number_of_str and len(result) != self.number_of_str:
                msg = f"Expect {self.number_of_str} strings, got {len(result)}"
                raise OutputParserException(msg)
            return result
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except Exception as e:
            msg = f"Exception {e}: the output format is not correct. Expect {self._get_description_text()}, got {output}"
            raise OutputParserException(msg)

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "list[str]"


class StrOutputParser(BaseOutputParser[str]):
    def __init__(self) -> None:
        super().__init__()

    def get_format_instructions(self) -> str:
        return "Please output a string"

    def parse(self, output: str) -> str:
        return output

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "str"


class ScriptOutputParser(BaseOutputParser[ScriptInteractionReturnType]):
    agent_names: list[str] = Field(
        description="The names of the two agents in the conversation"
    )
    background: str = Field(description="The background of the conversation")
    single_turn: bool = Field(description="Whether the output is a single turn")

    def get_format_instructions(self) -> str:
        if self.single_turn:
            return r"""For one turn, only write the next step of this agent. You should follow the structure. The format looks like this: Turn #0 \n[participant's name] [action].
This means you can only generate two lines in one turn.

You can use different types of actions in the [action] part, but PLEASE follows the rule STRICTLY. Remember to include the square brackets when doing an action as stated in the instructions.
1. Use "did nothing" if the agent did nothing.
2. Use "said: "{self.argument}" if the agent want to say, ask or inquire something.
3. Use "[non-verbal communication] {self.argument}" if the agent did non-verbal communication.
4. Use "[action] {self.argument}" if the agent did an action.
5. Use "left the conversation" if the agent left the conversation. And you should stop generation
Other than that, no other format are allowed.

For example, the following outputs are valid:
Turn #1
Oliver Thompson said: "Hey Esmeralda, what's wrong? You seem upset."
Turn #2
Esmeralda Solis [action] moved closer
Turn #3
Oliver Thompson [non-verbal communication] smiled
Turn #4
Esmeralda Solis did nothing
Turn #5
Oliver Thompson left the conversation
Remember to make it short and compact, as it should be less than 20 turns"""

        else:
            return r"""You should separate each turn by a newline. Each turn is separated by a newline, and should only describe one agent. Following the structure: Turn #x \n[participant's name] [action]

You can use different types of actions in the [action] part, but PLEASE follows the rule STRICTLY. Remember to include the square brackets when doing an action as stated in the instructions.
1. Use "did nothing" if the agent did nothing.
2. Use "said: "{self.argument}" if the agent want to say, ask or inquire something.
3. Use "[non-verbal communication] {self.argument}" if the agent did non-verbal communication.
4. Use "[action] {self.argument}" if the agent did an action.
5. Use "left the conversation" if the agent left the conversation. And you should stop generation

For example, the following outputs are valid:
a. Oliver Thompson said: "What's wrong? You seem upset."
b. Esmeralda Solis [action] moved closer
c. Oliver Thompson [non-verbal communication] smiled
e. Esmeralda Solis did nothing
f. Oliver Thompson left the conversation"""

    def parse(self, output: str) -> ScriptInteractionReturnType:
        """
        Parse the loosely formatted output to AgentAction
        We make the reformat in this function
        """
        print("Original output: ", output)
        interaction = ScriptInteraction(interactions=output)
        agent_names = self.agent_names
        assert len(agent_names) == 2, "agent_names must have length 2"
        try:
            # try to parse the output
            parsed_interaction = interaction.parse(
                agent_names=agent_names, background=self.background
            )
            return parsed_interaction
        except Exception as e:
            raise OutputParserException(
                f"Failed to parse the output: {output}. Encounter Exception {e}"
            )

    @property
    def _type(self) -> str:
        """Return the type key."""
        return "str"


def _return_fixed_model_version(model_name: str) -> str:
    if model_name in [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-finetuned",
        "gpt-3.5-turbo-ft-MF",
        "gpt-4",
        "gpt-4-turbo",
    ]:
        return {
            "gpt-3.5-turbo": "gpt-3.5-turbo-0125",
            "gpt-3.5-turbo-finetuned": "ft:gpt-3.5-turbo-0613:academicscmu::8nY2zgdt",
            "gpt-3.5-turbo-ft-MF": "ft:gpt-3.5-turbo-0613:academicscmu::8nuER4bO",
            "gpt-4": "gpt-4-0613",
            "gpt-4-turbo": "gpt-4-1106-preview",
        }[model_name]
    else:
        return model_name


@gin_configurable
@beartype
def obtain_chain(
    model_name: str,
    template: str,
    input_variables: list[str],
    temperature: float = 0.7,
    max_retries: int = 6,
    use_fixed_model_version: bool = True,
) -> RunnableSerializable[dict[Any, Any], BaseMessage]:
    """
    Using langchain to sample profiles for participants
    """
    human_message_prompt = HumanMessagePromptTemplate(
        prompt=PromptTemplate(
            template=template,
            input_variables=input_variables,
        )
    )
    chat_prompt_template = ChatPromptTemplate.from_messages([human_message_prompt])
    if use_fixed_model_version:
        model_name = _return_fixed_model_version(model_name)
    if model_name.startswith("together_ai"):
        model_name = "/".join(model_name.split("/")[1:])
        assert (
            TOGETHER_API_KEY := os.environ.get("TOGETHER_API_KEY")
        ), "TOGETHER_API_KEY is not set"
        chat_openai = ChatOpenAI(
            name=model_name,
            temperature=temperature,
            max_retries=max_retries,
            base_url="https://api.together.xyz/v1",
            api_key=SecretStr(TOGETHER_API_KEY),
        )
        chain = chat_prompt_template | chat_openai
        return chain
    elif model_name.startswith("groq"):
        model_name = "/".join(model_name.split("/")[1:])
        assert (
            GROQ_API_KEY := os.environ.get("GROQ_API_KEY")
        ), "GROQ_API_KEY is not set"
        chat_openai = ChatOpenAI(
            name=model_name,
            temperature=temperature,
            max_retries=max_retries,
            base_url="https://api.groq.com/openai/v1",
            api_key=SecretStr(GROQ_API_KEY),
        )
        chain = chat_prompt_template | chat_openai
        return chain
    elif model_name.startswith("azure"):
        # azure/resource_name/deployment_name/version
        azure_credentials = model_name.split("/")[1:]
        resource_name, deployment_name, azure_version = (
            azure_credentials[0],
            azure_credentials[1],
            azure_credentials[2],
        )
        chat_azure_openai = AzureChatOpenAI(
            azure_deployment=deployment_name,
            api_version=azure_version,
            azure_endpoint=f"https://{resource_name}.openai.azure.com",
            temperature=temperature,
            max_retries=max_retries,
        )
        chain = chat_prompt_template | chat_azure_openai
        return chain
    elif model_name.startswith("custom"):
        custom_model_name, model_base_url = (
            model_name.split("@")[0],
            model_name.split("@")[1],
        )
        custom_model_name = "/".join(custom_model_name.split("/")[1:])
        chat = ChatOpenAI(
            model=custom_model_name,
            temperature=temperature,
            max_retries=max_retries,
            api_key=SecretStr(
                CUSTOM_API_KEY
                if (CUSTOM_API_KEY := os.environ.get("CUSTOM_API_KEY"))
                else "EMPTY"
            ),
            base_url=model_base_url,
        )
        human_message_prompt = HumanMessagePromptTemplate(
            prompt=PromptTemplate(template=template, input_variables=input_variables)
        )
        chat_prompt_template = ChatPromptTemplate.from_messages([human_message_prompt])
        chain = chat_prompt_template | chat
        return chain
    else:
        chat = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_retries=max_retries,
            # base_url="http://tiger.lti.cs.cmu.edu:4000",
            api_key=SecretStr(os.environ.get("OPENAI_API_KEY", ""))
        )
        chain = chat_prompt_template | chat
        return chain


@beartype
def format_bad_output_for_script(
    ill_formed_output: str,
    format_instructions: str,
    agents: list[str],
    model_name: str,
    use_fixed_model_version: bool = True,
) -> BaseMessage:
    template = """
    Given the string that can not be parsed by a parser, reformat it to a string that can be parsed by the parser which uses the following format instructions. Do not add or delete any information.
    Small tip: for every round of conversation, first determine the name and the case, and whether this line contains errors. Correct it if necessary.

    Format instructions: {format_instructions}

    String to be corrected: {ill_formed_output}

    The two agents are: {agents}

    Please only generate the rewritten string:
    """
    print("ill_formed_output: ", ill_formed_output)
    chain = obtain_chain(
        model_name=model_name,
        template=template,
        input_variables=re.findall(r"{(.*?)}", template),
        use_fixed_model_version=use_fixed_model_version,
    )
    input_values = {
        "ill_formed_output": ill_formed_output,
        "format_instructions": format_instructions,
        "agents": agents,
    }
    reformat = chain.invoke(input_values, config={"callbacks": [logging_handler]})
    log.info(f"Reformated output: {reformat}")
    return reformat


@beartype
def format_bad_output(
    ill_formed_output: BaseMessage,
    format_instructions: str,
    model_name: str,
    use_fixed_model_version: bool = True,
) -> BaseMessage:
    template = """
    Given the string that can not be parsed by json parser, reformat it to a string that can be parsed by json parser.
    Original string: {ill_formed_output}

    Format instructions: {format_instructions}

    Please only generate the JSON:
    """
    chain = obtain_chain(
        model_name=model_name,
        template=template,
        input_variables=re.findall(r"{(.*?)}", template),
        use_fixed_model_version=use_fixed_model_version,
    )
    input_values = {
        "ill_formed_output": ill_formed_output.content,
        "format_instructions": format_instructions,
    }
    reformat = chain.invoke(input_values, config={"callbacks": [logging_handler]})
    log.info(f"Reformated output: {reformat}")
    return reformat


@gin_configurable
@beartype
async def agenerate(
    model_name: str,
    template: str,
    input_values: dict[str, str],
    output_parser: BaseOutputParser[OutputType],
    temperature: float = 0.7,
    structured_output: bool = False,
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> OutputType:
    input_variables = re.findall(
        r"(?<!{){([^{}]+)}(?!})", template
    )  # Add negative lookbehind and lookahead to avoid matching {{}}; note that {ab{ab}ab} will not be matched
    assert (
        set(input_variables) == set(list(input_values.keys()) + ["format_instructions"])
        or set(input_variables) == set(list(input_values.keys()))
    ), f"The variables in the template must match input_values except for format_instructions. Got {sorted(input_values.keys())}, expect {sorted(input_variables)}"
    # process template
    template = format_docstring(template)
    chain = obtain_chain(
        model_name=model_name,
        template=template,
        input_variables=input_variables,
        temperature=temperature,
        use_fixed_model_version=use_fixed_model_version,
    )

    if "format_instructions" not in input_values:
        input_values["format_instructions"] = output_parser.get_format_instructions()

    if structured_output:
        assert model_name == "gpt-4o-2024-08-06" or model_name.startswith(
            "custom"
        ), "Structured output is only supported in gpt-4o-2024-08-06 or custom models"
        human_message_prompt = HumanMessagePromptTemplate(
            prompt=PromptTemplate(
                template=template,
                input_variables=input_variables,
            )
        )
        chat_prompt_template = ChatPromptTemplate.from_messages([human_message_prompt])
        prompt_result = chat_prompt_template.invoke(input_values)
        assert isinstance(prompt_result, ChatPromptValue)
        instantiated_prompt = prompt_result.messages[0].content
        assert isinstance(output_parser, PydanticOutputParser)
        assert isinstance(instantiated_prompt, str)
        if model_name.startswith("custom"):
            client = OpenAI(
                base_url=model_name.split("@")[1],
                api_key=os.environ.get("CUSTOM_API_KEY") or "EMPTY",
            )
            model_name = model_name.split("@")[0].split("/")[1]
        else:
            client = OpenAI()

        completion = client.beta.chat.completions.parse(
            model=model_name,
            messages=[
                {"role": "user", "content": instantiated_prompt},
            ],
            response_format=output_parser.pydantic_object,
        )
        result = completion.choices[0].message.parsed
        casted_result = cast(OutputType, result)
        return casted_result

    result = await chain.ainvoke(input_values, config={"callbacks": [logging_handler]})
    try:
        parsed_result = output_parser.invoke(result)
    except Exception as e:
        if isinstance(output_parser, ScriptOutputParser):
            raise e  # the problem has been handled in the parser
        log.debug(
            f"[red] Failed to parse result: {result}\nEncounter Exception {e}\nstart to reparse",
            extra={"markup": True},
        )
        reformat_parsed_result = format_bad_output(
            result,
            format_instructions=output_parser.get_format_instructions(),
            model_name=bad_output_process_model or model_name,
            use_fixed_model_version=use_fixed_model_version,
        )
        parsed_result = output_parser.invoke(reformat_parsed_result)
    log.info(f"Generated result: {parsed_result}")
    return parsed_result


@gin_configurable
@beartype
async def agenerate_env_profile(
    model_name: str,
    inspiration_prompt: str = "asking my boyfriend to stop being friends with his ex",
    examples: str = "",
    temperature: float = 0.7,
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> tuple[EnvironmentProfile, str]:
    """
    Using langchain to generate the background
    """
    result = await agenerate(
        model_name=model_name,
        template="""Please generate scenarios and goals based on the examples below as well as the inspirational prompt, when creating the goals, try to find one point that both sides may not agree upon initially and need to collaboratively resolve it.
        Examples:
        {examples}
        Inspirational prompt: {inspiration_prompt}
        Please use the following format:
        {format_instructions}
        """,
        input_values=dict(
            inspiration_prompt=inspiration_prompt,
            examples=examples,
        ),
        output_parser=PydanticOutputParser(pydantic_object=EnvironmentProfile),
        temperature=temperature,
        bad_output_process_model=bad_output_process_model,
        use_fixed_model_version=use_fixed_model_version,
    )
    return cast(tuple[EnvironmentProfile, str], result)


@beartype
async def agenerate_relationship_profile(
    model_name: str,
    agents_profiles: list[str],
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> tuple[RelationshipProfile, str]:
    """
    Using langchain to generate the background
    """
    agent_profile = "\n".join(agents_profiles)
    result = await agenerate(
        model_name=model_name,
        template="""Please generate relationship between two agents based on the agents' profiles below. Note that you generate
        {agent_profile}
        Please use the following format:
        {format_instructions}
        """,
        input_values=dict(
            agent_profile=agent_profile,
        ),
        output_parser=PydanticOutputParser(pydantic_object=RelationshipProfile),
        bad_output_process_model=bad_output_process_model,
        use_fixed_model_version=use_fixed_model_version,
    )
    return cast(tuple[RelationshipProfile, str], result)


@gin_configurable
@beartype
async def agenerate_action(
    model_name: str,
    history: str,
    turn_number: int,
    action_types: list[ActionType],
    agent: str,
    goal: str,
    temperature: float = 0.7,
    script_like: bool = False,
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> AgentAction:
    """
    Using langchain to generate an example episode
    """
    try:
        if script_like:
            # model as playwright
            template = """
                Now you are a famous playwright, your task is to continue writing one turn for agent {agent} under a given background and history to help {agent} reach social goal. Please continue the script based on the previous turns. You can only generate one turn at a time.
                You can find {agent}'s background and goal in the 'Here is the context of the interaction' field.
                You should try your best to achieve {agent}'s goal in a way that align with their character traits.
                Additionally, maintaining the conversation's naturalness and realism is essential (e.g., do not repeat what other people has already said before).
                {history}.
                The script has proceeded to Turn #{turn_number}. Current available action types are
                {action_list}.
                Note: The script can be ended if 1. one agent have achieved social goals, 2. this conversation makes the agent uncomfortable, 3. the agent find it uninteresting/you lose your patience, 4. or for other reasons you think it should stop.

                Please only generate a JSON string including the action type and the argument.
                Your action should follow the given format:
                {format_instructions}
            """
        else:
            # Normal case, model as agent
            template = """
                Imagine you are {agent}, your task is to act/speak as {agent} would, keeping in mind {agent}'s social goal.
                You can find {agent}'s goal (or background) in the 'Here is the context of the interaction' field.
                Note that {agent}'s goal is only visible to you.
                You should try your best to achieve {agent}'s goal in a way that align with their character traits.
                Additionally, maintaining the conversation's naturalness and realism is essential (e.g., do not repeat what other people has already said before).
                {history}.
                You are at Turn #{turn_number}. Your available action types are
                {action_list}.
                Note: You can "leave" this conversation if 1. you have achieved your social goals, 2. this conversation makes you uncomfortable, 3. you find it uninteresting/you lose your patience, 4. or for other reasons you want to leave.

                Please only generate a JSON string including the action type and the argument.
                Your action should follow the given format:
                {format_instructions}
            """
        result = await agenerate(
            model_name=model_name,
            template=template,
            input_values=dict(
                agent=agent,
                turn_number=str(turn_number),
                history=history,
                action_list=" ".join(action_types),
            ),
            output_parser=PydanticOutputParser(pydantic_object=AgentAction),
            temperature=temperature,
            bad_output_process_model=bad_output_process_model,
            use_fixed_model_version=use_fixed_model_version,
        )
        return cast(AgentAction, result)
    except Exception:
        return AgentAction(action_type="none", argument="")


@gin_configurable
@beartype
async def agenerate_script(
    model_name: str,
    background: ScriptBackground,
    temperature: float = 0.7,
    agent_names: list[str] = [],
    agent_name: str = "",
    history: str = "",
    single_step: bool = False,
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> tuple[ScriptInteractionReturnType, str]:
    """
    Using langchain to generate an the script interactions between two agent
    The script interaction is generated in a single generation process.
    Note that in this case we do not require a json format response,
    so the failure rate will be higher, and it is recommended to use at least llama-2-70b.
    """
    try:
        if single_step:
            result = await agenerate(
                model_name=model_name,
                template="""Now you are a famous playwright, your task is to continue writing one turn for agent {agent} under a given background and history to help {agent} reach social goal. Please continue the script based on the previous turns. You can only generate one turn at a time.

                Here are the conversation background and history:
                {background}
                {history}

                Remember that you are an independent scriptwriter and should finish the script by yourself.
                The output should only contain the script following the format instructions, with no additional comments or text.

                Here are the format instructions:
                {format_instructions}""",
                input_values=dict(
                    background=background.to_natural_language(),
                    history=history,
                    agent=agent_name,
                ),
                output_parser=ScriptOutputParser(
                    agent_names=agent_names,
                    background=background.to_natural_language(),
                    single_turn=True,
                ),
                temperature=temperature,
                bad_output_process_model=bad_output_process_model,
                use_fixed_model_version=use_fixed_model_version,
            )
        else:
            result = await agenerate(
                model_name=model_name,
                template="""
                Please write the script between two characters based on their social goals with a maximum of 20 turns.

                {background}
                Your action should follow the given format:
                {format_instructions}
                Remember that you are an independent scriptwriter and should finish the script by yourself.
                The output should only contain the script following the format instructions, with no additional comments or text.""",
                input_values=dict(
                    background=background.to_natural_language(),
                ),
                output_parser=ScriptOutputParser(
                    agent_names=agent_names,
                    background=background.to_natural_language(),
                    single_turn=False,
                ),
                temperature=temperature,
                bad_output_process_model=bad_output_process_model,
                use_fixed_model_version=use_fixed_model_version,
            )
        return cast(tuple[ScriptInteractionReturnType, str], result)
    except Exception as e:
        # TODO raise(e) # Maybe we do not want to return anything?
        print(f"Exception in agenerate {e}")
        return_default_value: ScriptInteractionReturnType = (
            ScriptInteraction.default_value_for_return_type()
        )
        return (return_default_value, "")


@beartype
def process_history(
    script: ScriptBackground | EnvResponse | dict[str, AgentAction],
) -> str:
    """
    Format the script background
    """
    result = ""
    if isinstance(script, ScriptBackground | EnvResponse):
        script = script.dict()
        result = "The initial observation\n\n"
    for key, value in script.items():
        if value:
            result += f"{key}: {value} \n"
    return result


@beartype
async def agenerate_init_profile(
    model_name: str,
    basic_info: dict[str, str],
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> str:
    """
    Using langchain to generate the background
    """
    result = await agenerate(
        model_name=model_name,
        template="""Please expand a fictional background for {name}. Here is the basic information:
            {name}'s age: {age}
            {name}'s gender identity: {gender_identity}
            {name}'s pronouns: {pronoun}
            {name}'s occupation: {occupation}
            {name}'s big 5 personality traits: {bigfive}
            {name}'s moral Foundation: think {mft} is more important than others
            {name}'s Schwartz portrait value: {schwartz}
            {name}'s decision-making style: {decision_style}
            {name}'s secret: {secret}
            Include the previous information in the background.
            Then expand the personal backgrounds with concrete details (e.g, look, family, hobbies, friends and etc.)
            For the personality and values (e.g., MBTI, moral foundation, and etc.),
            remember to use examples and behaviors in the person's life to demonstrate it.
            """,
        input_values=dict(
            name=basic_info["name"],
            age=basic_info["age"],
            gender_identity=basic_info["gender_identity"],
            pronoun=basic_info["pronoun"],
            occupation=basic_info["occupation"],
            bigfive=basic_info["Big_Five_Personality"],
            mft=basic_info["Moral_Foundation"],
            schwartz=basic_info["Schwartz_Portrait_Value"],
            decision_style=basic_info["Decision_making_Style"],
            secret=basic_info["secret"],
        ),
        output_parser=StrOutputParser(),
        bad_output_process_model=bad_output_process_model,
        use_fixed_model_version=use_fixed_model_version,
    )
    return result


@beartype
async def convert_narratives(
    model_name: str,
    narrative: str,
    text: str,
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> str:
    if narrative == "first":
        result = await agenerate(
            model_name=model_name,
            template="""Please convert the following text into a first-person narrative.
            e.g, replace name, he, she, him, her, his, and hers with I, me, my, and mine.
            {text}""",
            input_values=dict(text=text),
            output_parser=StrOutputParser(),
            bad_output_process_model=bad_output_process_model,
            use_fixed_model_version=use_fixed_model_version,
        )
    elif narrative == "second":
        result = await agenerate(
            model_name=model_name,
            template="""Please convert the following text into a second-person narrative.
            e.g, replace name, he, she, him, her, his, and hers with you, your, and yours.
            {text}""",
            input_values=dict(text=text),
            output_parser=StrOutputParser(),
            bad_output_process_model=bad_output_process_model,
            use_fixed_model_version=use_fixed_model_version,
        )
    else:
        raise ValueError(f"Narrative {narrative} is not supported.")
    return result


@beartype
async def agenerate_goal(
    model_name: str,
    background: str,
    bad_output_process_model: str | None = None,
    use_fixed_model_version: bool = True,
) -> str:
    """
    Using langchain to generate the background
    """
    result = await agenerate(
        model_name=model_name,
        template="""Please generate your goal based on the background:
            {background}
            """,
        input_values=dict(background=background),
        output_parser=StrOutputParser(),
        bad_output_process_model=bad_output_process_model,
        use_fixed_model_version=use_fixed_model_version,
    )
    return result