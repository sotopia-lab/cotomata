from flask import Flask, request, jsonify, Response
import toml
import subprocess
import os
import sys
from typing import Union, Tuple

app = Flask(__name__)


@app.route('/health', methods=['GET'])
def health() -> str:
    return 'OK'

@app.route('/init-agents', methods=['POST'])
def init_agents() -> Union[Response, Tuple[Response, int]]:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        required_fields = ['redis_url', 'extra_modules', 'nodes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create a directory for temporary files if it doesn't exist
        temp_dir = os.path.join(current_dir, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a unique filename
        temp_file = os.path.join(temp_dir, f'interview_{os.getpid()}.toml')
        
        # Write the TOML file
        with open(temp_file, 'w') as f:
            toml_str = toml.dumps(data)
            f.write(toml_str)
            f.flush()
            os.fsync(f.fileno())  # Ensure file is written to disk
        
        try:
            # Run the command in background
            process = subprocess.Popen(
                ['uv', 'run', 'aact', 'run-dataflow', temp_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=current_dir,
                start_new_session=True  # This ensures the process continues running
            )
            
            # Check if process started successfully
            if process.poll() is None:  # None means process is still running
                return jsonify({
                    'status': 'success',
                    'message': 'Interview process started',
                    'pid': process.pid,
                    'config_file': temp_file
                })
            else:
                # Process failed to start
                return jsonify({
                    'error': 'Process failed to start',
                    'details': f'Exit code: {process.poll()}'
                }), 500
                
        except Exception as e:
            # Clean up file if process fails to start
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            return jsonify({
                'error': 'Failed to start interview process',
                'details': str(e)
            }), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_interview() -> int:
    """Run the interview directly using the default TOML configuration"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    toml_path = os.path.join(current_dir, 'interview.toml')
    
    try:
        # Run in foreground for direct execution
        subprocess.run(
            ['uv', 'run', 'aact', 'run-dataflow', toml_path],
            check=True,
            cwd=current_dir
        )
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}", file=sys.stderr)
        return 1

def main() -> None:
    """Entry point for the application script"""
    app.run(host='0.0.0.0', port=6000)

if __name__ == '__main__':
    main() 