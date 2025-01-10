# Interview Case Setup Guide

## Prerequisites

1. Clone and set up the AACT-OpenHands repository:
```bash
git clone https://github.com/akhatua2/aact-openhands
cd aact-openhands
```

2. Start the AACT runtime instance:
```bash
cd openhands; poetry install; cd ..
poetry install
poetry run aact run-dataflow examples/openhands_node.toml
```
Keep this running in a separate terminal window.

## Running the Interview

1. Make sure you're in the interview_case directory:
```bash
cd interview_case
```

2. Run the interview using:
```bash
uv run aact run-dataflow interview.toml
```

## Directory Structure

```
interview_case/
├── interview.toml      # Main dataflow configuration
├── interview_agent.py  # Interview agent implementation
├── base_agent.py      # Base agent class
└── nodes/             # Node implementations
``` 
