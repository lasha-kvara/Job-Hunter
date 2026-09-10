@echo off
title LinkedIn Agent - Chrome/Brave Launcher (Port 9222)
echo ======================================================================
echo Starting Browser with Remote Debugging Port 9222 for LinkedIn Agent...
echo ======================================================================

set CHROME_PATH1="C:\Program Files\Google\Chrome\Application\chrome.exe"
set CHROME_PATH2="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set CHROME_PATH3="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
set BRAVE_PATH1="C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
set BRAVE_PATH2="%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"

set TARGET_EXE=""

if exist %BRAVE_PATH1% (
    set TARGET_EXE=%BRAVE_PATH1%
    echo Found Brave Browser at %BRAVE_PATH1%
) else if exist %BRAVE_PATH2% (
    set TARGET_EXE=%BRAVE_PATH2%
    echo Found Brave Browser at %BRAVE_PATH2%
) else if exist %CHROME_PATH1% (
    set TARGET_EXE=%CHROME_PATH1%
    echo Found Google Chrome at %CHROME_PATH1%
) else if exist %CHROME_PATH2% (
    set TARGET_EXE=%CHROME_PATH2%
    echo Found Google Chrome at %CHROME_PATH2%
) else if exist %CHROME_PATH3% (
    set TARGET_EXE=%CHROME_PATH3%
    echo Found Google Chrome at %CHROME_PATH3%
)

if %TARGET_EXE%=="" (
    echo [ERROR] Could not find Chrome or Brave executable automatically.
    echo Please start Chrome or Brave from command line with:
    echo chrome.exe --remote-debugging-port=9222
    pause
    exit /b 1
)

set PROFILE_DIR="%LOCALAPPDATA%\LinkedInAgent_Profile"

echo Launching browser with --remote-debugging-port=9222 and persistent profile...
start "" %TARGET_EXE% --remote-debugging-port=9222 --user-data-dir=%PROFILE_DIR% "https://www.linkedin.com/feed/"
echo Browser started with persistent profile at %PROFILE_DIR%!
echo Your LinkedIn session will remain logged in across sessions.
