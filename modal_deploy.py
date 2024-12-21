import modal
import os
from pathlib import Path

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
    "gunicorn"
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

@app.function(
    image=base_image,
    mounts=[
        modal.Mount.from_local_dir("backend", remote_path="/root/backend"),
        modal.Mount.from_local_dir("backend/aact_openhands", remote_path="/root/backend/aact_openhands")
    ],
    network_file_systems={"/redis_data": redis_volume},
    keep_warm=1
)
@modal.web_endpoint(label="cotomata-backend")
async def start_backend():
    print("\n=== Starting Backend Deployment ===")
    import os
    import subprocess
    import time
    import asyncio
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import sys
    import traceback

    def log_error(e: Exception, context: str):
        print(f"\nERROR in {context}:")
        print(f"Exception type: {type(e).__name__}")
        print(f"Exception message: {str(e)}")
        print("Traceback:")
        traceback.print_exc(file=sys.stdout)
        print()  # Empty line for readability

    class ServiceManager:
        def __init__(self):
            self._services = {}
            self._processes = []
            print("ServiceManager initialized")

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
                log_error(e, "Redis initialization")
                raise

        async def init_openhands(self):
            print("\n[2/3] Starting OpenHands app...")
            try:
                # Setup OpenHands
                print("Changing to OpenHands directory...")
                os.chdir("/root/backend/aact_openhands")
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
                print("✓ OpenHands app started on port 5001")

                # Check process status
                time.sleep(2)  # Give it a moment to start
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    print("OpenHands stdout:", stdout)
                    print("OpenHands stderr:", stderr)
                    raise Exception(f"OpenHands process exited with code {process.returncode}")

            except Exception as e:
                self._services["openhands"] = f"failed: {str(e)}"
                log_error(e, "OpenHands initialization")
                raise

        async def init_nodejs(self):
            print("\n[3/3] Starting Node.js backend...")
            try:
                # Setup Node.js backend
                print("Changing to backend directory...")
                os.chdir("/root/backend")
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
                log_error(e, "Node.js initialization")
                raise

        async def init_all(self):
            print("\nInitializing all services...")
            try:
                await self.init_redis()
                await self.init_openhands()
                await self.init_nodejs()
                print("\n✓ All services initialized successfully")
                return {"status": "initialized", "services": self._services.copy()}
            except Exception as e:
                log_error(e, "Service initialization")
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

    # Create FastAPI app
    print("\nInitializing FastAPI application...")
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("CORS middleware configured")

    try:
        print("\nStarting service initialization...")
        service_manager = ServiceManager()
        result = await service_manager.init_all()
        
        if result["status"] == "failed":
            print("\n❌ ERROR: Service initialization failed")
            print(f"Error details: {result['error']}")
            print(f"Service status: {result['services']}")
            raise Exception(f"Startup failed: {result['error']}")
        
        print("\nSetting up FastAPI routes...")
        @app.get("/")
        async def root():
            return {"message": "Backend is running"}

        @app.get("/health")
        async def health():
            status = service_manager.get_status()
            return status

        print("\n✓ Backend deployment complete!")
        return app

    except Exception as e:
        print("\n❌ CRITICAL ERROR during backend startup")
        log_error(e, "Backend startup")
        raise


@app.function(
    image=base_image,
    mounts=[modal.Mount.from_local_dir("frontend", remote_path="/root/frontend")],
    keep_warm=1
)
@modal.asgi_app(label="cotomata-frontend")
def frontend_app():
    import os
    import subprocess
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    
    print("Starting Cotomata frontend...")
    
    # Build Frontend
    print("Building frontend...")
    os.chdir("/root/frontend")
    
    # Install dependencies
    print("Installing dependencies...")
    try:
        install_output = subprocess.check_output(["bun", "install"], stderr=subprocess.STDOUT)
        print("Install output:", install_output.decode())
    except subprocess.CalledProcessError as e:
        print("Install error output:", e.output.decode())
        raise Exception("Failed to install dependencies")
    
    # Build the project
    print("\nBuilding the project...")
    try:
        build_output = subprocess.check_output(["bun", "run", "build"], stderr=subprocess.STDOUT)
        print("Build output:", build_output.decode())
    except subprocess.CalledProcessError as e:
        print("Build error output:", e.output.decode())
        raise Exception("Build command failed")
    
    if not os.path.exists("out"):
        print("\nChecking for alternative output directories:")
        os.system("find /root/frontend -type d")
        raise Exception("Frontend build failed - no output directory found")
    
    # Create FastAPI app for serving static files
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    app.mount("/", StaticFiles(directory="out", html=True), name="static")
    return app

@app.local_entrypoint()
def main():
    print("Starting Cotomata deployment...")
    # Start backend in the background
    # start_backend.spawn()
    print("Your apps will be available at:")
    print("Frontend: https://sotopia-lab--cotomata-frontend.modal.run")
    print("Backend: https://sotopia-lab--cotomata-backend.modal.run")