@echo off
cd /d "C:\Users\eduardo.monzon\Documents\Proyectos Python Forvis Mazars\Generador-Reportes-Impresion\"
echo Iniciando servidor...
if exist "run_server.py" (
    py run_server.py
) else (
    py -c "from app import app; app.run(debug=False, host='0.0.0.0', port=5001)"
)
