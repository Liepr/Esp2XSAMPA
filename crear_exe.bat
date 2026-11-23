@echo off
REM Compila Esp2XSAMPA.py a Esp2XSAMPA.exe (con ventana, sin consola)
REM Pone este archivo en la misma carpeta que Esp2XSAMPA.py y Esp2XSAMPA.ico, y hace doble clic.
cd /d "%~dp0"

python --version
if errorlevel 1 (
    echo.
    echo [ERROR] No se encontro Python. Instalalo desde python.org y marca "Add Python to PATH".
    pause
    exit /b 1
)

if not exist Esp2XSAMPA.ico (
    echo.
    echo [ERROR] Falta Esp2XSAMPA.ico. Ponelo en la misma carpeta que Esp2XSAMPA.py.
    pause
    exit /b 1
)

python -m pip install --upgrade pynput pystray pillow pyinstaller
if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la instalacion de las dependencias.
    pause
    exit /b 1
)

python -m PyInstaller --onefile --noconsole --uac-admin --icon Esp2XSAMPA.ico --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 --hidden-import pystray._win32 --name Esp2XSAMPA Esp2XSAMPA.py
if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la compilacion. Revisa los mensajes de arriba.
    echo Si el error menciona tkinter, reinstala Python marcando "tcl/tk and IDLE".
    pause
    exit /b 1
)

echo.
echo Listo. El ejecutable esta en: %~dp0dist\Esp2XSAMPA.exe
pause
