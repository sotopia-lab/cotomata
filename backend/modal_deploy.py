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

from main import web_app, startup_event, shutdown_event

app = modal.App("cotomata")
redis_volume = modal.NetworkFileSystem.from_name("cotomata-redis", create_if_missing=True)

# Create the base image with common dependencies
base_image = (
    modal.Image.debian_slim().pip_install(
        "fastapi",
        "uvicorn",
        "redis",
        "flask",
        "python-dotenv",
        "poetry",
        "gunicorn",
        "uv",
        "httpx",
    ).apt_install(
        "curl",
        "wget",
        "gnupg2",
        "redis-server",
        "netcat",  # For checking port availability
        "python3-venv",  # For poetry
        "git"  # For poetry dependencies
    )
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
        print("\n[1/3] Starting Redis server...")
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
        print("\n[2/3] Starting OpenHands app...")
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
        print("\n[3/3] Starting Interview app...")
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

    async def init_all(self):
        print("\nInitializing all services...")
        try:
            await self.init_redis()
            await self.init_openhands()
            await self.init_interview()
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

@app.cls(
    image=base_image.add_local_dir(".", remote_path="/root")
                    .add_local_dir("aact-openhands", remote_path="/root/aact-openhands")
                    .add_local_python_source("main"),
    network_file_systems={"/redis_data": redis_volume},
    keep_warm=1,
    cpu=8,
    concurrency_limit=1,
    allow_concurrent_inputs=10
)
class ModalApp:
    def __init__(self):
        self.app = web_app

    @modal.enter()
    async def startup(self):
        serviceManager = ServiceManager()
        await serviceManager.init_all()
        await startup_event()

    @modal.exit()
    async def shutdown(self):
        await shutdown_event()

    @modal.asgi_app()
    def serve(self):
        return self.app


