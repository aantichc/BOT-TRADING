# Archivo: trading_bot.py - VERSIÓN CON CIERRE COMPLETO
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
        self.force_stop = False  # ✅ NUEVO: Bandera de parada forzosa
    
    def start(self):
        if not self.running:
            self.running = True
            self.force_stop = False  # ✅ Resetear bandera
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
            logging.info("Bot started")
            if self.gui: 
                self.gui.log_trade("Bot started", 'GREEN')
    
    def stop(self):
        """Parada normal"""
        self.running = False
        logging.info("Bot stopped")
        if self.gui: 
            self.gui.log_trade("Bot stopped", 'RED')
    
    def stop_completely(self):
        """✅ NUEVO: Parada completa para cerrar la aplicación"""
        print("Deteniendo bot completamente...")
        self.force_stop = True  # ✅ Activar bandera de parada forzosa
        self.running = False
        
        # Esperar a que el hilo termine (máximo 3 segundos)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
            if self.thread.is_alive():
                print("Hilo del bot aún activo, forzando cierre...")
        
        # Cerrar conexión de Binance
        try:
            self.client.close_connection()
            print("Conexión de Binance cerrada")
        except:
            pass
        
        logging.info("Bot completamente detenido")
    
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
        while self.running and not self.force_stop:  # ✅ Verificar ambas banderas
            try:
                # Rebalance automático
                self.manager.rebalance()
                
                # Espera exactamente 10 segundos como configuraste
                for i in range(10):  # ✅ Dividir la espera para poder interrumpir
                    if not self.running or self.force_stop:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error in bot loop: {e}")
                if not self.force_stop:  # ✅ Solo esperar si no estamos forzando cierre
                    time.sleep(UPDATE_INTERVAL)
        
        print("Hilo del bot terminado")  # ✅ Confirmación de cierre