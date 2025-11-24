# Archivo: trading_bot.py - VERSIÓN MEJORADA MANTENIENDO 10s
from binance.client import Client
from config import API_KEY, API_SECRET, UPDATE_INTERVAL
from indicators import Indicators
from binance_account import BinanceAccount
from capital_manager import CapitalManager
import time
import threading
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TradingBot:
    def __init__(self, gui):
        self.gui = gui
        self.client = Client(API_KEY, API_SECRET)
        self.indicators = Indicators(self.client)
        self.account = BinanceAccount(self.gui)
        self.manager = CapitalManager(self.account, self.indicators, self.gui)
        self.running = False
        self.thread = None
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
            logging.info("Bot started")
            if self.gui: 
                self.gui.log_trade("Bot started", 'GREEN')
    
    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        logging.info("Bot stopped")
        if self.gui: 
            self.gui.log_trade("Bot stopped", 'RED')
    
    def rebalance_manual(self):
        try:
            result = self.manager.rebalance(manual=True)
            logging.info(f"Manual rebalance: {result}")
            if self.gui: 
                self.gui.log_trade(f"Manual rebalance: {result}", 'GREEN')
        except Exception as e:
            logging.error(f"Error in manual rebalance: {e}")
            if self.gui: 
                self.gui.log_trade(f"Error in rebalance: {e}", 'RED')
    
    def loop(self):
        while self.running:
            try:
                # Rebalance automático
                self.manager.rebalance()
                
                # Espera exactamente 10 segundos como configuraste
                time.sleep(UPDATE_INTERVAL)
                
            except Exception as e:
                logging.error(f"Error in bot loop: {e}")
                time.sleep(UPDATE_INTERVAL)  # Mantener intervalo incluso en error