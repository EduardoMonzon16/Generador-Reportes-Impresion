@echo off
setlocal enabledelayedexpansion

REM ================================
REM SERVIDOR DE REPORTES - INICIO AUTOMÁTICO
REM ================================

REM Definir rutas
set PROYECTO_DIR=C:\Users\MONZON\Documents\Python Proyectos\Reporte-de-Impresiones
set LOG_FILE=%USERPROFILE%\Desktop\servidor_reportes.log

REM Limpiar log anterior y crear nuevo
echo. > "%LOG_FILE%"
echo ================================ >> "%LOG_FILE%"
echo SERVIDOR DE REPORTES - LOG DE INICIO >> "%LOG_FILE%"
echo Fecha: %date% %time% >> "%LOG_FILE%"
echo ================================ >> "%LOG_FILE%"

REM Función para escribir en log y consola
set "log_and_show=echo [%time%] "

REM Mostrar información inicial
%log_and_show% Iniciando servidor de reportes...
echo [%time%] Iniciando servidor de reportes... >> "%LOG_FILE%"

REM Esperar que el sistema termine de cargar
%log_and_show% Esperando carga del sistema (10 segundos)...
echo [%time%] Esperando carga del sistema... >> "%LOG_FILE%"
timeout /t 10 /nobreak >nul

REM Verificar ruta del proyecto
%log_and_show% Verificando directorio del proyecto...
echo [%time%] Verificando directorio: %PROYECTO_DIR% >> "%LOG_FILE%"

if not exist "%PROYECTO_DIR%" (
    %log_and_show% ERROR: No se encuentra la carpeta del proyecto
    echo [%time%] ERROR: Carpeta no encontrada >> "%LOG_FILE%"
    echo Presiona cualquier tecla para salir...
    pause >nul
    exit /b 1
)

REM Cambiar al directorio del proyecto
cd /d "%PROYECTO_DIR%"
%log_and_show% Directorio cambiado a: %CD%
echo [%time%] Directorio actual: %CD% >> "%LOG_FILE%"

REM Verificar Python
%log_and_show% Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    %log_and_show% ERROR: Python no disponible
    echo [%time%] ERROR: Python no encontrado >> "%LOG_FILE%"
    echo.
    echo Posibles soluciones:
    echo 1. Instalar Python desde python.org
    echo 2. Agregar Python al PATH del sistema
    echo.
    echo Presiona cualquier tecla para salir...
    pause >nul
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do (
        %log_and_show% Python encontrado: %%i
        echo [%time%] Python: %%i >> "%LOG_FILE%"
    )
)

REM Mostrar archivos Python disponibles
%log_and_show% Archivos Python en el directorio:
echo [%time%] Listando archivos .py: >> "%LOG_FILE%"
dir /b *.py >> "%LOG_FILE%" 2>&1

REM Buscar archivo del servidor
set ARCHIVO_SERVIDOR=
if exist "run_server.py" (
    set ARCHIVO_SERVIDOR=run_server.py
) else if exist "server.py" (
    set ARCHIVO_SERVIDOR=server.py
) else if exist "app.py" (
    set ARCHIVO_SERVIDOR=app.py
) else if exist "main.py" (
    set ARCHIVO_SERVIDOR=main.py
)

if "%ARCHIVO_SERVIDOR%"=="" (
    %log_and_show% ERROR: No se encuentra archivo del servidor
    echo [%time%] ERROR: Archivo servidor no encontrado >> "%LOG_FILE%"
    echo.
    echo Archivos buscados: run_server.py, server.py, app.py, main.py
    echo.
    echo Presiona cualquier tecla para salir...
    pause >nul
    exit /b 1
)

%log_and_show% Archivo servidor: !ARCHIVO_SERVIDOR!
echo [%time%] Archivo servidor: !ARCHIVO_SERVIDOR! >> "%LOG_FILE%"

REM Verificar puerto 5001
%log_and_show% Verificando puerto 5001...
netstat -an | find ":5001" | find "LISTENING" >nul 2>&1
if not errorlevel 1 (
    %log_and_show% Puerto 5001 ocupado, liberando...
    echo [%time%] Puerto 5001 ocupado, cerrando procesos >> "%LOG_FILE%"
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
)

REM Verificar dependencias
%log_and_show% Verificando dependencias...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    %log_and_show% Instalando Flask...
    echo [%time%] Instalando Flask... >> "%LOG_FILE%"
    python -m pip install flask --quiet --user
)

python -c "import waitress" >nul 2>&1
if errorlevel 1 (
    %log_and_show% Instalando Waitress...
    echo [%time%] Instalando Waitress... >> "%LOG_FILE%"
    python -m pip install waitress --quiet --user
)

%log_and_show% Dependencias verificadas
echo [%time%] Dependencias OK >> "%LOG_FILE%"

REM Intentar iniciar el servidor directamente primero
%log_and_show% Iniciando servidor...
echo [%time%] Iniciando servidor: !ARCHIVO_SERVIDOR! >> "%LOG_FILE%"

REM Crear comando de inicio
set START_CMD=python "!ARCHIVO_SERVIDOR!"

REM Iniciar servidor en segundo plano
start "Servidor Reportes" /min cmd /c "cd /d "%PROYECTO_DIR%" && %START_CMD%"

REM Esperar y verificar inicio
%log_and_show% Verificando inicio del servidor...
set SERVIDOR_OK=0
for /L %%i in (1,1,15) do (
    timeout /t 2 /nobreak >nul
    netstat -an | find ":5001" | find "LISTENING" >nul 2>&1
    if not errorlevel 1 (
        set SERVIDOR_OK=1
        goto :servidor_iniciado
    )
    %log_and_show% Esperando... %%i/15
)

:servidor_iniciado
if !SERVIDOR_OK!==1 (
    %log_and_show% ✅ Servidor iniciado correctamente
    echo [%time%] ✅ Servidor funcionando en puerto 5001 >> "%LOG_FILE%"
    echo.
    echo ================================
    echo   ✅ SERVIDOR FUNCIONANDO
    echo ================================
    echo   URL: http://localhost:5001
    echo   Log: %LOG_FILE%
    echo ================================
) else (
    %log_and_show% ⚠ Servidor no responde en puerto 5001
    echo [%time%] ⚠ Timeout - servidor no responde >> "%LOG_FILE%"
    echo.
    echo Revisa el log en: %LOG_FILE%
    echo Intenta acceder manualmente a: http://localhost:5001
)

echo.
echo Esta ventana se cerrará en 10 segundos...
echo (Presiona cualquier tecla para cerrar ahora)
timeout /t 10

exit /b 0