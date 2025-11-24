# main.py
from gui import ModernTradingGUI  # Cambiar por el nuevo nombre
from trading_bot import TradingBot

def main():
    bot = TradingBot(None)
    gui = ModernTradingGUI(bot)  # Usar la nueva interfaz
    bot.gui = gui

if __name__ == "__main__":
    main()