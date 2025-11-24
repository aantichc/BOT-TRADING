# run.py - VERSIÓN CON CIERRE MEJORADO
import os
import sys
import signal

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def signal_handler(sig, frame):
    """Manejar Ctrl+C"""
    print('\nCerrando aplicación...')
    sys.exit(0)

def main():
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        from main import main as app_main
        app_main()
    except KeyboardInterrupt:
        print('\nAplicación interrumpida por el usuario')
        sys.exit(0)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()