# debug.py
from trading_bot import TradingBot
from gui import ModernTradingGUI
import time

def test_trading():
    bot = TradingBot(None)
    gui = ModernTradingGUI(bot)
    bot.gui = gui
    
    # Test manual
    print("🧪 Iniciando test de trading...")
    bot.start()
    time.sleep(30)  # Esperar 30 segundos
    bot.stop()

if __name__ == "__main__":
    test_trading()