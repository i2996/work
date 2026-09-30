@echo off
pip install -r requirements.txt pyinstaller
pyinstaller --noconsole --onefile --name WorkSpace --collect-all holidays work_space.py
echo.
echo dist\WorkSpace.exe 가 생성되었습니다.
pause
