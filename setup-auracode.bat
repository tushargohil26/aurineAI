@echo off
:: AuraCode PATH Setup - Run once to enable 'auracode' command globally
echo.
echo   AuraCode - Adding to PATH...
echo.

set "SCRIPT_DIR=%~dp0"
set "BAT_FILE=%SCRIPT_DIR%auracode.bat"

:: Copy auracode.bat to a permanent location
set "INSTALL_DIR=%USERPROFILE%\.auracode"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "%BAT_FILE%" "%INSTALL_DIR%\auracode.bat" >nul 2>&1

:: Add to user PATH if not already there
echo %PATH% | findstr /I "%INSTALL_DIR%" >nul 2>&1
if errorlevel 1 (
    :: Use setx to permanently add to user PATH
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CURRENT_PATH=%%b"
    if defined CURRENT_PATH (
        setx PATH "%CURRENT_PATH%;%INSTALL_DIR%" >nul 2>&1
    ) else (
        setx PATH "%INSTALL_DIR%" >nul 2>&1
    )
    echo   Added to PATH: %INSTALL_DIR%
    echo.
    echo   Done! Open a NEW terminal and type: auracode
) else (
    echo   Already in PATH.
    echo.
    echo   Type: auracode
)

echo.
pause
