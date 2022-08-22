pyinstaller .\gui.py --icon=icon.ico -F -w
MOVE /Y dist\gui.exe lpis.exe
DEL /F /A gui.spec
RD /S /Q dist
RD /S /Q build