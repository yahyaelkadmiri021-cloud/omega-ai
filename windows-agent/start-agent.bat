@echo off
REM OMEGA AI - Windows agent launcher (double-click to run)
REM 1) Checks Python (downloads and installs it silently if missing)
REM 2) Installs requirements (PyAutoGUI)
REM 3) Binds the agent to this machine's Tailscale IP (so Muse can reach it)
REM 4) Reuses token.txt if it exists and is non-empty, otherwise creates a token and saves it there
REM 5) Starts agent.py (stop with Ctrl+C). Keep this window open.
cd /d %~dp0

echo Checking Python...
python --version >nul 2>&1
if not errorlevel 1 goto :python_ok
echo Python is not installed. Downloading the Python installer...
curl -L -o "%TEMP%\python-installer.exe" https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
if not exist "%TEMP%\python-installer.exe" (
  echo Download failed. Please install Python from https://www.python.org/downloads/ and run this file again.
  pause
  exit /b 1
)
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
del "%TEMP%\python-installer.exe" 2>nul
echo Re-checking Python...
python --version >nul 2>&1
if not errorlevel 1 goto :python_ok
echo Python still not found. Please install it from https://www.python.org/downloads/ and run this file again.
pause
exit /b 1

:python_ok
echo Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo pip install failed. Check your internet connection and run this file again.
  pause
  exit /b 1
)

REM Tailscale IP (so Muse can reach the agent over the tailnet)
for /f "delims=" %%I in ('tailscale ip -4 2^>nul') do set MUSE_AGENT_HOST=%%I
if "%MUSE_AGENT_HOST%"=="" set MUSE_AGENT_HOST=127.0.0.1

REM Token: reuse token.txt if it exists and is non-empty, otherwise create one
if not exist token.txt goto :make_token
set /p MUSE_AGENT_TOKEN=<token.txt
if not "%MUSE_AGENT_TOKEN%"=="" goto :have_token
:make_token
for /f "delims=" %%T in ('powershell -NoProfile -Command "$t = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_}); $t | Out-File -FilePath token.txt -Encoding ascii -NoNewline; $t"') do set MUSE_AGENT_TOKEN=%%T
:have_token

echo.
echo ============================================================
echo  OMEGA Windows agent is starting.
echo  Listening on: http://%MUSE_AGENT_HOST%:8472
echo  Agent token (send this ONE line to Muse so it can connect):
echo  %MUSE_AGENT_TOKEN%
echo  The token only works inside your private Tailscale network.
echo  Keep this window open. Stop the agent with Ctrl+C.
echo ============================================================
echo.
python agent.py
pause
