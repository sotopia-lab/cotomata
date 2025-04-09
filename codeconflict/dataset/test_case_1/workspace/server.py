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
    start_line: int | None = None
    end_line: int | None = None

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
        file_path = f"/workspace/{path}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if request.start_line is not None and request.end_line is not None:
            # Read existing content
            lines = []
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    lines = f.readlines()

            # Extend lines list if needed
            while len(lines) < request.end_line + 1:
                lines.append("\n")

            # Replace specified lines
            new_lines = request.content.splitlines(True)
            lines[request.start_line:request.end_line + 1] = new_lines

            # Write back all content
            with open(file_path, "w") as f:
                f.writelines(lines)
        else:
            # Original behavior: overwrite entire file
            with open(file_path, "w") as f:
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
