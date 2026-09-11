import subprocess
import tempfile
import os
from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolParam, ParamType, ToolCategory, ToolResult

def _run_powershell(params: dict) -> ToolResult:
    command = params.get("command", "")
    if not command:
        return ToolResult(False, "No command provided.", data={})
    
    try:
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=15)
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        msg = f"Executed PowerShell command. Output: {output}" if output else "Executed successfully."
        if error and result.returncode != 0:
            return ToolResult(False, f"Command failed: {error}", data={"output": output, "error": error})
        return ToolResult(True, msg, data={"output": output})
    except Exception as e:
        return ToolResult(False, f"Execution error: {e}", data={})

def _execute_python(params: dict) -> ToolResult:
    code = params.get("code", "")
    if not code:
        return ToolResult(False, "No Python code provided.", data={})
    
    try:
        fd, path = tempfile.mkstemp(suffix=".py")
        with os.fdopen(fd, 'w', encoding="utf-8") as f:
            f.write(code)
            
        result = subprocess.run(["python", path], capture_output=True, text=True, timeout=15)
        os.remove(path)
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        msg = f"Executed Python script. Output: {output}" if output else "Python script executed successfully."
        if error and result.returncode != 0:
            return ToolResult(False, f"Python execution failed: {error}", data={"output": output, "error": error})
        return ToolResult(True, msg, data={"output": output})
    except Exception as e:
        return ToolResult(False, f"Execution error: {e}", data={})

registry.register(
    schema=ToolSchema(
        name="run_powershell",
        description="Execute a terminal command directly in Windows PowerShell.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("command", ParamType.STRING, "The shell command to run.", required=True)],
        examples=["run powershell command dir", "delete file on desktop"]
    ),
    handler=_run_powershell,
)

registry.register(
    schema=ToolSchema(
        name="execute_python",
        description="Write and execute a Python script natively on the host machine.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("code", ParamType.STRING, "The complete python code to run.", required=True)],
        examples=["write a python script to scrape news", "calculate prime numbers in python"]
    ),
    handler=_execute_python,
)
