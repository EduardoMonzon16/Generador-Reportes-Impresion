"""
Archivo WSGI para servir la aplicación Flask con Waitress.
Este archivo permite ejecutar la aplicación en un servidor de producción.
"""
import os
import sys
from waitress import serve

# Asegurarse de que el directorio actual esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Importar la aplicación Flask
from app import app  # Asumiendo que tu archivo principal se llama app.py

# Configuración del servidor
HOST = '0.0.0.0'  # Permite conexiones desde cualquier IP
PORT = 5001       # Puerto por defecto
THREADS = 4       # Número de hilos para manejar requests

def create_app():
    """Función factory para crear la aplicación."""
    # Configuraciones adicionales para producción
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
    
    return app

if __name__ == '__main__':
    application = create_app()
    
    print(f"Iniciando servidor Waitress...")
    print(f"Aplicación disponible en: http://localhost:{PORT}")
    print(f"Para acceder desde otras máquinas: http://{HOST}:{PORT}")
    print("Presiona Ctrl+C para detener el servidor")
    
    try:
        serve(
            application,
            host=HOST,
            port=PORT,
            threads=THREADS,
            url_scheme='http',
            # Configuraciones adicionales de Waitress
            connection_limit=100,
            cleanup_interval=30,
            channel_timeout=120,
            log_socket_errors=True,
            # Configuración para archivos estáticos
            expose_tracebacks=False,
            # Configuración de timeout
            recv_bytes=65536,
            send_bytes=18000
        )
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")
        sys.exit(1)