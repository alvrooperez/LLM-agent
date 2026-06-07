@echo off
REM ============================================================================
REM AI Engineering Portfolio — Setup script
REM Verifica prerequisitos y arranca el stack completo.
REM
REM Uso:
REM   setup.bat                    (verificar + arrancar)
REM   setup.bat check              (solo verificar, no arranca nada)
REM   setup.bat bootstrap          (verificar + arrancar + poblar Qdrant)
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================
echo  AI Engineering Portfolio — Setup
echo ============================================================
echo.

set "ERRORS=0"
set "WARNINGS=0"

REM -- Check Docker --------------------------------------------------------
echo [1/6] Checking Docker...
where docker >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   FAIL: Docker not installed.
    echo   Install from: https://www.docker.com/products/docker-desktop
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('docker --version') do echo   OK: %%i
)

REM -- Check Docker Compose ------------------------------------------------
echo [2/6] Checking Docker Compose...
docker compose version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   FAIL: Docker Compose not available.
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('docker compose version') do echo   OK: %%i
)

REM -- Check NVIDIA driver + CUDA ----------------------------------------
echo [3/6] Checking NVIDIA driver...
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   FAIL: nvidia-smi not found.
    echo   Update driver: https://www.nvidia.com/Download/index.aspx
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('nvidia-smi --query-gpu=name --format=csv,noheader') do echo   OK: GPU %%i
)

REM -- Check Python --------------------------------------------------------
echo [4/6] Checking Python...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   FAIL: Python not installed.
    echo   Install from: https://www.python.org/downloads/
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('python --version') do echo   OK: %%i
)

REM -- Check Ollama reachable --------------------------------------------
echo [5/6] Checking Ollama (if running already)...
powershell -NoProfile -Command "try{$r=Invoke-WebRequest 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop;$r.Content|Out-Null;exit 0}catch{exit 1}" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   OK: Ollama reachable at http://localhost:11434
) else (
    echo   INFO: Ollama not running yet. Will be started by docker compose.
)

REM -- Check Docker NVIDIA runtime ----------------------------------------
echo [6/6] Checking Docker GPU passthrough...
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   WARN: Docker cannot access GPU. Will affect performance but stack will work.
    set /a WARNINGS+=1
) else (
    echo   OK: Docker can access GPU.
)

echo.
echo ============================================================
if %ERRORS% gtr 0 (
    echo  SETUP FAILED — %ERRORS% error^(s^), %WARNINGS% warning^(s^)
    echo ============================================================
    echo.
    echo Fix the errors above and run setup.bat again.
    echo.
    pause
    exit /b 1
) else (
    echo  SETUP OK — %WARNINGS% warning^(s^)
    echo ============================================================
)

REM -- If only check, stop here -------------------------------------------
if /i "%1"=="check" (
    echo.
    echo Check-only mode. Not starting services.
    exit /b 0
)

echo.
echo Starting stack with docker compose...
cd /d "%~dp0"
docker compose up -d

if %ERRORLEVEL% neq 0 (
    echo.
    echo FAIL: docker compose up failed.
    echo Run 'docker compose logs' to debug.
    pause
    exit /b 1
)

echo.
echo Stack started. Services:
echo   Ollama:    http://localhost:11434
echo   Qdrant:    http://localhost:6333
echo   RAG API:   http://localhost:8000
echo   Chat App:  http://localhost:8090

if /i "%1"=="bootstrap" (
    echo.
    echo Populating Qdrant with knowledge base...
    docker compose --profile bootstrap run --rm rag-bootstrap
)

echo.
echo Next steps:
echo   1. Download Ollama models:
echo      docker exec aieng-ollama ollama pull qwen2.5:3b
echo      docker exec aieng-ollama ollama pull qwen2.5-rag-ft
echo   2. Open the chat: http://localhost:8090
echo.
pause
