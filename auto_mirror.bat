@echo off
title Galaxy S9+ Auto-Connect & Mirror
echo ========================================================
echo   Galaxy S9+ Instant Mirror Listener (SM-G965F)
echo ========================================================
echo.
echo Phone detected: 22858e1e40047ece
echo Waiting for RSA authorization prompt to be accepted...
echo.
echo Tap the screen: slightly below the vertical center, towards the right side.
echo.

:loop
"%~dp0..\scrcpy-win64-v3.3.4\adb.exe" devices | findstr /R /C:"22858e1e40047ece.*device$" >nul
if not errorlevel 1 (
    echo.
    echo ========================================================
    echo   DEVICE AUTHORIZED! Launching live mirror now...
    echo ========================================================
    echo.
    "%~dp0..\scrcpy-win64-v3.3.4\scrcpy.exe" -s 22858e1e40047ece --stay-awake --turn-screen-off --window-title "Galaxy S9+ (SM-G965F)"
    goto done
)

timeout /t 1 /nobreak >nul
goto loop

:done
pause
