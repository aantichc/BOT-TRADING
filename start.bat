@echo off
setlocal EnableDelayedExpansion

:: Configuración
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "RUN_SCRIPT=%SCRIPT_DIR%run.py"

:: Cambiar al directorio del script
cd /d "%SCRIPT_DIR%"

:: Título de la ventana
title Crypto Trading Bot

echo [INFO] Iniciando Crypto Trading Bot...
echo [INFO] Directorio: %SCRIPT_DIR%
echo.

:: Verificar existencia del entorno virtual
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Entorno virtual no encontrado en: %VENV_DIR%
    echo [INFO] Creando entorno virtual...
    python -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual
        echo [INFO] Asegurate de tener Python instalado
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
)

:: Verificar si run.py existe
if not exist "%RUN_SCRIPT%" (
    echo [ERROR] No se encuentra run.py en: %RUN_SCRIPT%
    pause
    exit /b 1
)

:: Ejecutar la aplicación
echo [OK] Ejecutando aplicacion...
echo.
"%PYTHON_EXE%" "%RUN_SCRIPT%"

:: Pausar al finalizar
echo.
echo [INFO] Aplicacion finalizada
pause
