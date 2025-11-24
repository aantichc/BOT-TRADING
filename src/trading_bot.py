
# Archivo: trading_bot.py
from binance.client import Client
from config import API_KEY, API_SECRET, UPDATE_INTERVAL
from indicators import Indicators
from binance_account import BinanceAccount
from capital_manager import CapitalManager
import time
import threading

class TradingBot:
    def __init__(self, gui):
        self.gui = gui
        self.client = Client(API_KEY, API_SECRET)
        self.indicators = Indicators(self.client)
        self.account = BinanceAccount(self.gui)
        self.manager = CapitalManager(self.account, self.indicators, self.gui)
        self.running = False
    
    def start(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.loop, daemon=True).start()   # ← daemon=True
            if self.gui: self.gui.log_trade("Bot started", 'GREEN')
    
    def stop(self):
        self.running = False
        if self.gui: self.gui.log_trade("Bot stopped", 'RED')
    
    def rebalance_manual(self):
        result = self.manager.rebalance(manual=True)
        if self.gui: self.gui.log_trade(f"Manual rebalance: {result}", 'GREEN')
    
    def loop(self):
        while self.running:
            # PRIMERO: rebalancea (para trades automáticos)
            self.manager.rebalance()
            
            # SEGUNDO: fuerza actualización de GUI (para que se vean las señales aunque no haya trade)
            if self.gui:
                self.gui.update_ui()  # ← ESTA LÍNEA ES LA CLAVE
            
            time.sleep(UPDATE_INTERVAL)  
