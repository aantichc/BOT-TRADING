# run.py
import os
import sys

# Añade la carpeta raíz del proyecto (donde está src) al path
# Esto es clave en Windows
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
sys.path.insert(0, src_path)

# Ahora sí puede importar desde src
from main import main

if __name__ == "__main__":
    main()