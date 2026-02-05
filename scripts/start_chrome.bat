@echo off
REM Close all Chrome windows first
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

REM Start Chrome with remote debugging enabled
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 "https://games.betfair.com/exchange-baccarat/standard/"

echo Chrome started with remote debugging on port 9222
echo You can now log in to Betfair
echo Keep this window open and run the betting script
pause
