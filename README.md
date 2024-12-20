# Development Environment Setup Guide

This guide provides instructions for setting up and running the development environment both locally and on Google VM.

## Local Development Setup

### Prerequisites

1. **Redis Server**
  - Must be running on `localhost:6379`
  - Ensure Redis is installed and properly configured

### Project Setup

#### AACT-OpenHands Backend
1. Clone the repository:
  git clone https://github.com/akhatua2/aact-openhands

2. Follow the repository's README for detailed setup instructions
3. Verify the Flask server is running successfully
    ```
    # Install dependencies
    bun i

    # Start development server
    bun run dev
    ```

### Google VM Environment

#### Project Structure
```
Root Directory
├── cotomata/          # Cotomata project files
└── aact-openhands/    # AACT-OpenHands project files
```

API Endpoints

- Base Server URL: http://34.57.199.157
- Cotomata API: http://34.57.199.157:3000/{endpoint}
- AACT-OpenHands API: http://34.57.199.157:5000/{endpoint}

#### Server Management

Status Monitoring
Check the current server status:
```
sudo systemctl status {branch}.service
```
Restart the server:
```
# Reload system configurations
sudo systemctl daemon-reload

# Restart specific service
sudo systemctl restart {branch}.service
```
Stop server (required before local testing):
```
sudo systemctl stop cotomata
```

#### Local Development on VM
Running Cotomata
```
# Navigate to frontend directory
cd cotomata/frontend

# Start development server
bun run dev
```
Running AACT-OpenHands
```
# Navigate to project directory
cd aact-openhands/aact_openhands

# Start Python application
poetry run python app.py
```

Access your local development instance at: http://34.57.199.157:{PORT}/