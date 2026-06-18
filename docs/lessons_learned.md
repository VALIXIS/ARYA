# Lessons Learned

## What worked

- Keeping project notes in `docs/` made the setup and design decisions easier to find.
- Breaking the project into focused documents helped separate architecture, roadmap, memory design, and task tracking.
- Using small, clear setup steps made problems easier to isolate.

## Problems faced

- Some dependencies were missing during setup.
- Python modules needed by the project were not always installed in the active environment.
- Environment setup can fail silently if the wrong terminal, Python version, or virtual environment is being used.

## Setup commands

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Fixes

- If the `requests` module is missing, install it with:

```powershell
python -m pip install requests
```

- If dependencies are listed in `requirements.txt`, reinstall them with:

```powershell
python -m pip install -r requirements.txt
```

- If PowerShell blocks virtual environment activation, allow scripts for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
