@echo off
REM Start script for the MongoDB Atlas Search API on Windows

REM Check if Docker is installed
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Docker is not installed. Please install Docker first.
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit the .env file with your MongoDB Atlas credentials if needed.
)

REM Build and start the containers
echo Building and starting containers...
docker-compose up -d --build

REM Wait for the containers to be ready
echo Waiting for API to be ready...
timeout /t 5 /nobreak >nul

REM Check if the API is healthy
echo Checking API health...
curl -s http://localhost:8000/health > health.tmp
findstr "healthy" health.tmp >nul
if %ERRORLEVEL% EQU 0 (
    echo API is healthy and ready to use!
    echo API documentation available at: http://localhost:8000/docs
    echo.
    echo Loading sample data (optional)...
    echo To load sample data, run: cd test_data ^&^& python load_test_data.py
    echo.
    echo To stop the application, run: docker-compose down
) else (
    echo API is not responding. Please check the logs for issues:
    echo docker-compose logs -f app
)

REM Clean up temporary file
del health.tmp
