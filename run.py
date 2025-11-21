import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import main

if __name__ == "__main__":
    print("🚀 Iniciando Trading Bot con USDC...")
    main()