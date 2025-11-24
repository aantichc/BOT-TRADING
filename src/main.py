from gui import TradingGUI
from trading_bot import TradingBot

def main():
    bot = TradingBot(None)
    gui = TradingGUI(bot)
    bot.gui = gui  # Conectar GUI al bot

if __name__ == "__main__":
    main()