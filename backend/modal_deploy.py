from contextlib import asynccontextmanager
from typing import Dict
import modal
import os
from pathlib import Path

import os
import subprocess
import time
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import traceback

app = modal.App("cotomata")
redis_volume = modal.NetworkFileSystem.from_name("cotomata-redis", create_if_missing=True)

# Create the base image with common dependencies
base_image = modal.Image.debian_slim().pip_install(
    "fastapi",
    "uvicorn",
    "redis",
    "flask",
    "python-dotenv",
    "poetry",
    "gunicorn",
    "uv",
).apt_install(
    "curl",
    "wget",
    "gnupg2",
    "redis-server",
    "netcat",  # For checking port availability
    "python3-venv",  # For poetry
    "git"  # For poetry dependencies
)

# Add Node.js and bun to the image
base_image = base_image.dockerfile_commands(
    "RUN apt-get update",
    "RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
    "RUN apt-get install -y nodejs",
    "RUN npm install -g bun"
)

class ServiceManager:
    def __init__(self):
        self._services = {}
        self._processes = []
        print("ServiceManager initialized")

    def log_error(self, e: Exception, context: str):
        print(f"\nERROR in {context}:")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print("Traceback:")
        traceback.print_exc(file=sys.stdout)
        print()

    async def init_redis(self):
        print("\n[1/4] Starting Redis server...")
        try:
            # Create Redis directory
            os.makedirs("/redis_data", exist_ok=True)
            print("Redis directory created at /redis_data")

            # Write Redis config
            config = "bind 0.0.0.0\nport 6379\ndir /redis_data\nappendonly yes\ndaemonize yes"
            with open("/redis_data/redis.conf", "w") as f:
                f.write(config)
            print("Redis config written to /redis_data/redis.conf")
            
            # Start Redis server
            print("Starting Redis server with config...")
            result = subprocess.run(
                ["redis-server", "/redis_data/redis.conf"],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"Redis server output: {result.stdout}")
            if result.stderr:
                print(f"Redis server stderr: {result.stderr}")
            
            # Wait for Redis to be ready
            print("Checking Redis connection...")
            for attempt in range(30):
                try:
                    result = subprocess.run(
                        ["redis-cli", "ping"],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    self._services["redis"] = "connected"
                    print(f"✓ Redis is ready! (attempt {attempt + 1})")
                    return True
                except subprocess.CalledProcessError as e:
                    print(f"Waiting for Redis... (attempt {attempt + 1}/30)")
                    print(f"Redis ping error: {e.stderr if e.stderr else str(e)}")
                    await asyncio.sleep(1)
            
            raise Exception("Redis server failed to start after 30 attempts")
        except Exception as e:
            self._services["redis"] = f"failed: {str(e)}"
            self.log_error(e, "Redis initialization")
            raise

    async def init_openhands(self):
        print("\n[2/4] Starting OpenHands app...")
        try:
            # Setup OpenHands
            print("Changing to OpenHands directory...")
            os.chdir("/root/aact-openhands")
            print(f"Current directory: {os.getcwd()}")

            # Install the current package
            subprocess.run(
                ["poetry", "install"],
                check=True,
                capture_output=True,
                text=True
            )
            # Start OpenHands with proper Python path
            print("Starting OpenHands with Gunicorn...")
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"
            
            process = subprocess.Popen(
                ["poetry", "run", "python", "-m", "aact_openhands.app"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            self._processes.append(process)
            self._services["openhands"] = "running"
            print("✓ OpenHands app started on port 5000")

            # Check process status
            time.sleep(2)  # Give it a moment to start
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print("OpenHands stdout:", stdout)
                print("OpenHands stderr:", stderr)
                raise Exception(f"OpenHands process exited with code {process.returncode}")

        except Exception as e:
            self._services["openhands"] = f"failed: {str(e)}"
            self.log_error(e, "OpenHands initialization")
            raise

    async def init_interview(self):
        print("\n[3/4] Starting Interview app...")
        try:
            # Setup Interview
            print("Changing to Interview directory...")
            os.chdir("/root")
            print(f"Current directory: {os.getcwd()}")

            # Install the current package
            subprocess.run(
                ["pip", "install", "-e", "."],
                check=True,
                capture_output=True,
                text=True
            )
            # Start Interview with proper Python path
            print("Starting Interview case with Gunicorn...")
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"

            process = subprocess.Popen(
                ["uv", "run", "python", "-m","interview_case.app"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            self._processes.append(process)
            self._services["interview"] = "running"
            print("✓ Interview case started on port 9000")

            # Check process status
            time.sleep(2)  # Give it a moment to start
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print("Interview case stdout:", stdout)
                print("Interview case stderr:", stderr)
                raise Exception(f"Interview case process exited with code {process.returncode}")
            
        except Exception as e:
            self._services["interview"] = f"failed: {str(e)}"
            self.log_error(e, "Interview case initialization")
            raise

    async def init_nodejs(self):
        print("\n[4/4] Starting Node.js backend...")
        try:
            # Setup Node.js backend
            print("Changing to backend directory...")
            os.chdir("/root")
            print(f"Current directory: {os.getcwd()}")

            # Install dependencies
            print("Installing Node.js dependencies...")
            result = subprocess.run(
                ["bun", "install"],
                check=True,
                capture_output=True,
                text=True
            )
            print("Bun install output:", result.stdout)
            if result.stderr:
                print("Bun install stderr:", result.stderr)

            # Set environment variables
            os.environ.update({
                "REDIS_URL": "redis://localhost:6379/0",
                "PORT": "8000",
                "NODE_ENV": "production"
            })

            # Start Node.js backend
            print("Starting Node.js backend...")
            process = subprocess.Popen(
                ["bun", "src/server.js"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self._processes.append(process)
            self._services["node"] = "running"
            print("✓ Node.js backend started on port 8000")

            # Check process status
            time.sleep(2)  # Give it a moment to start
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print("Node.js stdout:", stdout)
                print("Node.js stderr:", stderr)
                raise Exception(f"Node.js process exited with code {process.returncode}")

        except Exception as e:
            self._services["node"] = f"failed: {str(e)}"
            self.log_error(e, "Node.js initialization")
            raise

    async def init_all(self):
        print("\nInitializing all services...")
        try:
            await self.init_redis()
            await self.init_openhands()
            await self.init_interview()
            await self.init_nodejs()
            print("\n✓ All services initialized successfully")
            return {"status": "initialized", "services": self._services.copy()}
        except Exception as e:
            self.log_error(e, "Service initialization")
            return {"status": "failed", "error": str(e), "services": self._services.copy()}

    def cleanup(self):
        print("\nCleaning up processes...")
        for process in self._processes:
            try:
                process.terminate()
                print(f"Process {process.pid} terminated")
            except Exception as e:
                print(f"Error terminating process: {e}")
        self._processes.clear()
        self._services.clear()
        print("Cleanup complete")

    def get_status(self):
        return {
            "services": self._services.copy(),
            "process_count": len(self._processes)
        }
    
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services and attach the manager to app.state.
    service_manager = ServiceManager()
    result = await service_manager.init_all()
    if result["status"] == "failed":
        print("Service initialization failed:", result)
        # Optionally, you might raise an exception here to abort startup.
    app.state.service_manager = service_manager
    yield
    # Shutdown: Clean up any spawned processes.
    print("FastAPI shutdown: cleaning up services...")
    if hasattr(app.state, "service_manager"):
        app.state.service_manager.cleanup()
    print("Cleanup complete.")


web_app = FastAPI(lifespan=lifespan)
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("CORS middleware configured")

@web_app.get("/")
async def root():
    return {"message": "Backend is running"}

@web_app.get("/health")
async def health():
    service_manager = getattr(web_app.state, "service_manager", None)
    status = service_manager.get_status() if service_manager else {}
    return status
    
@app.function(
    image=base_image.add_local_dir(".", remote_path="/root")
            .add_local_dir("aact-openhands", remote_path="/root/aact-openhands"),
    network_file_systems={"/redis_data": redis_volume},
    keep_warm=1
)

@modal.asgi_app()
def serve_app():
    return web_app


