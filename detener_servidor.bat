@echo off
echo ================================
echo   DETENER SERVIDOR DE REPORTES
echo ================================
echo.

echo Buscando procesos Python en puerto 5001...

REM Encontrar el PID del proceso que usa el puerto 5001
for /f "tokens=5" %%a in ('netstat -ano ^| find ":5001" ^| find "LISTENING"') do (
    echo Proceso encontrado con PID: %%a
    taskkill /PID %%a /F
    if not errorlevel 1 (
        echo ✅ Servidor detenido correctamente
    ) else (
        echo ❌ Error al detener el servidor
    )
)

REM También detener todos los procesos Python como medida adicional
echo.
echo Deteniendo todos los procesos Python...
taskkill /f /im python.exe >nul 2>&1
if not errorlevel 1 (
    echo ✅ Procesos Python detenidos
) else (
    echo ℹ No se encontraron procesos Python adicionales
)

echo.
echo ================================
echo   SERVIDOR DETENIDO
echo ================================
pause