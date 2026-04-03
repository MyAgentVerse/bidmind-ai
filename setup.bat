@echo off
REM BidMind AI Backend Setup Script for Windows

setlocal enabledelayedexpansion

echo.
echo 🚀 BidMind AI Backend Setup
echo ================================
echo.

REM Check Python version
echo ✓ Checking Python version...
python --version

REM Create virtual environment
if not exist "venv" (
    echo ✓ Creating virtual environment...
    python -m venv venv
) else (
    echo ✓ Virtual environment already exists
)

REM Activate virtual environment
echo ✓ Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ✓ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo ✓ Installing dependencies...
pip install -r requirements.txt

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo ✓ Creating .env file from template...
    copy .env.example .env
    echo.
    echo ⚠️  Please edit .env with your configuration (especially OPENAI_API_KEY and DATABASE_URL)
) else (
    echo ✓ .env file already exists
)

REM Create uploads directory
echo ✓ Creating uploads directory...
if not exist "uploads" mkdir uploads

REM Print next steps
echo.
echo ================================
echo ✅ Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Configure your .env file:
echo    - Set OPENAI_API_KEY
echo    - Set DATABASE_URL (PostgreSQL connection string)
echo    - Adjust other settings as needed
echo.
echo 2. Set up the database:
echo    - Ensure PostgreSQL is running
echo    - Run: alembic upgrade head
echo.
echo 3. Start the development server:
echo    - Run: uvicorn app.main:app --reload
echo    - Visit: http://localhost:8000/api/docs
echo.
echo For more information, see README.md
echo.

pause
