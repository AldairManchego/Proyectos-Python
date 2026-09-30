@echo off
REM =========================================================
REM  Ejecutor de main.py - Proyecto Pcol
REM =========================================================

REM Ruta base del proyecto
set "PROYECTO=C:\Users\aldair.manchego\OneDrive - Concentrix Corporation\11. Proyecto_Pcol"

REM Ruta del entorno virtual
set "VENV=%PROYECTO%\01. Amazon_Connect\.venv"

echo ===========================================
echo   Iniciando proceso Pcol
echo ===========================================
echo.

REM Activar el entorno virtual
call "%VENV%\Scripts\activate.bat"

if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo activar el entorno virtual.
    echo Verifica que exista: %VENV%\Scripts\activate.bat
    pause
    exit /b 1
)

echo Entorno virtual activado: %VENV%
echo.

REM Ir a la carpeta del proyecto y ejecutar main.py
cd /d "%PROYECTO%"
python "main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] El script main.py finalizo con errores.
    echo Revisa el mensaje de arriba para mas detalle.
    pause
    exit /b 1
)

echo.
echo ===========================================
echo   Proceso finalizado correctamente
echo ===========================================
pause
