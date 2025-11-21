import tkinter as tk
from gui import TradingBotGUI
from trading_bot import TradingBot

def main():
    root = tk.Tk()
    
    # Crear primero el bot sin GUI
    bot = TradingBot(None)
    
    # Crear la GUI con referencia al bot
    gui = TradingBotGUI(root, bot)
    
    # Ahora conectar la GUI al bot
    bot.gui = gui
    
    root.mainloop()

if __name__ == "__main__":
    main()