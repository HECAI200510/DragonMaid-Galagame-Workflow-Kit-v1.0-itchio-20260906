@echo off
setlocal
cd /d "%~dp0"

where pyw.exe >nul 2>nul
if %errorlevel%==0 (
  start "" pyw.exe -3 "batch_prompt_tool_v2.py"
  exit /b 0
)

where pythonw.exe >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw.exe "batch_prompt_tool_v2.py"
  exit /b 0
)

where py.exe >nul 2>nul
if %errorlevel%==0 (
  py.exe -3 "batch_prompt_tool_v2.py"
  exit /b %errorlevel%
)

python.exe "batch_prompt_tool_v2.py"
exit /b %errorlevel%
