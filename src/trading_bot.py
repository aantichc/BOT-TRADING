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
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
            print("🤖 Bot iniciado")  # ← DEBUG
            if self.gui: 
                self.gui.log_trade("🤖 Bot iniciado", 'GREEN')
            else:
                print("❌ GUI no conectada al bot")  # ← DEBUG
    
    def stop(self):
        """Parada normal"""
        self.running = False
        logging.info("Bot stopped")
        if self.gui: 
            self.gui.log_trade("Bot stopped", 'RED')
   
    def stop_completely(self):
        """Parada completa para reinicio de aplicación"""
        print("🛑 Deteniendo bot completamente para reinicio...")
        self.force_stop = True
        self.running = False
        
        # Detener inmediatamente cualquier operación en curso
        try:
            # Cerrar conexiones de Binance
            self.client.close_connection()
            print("✅ Conexión de Binance cerrada")
        except Exception as e:
            print(f"⚠️ Error cerrando conexión: {e}")
        
        # Esperar a que el hilo termine (pero no demasiado)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)  # Timeout más corto para reinicio rápido
            if self.thread.is_alive():
                print("⚠️ Hilo del bot aún activo, forzando cierre...")
            else:
                print("✅ Hilo del bot terminado")
        
        print("✅ Bot listo para reinicio")
    
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