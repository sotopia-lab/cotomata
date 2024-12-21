from flask import Flask, jsonify, request
import subprocess
import os
from dotenv import load_dotenv
import logging
import time
from redis import Redis
from aact import Message
from aact_openhands.utils import AgentAction

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
load_dotenv()

port = int(os.environ.get("PORT", 5001))
debug = os.environ.get("FLASK_DEBUG", "0") == "1"

# Default TOML configuration
DEFAULT_CONFIG = """redis_url = "redis://localhost:6379/0"
extra_modules = ["aact_openhands.openhands_node"]

[[nodes]]
node_name = "{node_name}"
node_class = "openhands"

[nodes.node_args]
output_channels = {output_channels}
input_channels = {input_channels}
modal_session_id = "{modal_session_id}"
"""

class AACTProcess:
    def __init__(self):
        self.status = None
        self.output = None
        self.success = None
        self._process = None
        self._config_path = 'temp_config.toml'
        self._config = DEFAULT_CONFIG
        self.input_channel = None
        self.output_channel = None

    def start(self, config=None, input_channel='Agent:Runtime', output_channel='Runtime:Agent'):
        """Start the AACT process"""
        self.input_channel = input_channel
        self.output_channel = output_channel
        try:
            # Write config
            logger.debug(f"Writing config to {self._config_path}")
            with open(self._config_path, 'w') as f:
                f.write(config if config is not None else self._config)

            # Start process
            cmd = ['poetry', 'run', 'aact', 'run-dataflow', self._config_path]
            logger.info(f"Starting process with command: {' '.join(cmd)}")
            
            try:
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1  # Line buffered
                )
            except FileNotFoundError:
                logger.error("Failed to find poetry or aact command. Is poetry installed and in PATH?")
                self.status = 'error'
                self.output = "Command not found: poetry or aact"
                self.success = False
                return False
            except PermissionError:
                logger.error("Permission denied when trying to execute the command")
                self.status = 'error'
                self.output = "Permission denied executing command"
                self.success = False
                return False
            except Exception as e:
                logger.error(f"Failed to start process: {e}", exc_info=True)
                self.status = 'error'
                self.output = f"Failed to start process: {str(e)}"
                self.success = False
                return False

            if self._process is None:
                logger.error("Process creation failed for unknown reason")
                self.status = 'error'
                self.output = "Process creation failed"
                self.success = False
                return False
            
            
            start_time = time.time()
            timeout_at = start_time + 300  # 5 minutes
            process_running = True
            
            dummy_action = AgentAction(
                agent_name='system',
                action_type='run',
                argument='echo "I am alive kimosabe"',
                path=None
            )
            message_json = Message[AgentAction](data=dummy_action).model_dump_json()
            
            # Test communication with Redis
            r = Redis.from_url("redis://localhost:6379/0")
            r.ping()
            
            pubsub = r.pubsub()
            pubsub.subscribe(self.output_channel)
                    
            while process_running:
                try:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # # Check for timeout
                    if current_time > timeout_at:
                        logger.error(f"Process timed out after {elapsed:.1f} seconds")
                        self._process.terminate()
                        self.status = 'error'
                        self.output = f"Timeout after {elapsed:.1f}s"
                        return False
                    
                    # Send dummy action and check for response
                    r.publish(self.input_channel, message_json)
                    # Wait for response with timeout
                    start_listen = time.time()
                    while (time.time() - start_listen) < 2:
                        message = pubsub.get_message(timeout=1)
                        if message and message['type'] == 'message':
                            self.status = 'running'
                            self.output = "OpenHands node started successfully"
                            return True
                        time.sleep(0.1)
                    logger.info("Waiting for OpenHands node to start...")
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                    process_running = False
            
            # Process ended - try to get final output
            logger.error("Process ended unexpectedly")
            try:
                remaining_out, remaining_err = self._process.communicate(timeout=1)
                if remaining_out:
                    logger.error(f"Final stdout: {remaining_out}")
                if remaining_err:
                    logger.error(f"Final stderr: {remaining_err}")
            except Exception as e:
                logger.error(f"Error getting final output: {e}")
            
            self.status = 'error'
            self.output = "Process ended unexpectedly"
            return False
            
        except Exception as e:
            logger.error(f"Failed to start process: {e}", exc_info=True)  # Added stack trace
            self.status = 'error'
            self.output = str(e)
            self.success = False
            return False

    def stop(self):
        """Stop the AACT process"""
        if self._process:
            # Close any open streams
            if self._process.stdout:
                self._process.stdout.close()
            if self._process.stderr:
                self._process.stderr.close()
                
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()  # Ensure process is fully cleaned up
            
            self._process = None
        
        if os.path.exists(self._config_path):
            os.remove(self._config_path)

    def get_status(self):
        """Get current process status"""
        if not self._process:
            return {
                'status': self.status or 'not_started',
                'output': self.output,
                'success': self.success
            }

        # Check if process is still running
        if self._process.poll() is None:
            return {
                'status': 'running',
                'output': None,
                'success': None
            }
        
        # Process finished - read output and close streams
        stdout, stderr = self._process.communicate()
        success = self._process.returncode == 0
        
        # Close streams explicitly
        if self._process.stdout:
            self._process.stdout.close()
        if self._process.stderr:
            self._process.stderr.close()
            
        return {
            'status': 'completed',
            'output': stdout if success else stderr,
            'success': success
        }

    def __del__(self):
        """Ensure cleanup on object destruction"""
        self.stop()

# Global process manager
process_manager = AACTProcess()

@app.route('/initialize', methods=['POST'])
def initialize():
    """Initialize the AACT dataflow process with custom configuration"""
    try:
        params = request.json
        logger.debug(f"Initializing with params: {params}")
        
        required_fields = ['output_channels', 'input_channels', 'node_name', 'modal_session_id']
        if not all(field in params for field in required_fields):
            logger.error(f"Missing required fields. Required: {required_fields}, Received: {list(params.keys())}")
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Stop any existing process
        process_manager.stop()
        
        # Write config with params and start process
        config = DEFAULT_CONFIG.format(**params)
        
        # Extract channels from params
        input_channel = params['input_channels'][0]
        output_channel = params['output_channels'][0]
        
        success = process_manager.start(
            config=config,
            input_channel=input_channel,
            output_channel=output_channel
        )
        
        if not success:
            logger.error(f"Process start failed: {process_manager.output}")
            return jsonify({
                'status': 'error',
                'error': process_manager.output
            }), 500

        return jsonify({'status': 'initialized'})

            
    except Exception as e:
        logger.error(f"Error in initialize: {e}", exc_info=True)  # Include stack trace
        process_manager.stop()
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
        
        
@app.route('/status', methods=['GET'])
def get_status():
    """Get current process status"""
    return jsonify(process_manager.get_status())


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


@app.route('/stop', methods=['POST'])
def stop():
    """Stop the AACT process"""
    try:
        process_manager.stop()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f"Error stopping process: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port, debug=debug)