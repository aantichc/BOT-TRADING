from gui import ModernTradingGUI
from trading_bot import TradingBot
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Iniciando aplicación...")
    
    # Crear bot primero pero sin GUI
    bot = TradingBot(None)
    print(f"✅ Bot creado - GUI: {bot.gui}")
    
    # Crear GUI y conectar
    gui = ModernTradingGUI(bot)
    print(f"✅ GUI creada - Bot: {gui.bot}")
    
    # Conexión bidireccional
    bot.gui = gui
    print(f"✅ Conexión completa - Bot GUI: {bot.gui is not None}")
    
    # Test inmediato
    if bot.gui:
        bot.gui.log_trade("🔧 Test de conexión GUI-Bot", 'GREEN')
    else:
        print("❌ ERROR: GUI no conectada al bot")

if __name__ == "__main__":
    main()