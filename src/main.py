import tkinter as tk
from .trading_bot import TradingBotGUI

def main():
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()