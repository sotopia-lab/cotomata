from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WriteRequest(BaseModel):
    content: str

class BashRequest(BaseModel):
    command: str

@app.get("/")
async def health_check():
    return "I am alive"

@app.get("/read/{path:path}")
async def read_file(path: str):
    try:
        with open(f"/workspace/{path}", "r") as f:
            return {"content": f.read()}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/write/{path:path}")
async def write_file(path: str, request: WriteRequest):
    try:
        os.makedirs(os.path.dirname(f"/workspace/{path}"), exist_ok=True)
        with open(f"/workspace/{path}", "w") as f:
            f.write(request.content)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bash")
async def execute_bash(request: BashRequest):
    try:
        result = subprocess.run(
            request.command,
            shell=True,
            cwd="/workspace",
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
