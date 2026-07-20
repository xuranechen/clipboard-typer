@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "ENV_NAME=typer"
set "PYTHON_VER=3.12"
set "REQUIREMENTS=%~dp0requirements.txt"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
set "ENTRY=%~dp0main.py"
set "LOG_FILE=%~dp0start.log"
set "PYTHONUTF8=1"

> "%LOG_FILE%" echo ========================================
>> "%LOG_FILE%" echo   Clipboard Typer Starting...
>> "%LOG_FILE%" echo   Time: %DATE% %TIME%
>> "%LOG_FILE%" echo ========================================

echo ========================================
echo   Clipboard Typer Starting...
echo ========================================

echo.
echo [1/5] Checking Conda...
>> "%LOG_FILE%" echo.
>> "%LOG_FILE%" echo [1/5] Checking Conda...
where conda >nul 2>nul
if errorlevel 1 (
    echo   [ERROR] Conda not found. Please install Miniconda or Anaconda first.
    >> "%LOG_FILE%" echo   [ERROR] Conda not found. Please install Miniconda or Anaconda first.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('call conda --version 2^>^&1') do set "CONDA_VERSION=%%v"
echo   Found %CONDA_VERSION%
>> "%LOG_FILE%" echo   Found %CONDA_VERSION%

echo.
echo [2/5] Checking conda env "%ENV_NAME%"...
>> "%LOG_FILE%" echo.
>> "%LOG_FILE%" echo [2/5] Checking conda env "%ENV_NAME%"...
call conda env list | findstr /R /C:"^%ENV_NAME%[ ]" >nul 2>nul
if errorlevel 1 (
    echo   Env "%ENV_NAME%" not found, creating with Python %PYTHON_VER%...
    >> "%LOG_FILE%" echo   Env "%ENV_NAME%" not found, creating with Python %PYTHON_VER%...
    call conda create -y -n %ENV_NAME% python=%PYTHON_VER% pip >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo   [ERROR] Failed to create conda env "%ENV_NAME%". See start.log.
        pause
        exit /b 1
    )
    echo   Env created successfully.
    >> "%LOG_FILE%" echo   Env created successfully.
) else (
    echo   Env "%ENV_NAME%" exists, skip.
    >> "%LOG_FILE%" echo   Env "%ENV_NAME%" exists, skip.
)

echo.
echo [3/5] Verifying Python in env "%ENV_NAME%"...
>> "%LOG_FILE%" echo.
>> "%LOG_FILE%" echo [3/5] Verifying Python in env "%ENV_NAME%"...
call conda run -n %ENV_NAME% python --version >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo   [ERROR] Failed to run python in env "%ENV_NAME%". See start.log.
    pause
    exit /b 1
)
call conda run -n %ENV_NAME% python --version

echo.
echo [4/5] Checking dependencies...
>> "%LOG_FILE%" echo.
>> "%LOG_FILE%" echo [4/5] Checking dependencies...
if not exist "%REQUIREMENTS%" (
    echo   [ERROR] requirements.txt not found: %REQUIREMENTS%
    >> "%LOG_FILE%" echo   [ERROR] requirements.txt not found: %REQUIREMENTS%
    pause
    exit /b 1
)
call conda run -n %ENV_NAME% python -c "import pyperclip, pyautogui, pynput" >nul 2>nul
if errorlevel 1 (
    echo   Dependencies missing, installing from %MIRROR% ...
    >> "%LOG_FILE%" echo   Dependencies missing, installing from %MIRROR% ...
    call conda run -n %ENV_NAME% python -m pip install --upgrade pip -q -i %MIRROR% >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo   [ERROR] Failed to upgrade pip. See start.log.
        pause
        exit /b 1
    )
    call conda run -n %ENV_NAME% python -m pip install -r "%REQUIREMENTS%" -i %MIRROR% >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo   [ERROR] Dependency installation failed. See start.log.
        pause
        exit /b 1
    )
    echo   Dependencies installed.
    >> "%LOG_FILE%" echo   Dependencies installed.
) else (
    echo   All dependencies satisfied.
    >> "%LOG_FILE%" echo   All dependencies satisfied.
)

echo.
echo ========================================
echo   Clipboard Typer is starting...
echo   Conda env: %ENV_NAME%
echo   Log file: %LOG_FILE%
echo   Press Ctrl+C to stop if needed.
echo ========================================
echo.
>> "%LOG_FILE%" echo.
>> "%LOG_FILE%" echo ========================================
>> "%LOG_FILE%" echo   Clipboard Typer is starting...
>> "%LOG_FILE%" echo   Conda env: %ENV_NAME%
>> "%LOG_FILE%" echo ========================================

call conda run -n %ENV_NAME% python "%ENTRY%" >> "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo Clipboard Typer exited with code %EXIT_CODE%.
echo Log saved to %LOG_FILE%
echo Press any key to exit...
>> "%LOG_FILE%" echo.
>> "%LOG_FILE%" echo Clipboard Typer exited with code %EXIT_CODE%.
pause >nul
exit /b %EXIT_CODE%
