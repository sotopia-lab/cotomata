import modal
import os
from pathlib import Path

app = modal.App("cotomata")

# Create the base image with common dependencies
base_image = modal.Image.debian_slim().pip_install(
    "fastapi",
    "uvicorn"
).apt_install(
    "curl",
    "wget",
    "gnupg2"
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
    
    # List files to verify the mount
    print("\nContents of /root/frontend:")
    os.system("ls -la /root/frontend")
    
    # Build the project
    print("\nBuilding the project...")
    try:
        # First ensure next.config.mjs is correct
        print("\nContents of next.config.mjs:")
        with open("next.config.mjs", "r") as f:
            print(f.read())
        
        # Run the build
        build_output = subprocess.check_output(["bun", "run", "build"], stderr=subprocess.STDOUT)
        print("Build output:", build_output.decode())
    except subprocess.CalledProcessError as e:
        print("Build error output:", e.output.decode())
        raise Exception("Build command failed")
    
    print("\nContents of /root/frontend after build:")
    os.system("ls -la /root/frontend")
    
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
    print("Starting Cotomata frontend deployment...")
    print("Frontend will be available at: https://sotopia-lab--cotomata-frontend.modal.run")
    print("Make sure to start the backend locally with: cd backend && bun run dev")