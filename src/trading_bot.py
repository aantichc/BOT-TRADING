# Archivo: trading_bot.py - VERSIÓN SIN INICIO AUTOMÁTICO
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
        print(f"🤖 Creando bot - GUI recibida: {gui is not None}")
        self.gui = gui
        print(f"🤖 Bot GUI asignada: {self.gui is not None}")

        self.client = Client(API_KEY, API_SECRET)
        self.indicators = Indicators(self.client)
        self.account = BinanceAccount(None)  # ✅ Inicialmente sin GUI
        self.manager = CapitalManager(self.account, self.indicators, None)  # ✅ Inicialmente sin GUI
        self.running = False
        self.thread = None
        self.force_stop = False
    
    def connect_gui(self, gui):
        """✅ CONECTA GUI a todos los componentes"""
        print(f"🔗 Conectando GUI a todos los componentes...")
        self.gui = gui
        self.account.gui = gui  # Actualizar cuenta
        self.manager.gui = gui  # Actualizar manager
        print(f"✅ GUI conectada - Account: {self.account.gui is not None}, Manager: {self.manager.gui is not None}")
    
    def start(self):
        """✅ INICIAR BOT MANUALMENTE"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
            print("🤖 Bot iniciado")
            if self.gui: 
                self.gui.log_trade("🤖 Bot iniciado", 'GREEN')
            else:
                print("⚠️ Bot iniciado sin GUI conectada")
    
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
        
        try:
            self.client.close_connection()
            print("✅ Conexión de Binance cerrada")
        except Exception as e:
            print(f"⚠️ Error cerrando conexión: {e}")
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
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
        while self.running and not self.force_stop:
            try:
                # ✅ ESPERAR HASTA QUE LA GUI ESTÉ CONECTADA
                if (hasattr(self, 'manager') and hasattr(self.manager, 'gui') 
                    and self.manager.gui is not None and hasattr(self, 'gui') 
                    and self.gui is not None):
                    
                    self.manager.rebalance()
                else:
                    print("⏳ Esperando conexión GUI completa...")
                    time.sleep(5)  # Esperar 5 segundos antes de reintentar
                    continue
                    
                # Espera normal de 10 segundos
                for i in range(10):
                    if not self.running or self.force_stop:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logging.error(f"Error in bot loop: {e}")
                if not self.force_stop:
                    time.sleep(10)  # Esperar más en caso de error