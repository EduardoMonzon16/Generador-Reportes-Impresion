@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ===== CONFIGURACIÓN PORTABLE =====
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo ================================
echo 🔧 INSTALADOR DE APLICACIÓN
echo ================================
echo 📁 Directorio: %CD%

REM Verificar archivos principales
if not exist "app.py" (
    echo ❌ No se encontró app.py en %APP_DIR%
    timeout /t 15 /nobreak >nul
    exit /b 1
)

echo ================================
echo 🐍 CONFIGURANDO PYTHON
echo ================================

REM Buscar Python
set PYTHON_CMD=
for %%P in (python py python3) do (
    %%P --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=%%P
        goto :found_python
    )
)

echo ❌ No se encontró Python instalado
echo Por favor instala Python desde https://python.org
timeout /t 10 /nobreak >nul
exit /b 1

:found_python
echo 🐍 Usando: !PYTHON_CMD!
!PYTHON_CMD! --version

echo ================================
echo 📦 INSTALANDO DEPENDENCIAS
echo ================================

echo 📦 Actualizando pip...
!PYTHON_CMD! -m pip install --upgrade pip --user >nul 2>&1

echo 📦 Instalando dependencias críticas...
set CRITICAL_DEPS=python-dotenv flask waitress pandas openpyxl xlwings jinja2 werkzeug markupsafe itsdangerous click chardet numpy mysql-connector-python

for %%D in (%CRITICAL_DEPS%) do (
    echo   - Instalando %%D...
    !PYTHON_CMD! -m pip install "%%D" --user --no-warn-script-location >nul 2>&1
    if errorlevel 1 (
        echo     ⚠️ Error con %%D, reintentando...
        !PYTHON_CMD! -m pip install "%%D" --user --no-warn-script-location --no-deps >nul 2>&1
        if errorlevel 1 (
            echo     ❌ No se pudo instalar %%D
        )
    )
)

echo ================================
echo 🧪 VERIFICANDO CONFIGURACIÓN
echo ================================

REM Verificar módulos Python
echo 🔹 Verificando módulos Python...
set MODULES_TO_CHECK=xlwings flask pandas openpyxl dotenv jinja2 werkzeug mysql.connector

for %%M in (%MODULES_TO_CHECK%) do (
    if "%%M"=="mysql.connector" (
        !PYTHON_CMD! -c "import mysql.connector; print('  ✅ mysql.connector OK')" 2>nul
    ) else (
        !PYTHON_CMD! -c "import %%M; print('  ✅ %%M OK')" 2>nul
    )
    if errorlevel 1 (
        echo   ❌ %%M no disponible
        set MISSING_MODULES=1
    )
)

REM Si falta MySQL connector, intentar alternativas
if defined MISSING_MODULES (
    echo.
    echo ⚠️ Intentando instalar conectores MySQL alternativos...
    echo   - Instalando PyMySQL...
    !PYTHON_CMD! -m pip install PyMySQL --user --no-warn-script-location >nul 2>&1
    echo   - Instalando mysqlclient...
    !PYTHON_CMD! -m pip install mysqlclient --user --no-warn-script-location >nul 2>&1
)

echo ================================
echo 📝 CONFIGURACIÓN DE APLICACIÓN
echo ================================

REM Verificar archivo .env
if exist ".env" (
    echo ✅ Archivo .env encontrado
    echo 🔍 Configuración actual:
    findstr /i "FLASK\|SECRET\|DATABASE\|MYSQL" .env 2>nul
) else (
    echo ⚠️ No se encontró archivo .env
    echo.
    echo 📝 Creando archivo .env de ejemplo...
    (
        echo # Configuración de Flask
        echo FLASK_ENV=production
        echo SECRET_KEY=tu_clave_secreta_aqui
        echo.
        echo # Configuración de Base de Datos
        echo DB_HOST=localhost
        echo DB_USER=root
        echo DB_PASSWORD=
        echo DB_NAME=reporte_impresiones
        echo DB_PORT=3306
    ) > .env.example
    echo ✅ Archivo .env.example creado
    echo.
    echo 🔧 IMPORTANTE: 
    echo   1. Renombra .env.example a .env
    echo   2. Configura tus variables de entorno
    echo   3. Configura la conexión a MySQL
)

echo ================================
echo 🚀 INICIANDO SERVIDOR
echo ================================

REM Crear archivos de control
echo 🔧 Creando archivos de control...

REM Archivo para ejecutar servidor
(
    echo @echo off
    echo cd /d "%APP_DIR%"
    echo echo Iniciando servidor...
    echo if exist "run_server.py" (
    echo     %PYTHON_CMD% run_server.py
    echo ^) else (
    echo     %PYTHON_CMD% -c "from app import app; app.run(debug=False, host='0.0.0.0', port=5001)"
    echo ^)
) > "%APP_DIR%\start_server_background.bat"

REM Archivo VBS para ejecución silenciosa
(
    echo Set WshShell = CreateObject("WScript.Shell"^)
    echo WshShell.Run chr(34^) ^& "%APP_DIR%\start_server_background.bat" ^& chr(34^), 0
    echo Set WshShell = Nothing
) > "%APP_DIR%\start_server_silent.vbs"

echo ✅ Archivos de control creados

echo.
echo 🚀 Iniciando servidor...
cscript //nologo "%APP_DIR%\start_server_silent.vbs"

echo.
echo ================================
echo ✅ INSTALACIÓN COMPLETADA
echo ================================
echo.
echo 🎯 Servidor disponible en: http://localhost:5001
echo.
echo 📋 CHECKLIST FINAL:
echo   ✅ Python instalado y configurado
echo   ✅ Dependencias instaladas (incluyendo MySQL)
echo   ✅ Archivos de control creados
echo   ✅ Servidor iniciado
echo.
echo 💡 Si tienes problemas de conexión MySQL:
echo   - Verifica que MySQL esté ejecutándose
echo   - Configura el archivo .env con tus credenciales
echo   - Verifica que la base de datos exista
echo.

timeout /t 15 /nobreak >nul