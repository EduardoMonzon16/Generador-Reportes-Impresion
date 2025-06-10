@echo off
echo ================================
echo 🛑 DETENER SERVIDOR DE REPORTES
echo ================================
echo.
echo Buscando procesos en puerto 5001...

REM Encontrar y detener procesos en puerto 5001
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| find ":5001" ^| find "LISTENING"') do (
    echo Proceso encontrado con PID: %%a
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo ✅ Servidor detenido correctamente
    ) else (
        echo ❌ Error al detener el servidor
    )
)

REM Detener procesos Python adicionales
echo.
echo Deteniendo procesos Python relacionados...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1

echo.
echo ✅ Servidor en puerto 5001 detenido
echo ================================
timeout /t 2 /nobreak >nul
exit