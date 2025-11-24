# main.py - VERSIÓN CON MANEJO DE CIERRE
from gui import TradingGUI
from trading_bot import TradingBot
import sys
import traceback

def main():
    try:
        bot = TradingBot(None)
        gui = TradingGUI(bot)
        bot.gui = gui  # Conectar GUI al bot
    except Exception as e:
        print(f"Error al iniciar la aplicación: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()