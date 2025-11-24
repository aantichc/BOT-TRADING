# main.py - VERSIÓN CORREGIDA
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Iniciando aplicación...")
    
    try:
        # ✅ IMPORTAR DENTRO de la función para evitar circular imports
        from trading_bot import TradingBot
        from gui import ModernTradingGUI
        
        print("1. Creando bot...")
        bot = TradingBot(None)
        print(f"✅ Bot creado - GUI temporal: {bot.gui is not None}")
        
        print("2. Creando GUI con bot...")
        gui = ModernTradingGUI(bot)  # ← Pasar el bot directamente
        print(f"✅ GUI creada - Bot: {gui.bot is not None}")
        
        print("3. Conectando bot con GUI...")
        bot.gui = gui  # Ahora el bot tiene la GUI real
        print(f"✅ Conexión completa - Bot GUI: {bot.gui is not None}")
        
        # ✅ INICIAR BOT AUTOMÁTICAMENTE
        if bot.gui and gui.bot:
            print("4. Iniciando bot automáticamente...")
            bot.start()
            print("✅ Aplicación iniciada correctamente")
        else:
            print("❌ Error de conexión")
            
    except Exception as e:
        print(f"❌ Error al iniciar aplicación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()