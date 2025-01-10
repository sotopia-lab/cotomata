# Interview Case Setup Guide

## Prerequisites

1. Clone and set up the AACT-OpenHands repository:
```bash
git clone https://github.com/akhatua2/aact-openhands
cd aact-openhands
```

2. Install dependencies using uv:
```bash
cd backend
uv pip install -e .
```

3. Start the AACT runtime instance:
```bash
cd openhands; poetry install; cd ..
poetry install
poetry run aact run-dataflow examples/openhands_node.toml
```
Keep this running in a separate terminal window.

## Running the Interview

### Method 1: Direct TOML File

Run the interview using the provided script:
```bash
uv run aact run-dataflow interview.toml
```

### Method 2: REST API

1. Start the Flask API server:
```bash
uv run start-api
```
This will start the server on port 9000.

2. Use the API endpoint to initialize agents:
Check `test_curl.sh` for an example curl command.
> You MUST update line 84 in `test_curl.sh` to point to the correct log directory.
## Directory Structure

```
backend/
├── pyproject.toml     # Project configuration and dependencies
└── interview_case/
    ├── interview.toml      # Main dataflow configuration
    ├── interview_agent.py  # Interview agent implementation
    ├── base_agent.py      # Base agent class
    ├── app.py             # Flask API server
    └── nodes/             # Node implementations
```

## API Documentation

### POST /init-agents

Initializes the interview agents using provided configuration.

**Request Body:**
- `redis_url` (string, required): Redis connection URL
- `extra_modules` (array, required): List of Python modules to import
- `nodes` (array, required): List of node configurations
  - Each node requires:
    - `node_name` (string)
    - `node_class` (string)
    - `node_args` (object): Configuration specific to the node type

**Response:**
```json
{
    "config_file": "......./interview_37489.toml",
    "message": "Interview process started",
    "pid": 37502,
    "status": "success"
}
```

**Error Response:**
```json
{
    "error": "Error message",
    "details": "Error details..."
}
``` 