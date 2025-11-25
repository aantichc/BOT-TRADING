# main.py - VERSIÓN CORREGIDA
import logging
import time

logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Iniciando aplicación...")
    
    try:
        from trading_bot import TradingBot
        from gui import ModernTradingGUI
        
        print("1. Creando bot...")
        bot = TradingBot(None)
        print(f"✅ Bot creado")
        
        print("2. Creando GUI...")
        gui = ModernTradingGUI(bot)
        print(f"✅ GUI creada")
        
        print("3. Conectando GUI...")
        bot.connect_gui(gui)
        print(f"✅ GUI conectada")
        
        print("4. Iniciando bot...")
        bot.start()
        print("✅ Bot iniciado")
        
        print("5. Configurando controles...")
        gui.enable_bot_controls()
        
        # ✅ LOG INICIAL
        gui.log_trade("🚀 System Working", 'GREEN')
        
        print("🎯 Aplicación ejecutándose...")
        
        # ✅ LOOP PRINCIPAL
        try:
            while True:
                try:
                    gui.root.update()
                    gui.process_data_queue()  # Procesar cola en hilo principal
                    time.sleep(0.05)
                except Exception as e:
                    if "main thread is not in main loop" not in str(e):
                        print(f"⚠️ Error en update: {e}")
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Cerrando aplicación...")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'bot' in locals():
            bot.stop_completely()

if __name__ == "__main__":
    main()