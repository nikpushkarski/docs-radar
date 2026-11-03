@echo off
rem Use scripts\start.cmd explicitly: bare start is a built-in cmd command.
if not exist "%~dp0..\.venv\Scripts\activate.bat" (
    echo [docs-radar] No .venv found. From the repository folder, run: py -m venv .venv
    exit /b 1
)
call "%~dp0..\.venv\Scripts\activate.bat"
echo [docs-radar] Activated this project's .venv in the current terminal.
echo Python and pip now use project-local packages to avoid conflicts with other projects.
echo This does not start the app or limit system resources. Run deactivate to leave.
