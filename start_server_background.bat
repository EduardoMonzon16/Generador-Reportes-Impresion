@echo off
cd /d "C:\Users\MONZON\Documents\Python Proyectos\Reporte-de-Impresiones\"
echo Iniciando servidor...
if exist "run_server.py" (
    python run_server.py
) else (
    python -c "from app import app; app.run(debug=False, host='0.0.0.0', port=5001)"
)
