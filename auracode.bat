@echo off
:: AuraCode global launcher
:: Finds the project and starts AuraCode in a new terminal window
set "AURINE_DIR=%~dp0"
if exist "%AURINE_DIR%.venv\Scripts\python.exe" (
    start cmd /k "cd /d "%AURINE_DIR%" && ".venv\Scripts\python.exe" auracode.py"
) else if exist "%USERPROFILE%\aurine-ai-assistant\.venv\Scripts\python.exe" (
    start cmd /k "cd /d "%USERPROFILE%\aurine-ai-assistant" && ".venv\Scripts\python.exe" auracode.py"
) else (
    echo AuraCode not found. Run setup first.
    pause
)
