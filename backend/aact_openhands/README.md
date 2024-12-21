# Openhands x AAct

## Overview

This project integrates the Openhands framework with AAct to create a runtime environment for executing actions and handling events. The `openhands_node.py` file defines the `OpenHands` class, which is a node that processes actions and communicates with a runtime environment.

## Project Structure

- `aact_openhands/`: Contains the core implementation of the Openhands node and related utilities.
  - `openhands_node.py`: Main implementation of the OpenHands node.
  - `utils.py`: Contains utility classes and functions, including `AgentAction` and `ActionType`.
  - `__init__.py`: Marks the directory as a Python package.

- `app.py`: Flask server for managing AACT dataflow processes.
- `tests/`: Contains test files for the project.
  - `__init__.py`: Marks the directory as a Python package.

- `examples/`: Contains example configuration files.
  - `openhands_node.toml`: Configuration file for running the OpenHands node.

- `pyproject.toml`: Configuration file for managing dependencies with Poetry.

## Installation

To set up the project, ensure you have Python 3.12 installed. Then, follow these steps:

1. **Install Poetry**: If you haven't already, install Poetry for dependency management.
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install Dependencies**: Navigate to the project directory and install the dependencies.
   ```bash
   poetry install
   ```

## Setting Up Environment Variables

To run the OpenHands node, you need to set up your environment variables. Follow these steps:

1. **Obtain Modal API Keys**:
   - **Sign Up / Log In**: Go to the [Modal website](https://modal.com) and sign up or log in to your account.
   - **Navigate to API Keys**: Once logged in, navigate to the API keys section, usually found under account settings.
   - **Generate API Keys**: Generate a new API key pair. You should receive a `MODAL_API_TOKEN_ID` and a `MODAL_API_TOKEN_SECRET`.
   - **Secure Your Keys**: Store these keys securely. Do not share them publicly or commit them to version control.

2. **Create a `.env` File**: Copy the `env.example` file to a new file named `.env` in the root of your project directory:

   ```bash
   cp env.example .env
   ```

3. **Edit the `.env` File**: Open the `.env` file and replace the placeholder values with your actual API keys and URLs:

   ```
   MODAL_API_TOKEN_ID=your_actual_modal_api_token_id
   MODAL_API_TOKEN_SECRET=your_actual_modal_api_token_secret
   ```

## Flask Server

The project includes a Flask server (`app.py`) that manages AACT dataflow processes. The server provides the following endpoints:

- `GET /health`: Health check endpoint
- `POST /initialize`: Start a new AACT dataflow process
- `GET /status`: Get the status of the current process

### Running the Server

To start the Flask server:
```bash
poetry run python app.py
```

The server will start on `http://localhost:5000`.

## Flask Server API Documentation

The Flask server (`app.py`) provides several endpoints to manage the OpenHands runtime:

### Endpoints

#### Initialize Runtime
- **URL**: `/initialize`
- **Method**: `POST`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "output_channels": ["Runtime1234:Agent"],
    "input_channels": ["Agent:Runtime1234"],
    "node_name": "runtime",
    "modal_session_id": "session_id"
  }
  ```
- **Success Response**:
  - Code: 200
  - Content: `{"status": "initialized"}`
- **Error Response**:
  - Code: 400
  - Content: `{"error": "Missing required fields"}`
  - Code: 500
  - Content: `{"status": "error", "error": "Error message"}`

#### Check Status
- **URL**: `/status`
- **Method**: `GET`
- **Success Response**:
  - Code: 200
  - Content:
    ```json
    {
      "status": "running|completed|not_started|error",
      "output": "output message or null",
      "success": true|false|null
    }
    ```

#### Health Check
- **URL**: `/health`
- **Method**: `GET`
- **Success Response**:
  - Code: 200
  - Content: `{"status": "ok"}`

#### Stop Runtime
- **URL**: `/stop`
- **Method**: `POST`
- **Success Response**:
  - Code: 200
  - Content: `{"status": "stopped"}`
- **Error Response**:
  - Code: 500
  - Content: `{"status": "error", "error": "Error message"}`

### Example Usage

Using curl:
```bash
# Initialize the runtime
curl -X POST http://localhost:5000/initialize \
  -H "Content-Type: application/json" \
  -d '{
    "output_channels": ["Runtime1234:Agent"],
    "input_channels": ["Agent:Runtime1234"],
    "node_name": "runtime",
    "modal_session_id": "session_id"
  }'

# Check status
curl http://localhost:5000/status

# Health check
curl http://localhost:5000/health

# Stop runtime
curl -X POST http://localhost:5000/stop
```

Using Python requests:
```python
import requests

# Initialize the runtime
response = requests.post(
    'http://localhost:5000/initialize',
    json={
        "output_channels": ["Runtime1234:Agent"],
        "input_channels": ["Agent:Runtime1234"],
        "node_name": "runtime",
        "modal_session_id": "session_id"
    }
)

# Check status
status = requests.get('http://localhost:5000/status').json()

# Health check
health = requests.get('http://localhost:5000/health').json()

# Stop runtime
stop = requests.post('http://localhost:5000/stop').json()
```

## Testing

The project includes both unit tests and integration tests:

### Running Tests

To run all tests:
```bash
./run_tests.sh
```

This script will:
1. Run unit tests for the Flask server
2. Start the Flask server
3. Run integration tests for AACT command execution
4. Clean up all processes and temporary files

### Test Structure

- **Unit Tests** (`tests/test_server.py`):
  - Tests Flask server endpoints
  - Verifies server responses and process management
  - Runs without actual AACT process execution

- **Integration Tests** (`tests/test_live_server.py`):
  - Tests actual AACT command execution
  - Verifies process startup and management
  - Includes proper resource cleanup

## Usage

### Running the OpenHands Node

To run the OpenHands node with the provided configuration, use the following command:
```bash
poetry run aact run-dataflow examples/openhands_node.toml
```

Upon successful execution, you should see output similar to the following:

```bash
16:41:26 - openhands:INFO: openhands_node.py:120 - --------------------
16:41:26 - openhands:INFO: openhands_node.py:121 - RUNTIME CONNECTED
16:41:26 - openhands:INFO: openhands_node.py:122 - --------------------
16:41:26 - openhands:INFO: openhands_node.py:127 - Runtime initialization took 157.77 seconds.
```

## Troubleshooting

If you encounter a `ModuleNotFoundError`, ensure that:

- The directory structure is correct, and `openhands_node.py` is located in the `openhands` directory.
- The `openhands` directory contains an `__init__.py` file.
- The `pyproject.toml` file includes the `openhands` package in the `[tool.poetry.packages]` section.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or issues, please contact Arpandeep Khatua at arpandeepk@gmail.com.