#!/usr/bin/env python3
"""
Script simple para ejecutar el servidor de la aplicación Flask.
Ejecuta: python run_server.py
"""
import os
import sys
from waitress import serve

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar la aplicación
try:
    from app import app
except ImportError as e:
    print(f"Error: No se pudo importar la aplicación Flask: {e}")
    print("Asegúrate de que el archivo 'app.py' esté en el mismo directorio.")
    sys.exit(1)

# Configuración
HOST = '0.0.0.0'
PORT = 5001

def main():
    """Función principal para ejecutar el servidor."""
    print("=" * 60)
    print("🚀 SERVIDOR DE REPORTES DE IMPRESIÓN")
    print("=" * 60)
    print(f"📍 Servidor iniciando en: http://localhost:{PORT}")
    print(f"🌐 Acceso desde red local: http://{get_local_ip()}:{PORT}")
    print("⏹️  Para detener: Ctrl+C")
    print("=" * 60)
    
    try:
        # Configurar aplicación para producción
        app.config['ENV'] = 'production'
        app.config['DEBUG'] = False
        
        # Ejecutar servidor Waitress
        serve(
            app,
            host=HOST,
            port=PORT,
            threads=4,
            connection_limit=100,
            cleanup_interval=30,
            channel_timeout=120
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Servidor detenido por el usuario.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Error: El puerto {PORT} ya está en uso.")
            print("   Intenta usar un puerto diferente o detén el otro proceso.")
        else:
            print(f"❌ Error del sistema: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    finally:
        print("👋 ¡Hasta luego!")

def get_local_ip():
    """Obtiene la IP local de la máquina."""
    import socket
    try:
        # Conectar a una dirección externa para obtener la IP local
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"

if __name__ == '__main__':
    main()