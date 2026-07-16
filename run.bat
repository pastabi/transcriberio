@echo off
echo 🚀 Starting Transcriberio...

:: 1. Automatically build virtual environment folder if it doesn't exist yet
if not exist .venv (
    echo 📦 Creating local Python virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment. Ensure Python is installed.
        pause
        exit /b 1
    )
)

:: 2. Activate the virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment.
    pause
    exit /b 1
)

:: 3. Quietly ensure all dependencies are completely up to date
echo 📥 Syncing project libraries...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies.
    pause
    exit /b 1
)

:: 4. Spin up the application UI server
echo 🖥️  Launching browser dashboard...
python main.py

pause