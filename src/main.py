# main.py - VERSIÓN COMPLETAMENTE CORREGIDA
import logging
import time
import sys
import tkinter as tk

logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Iniciando aplicación...")
    
    try:
        from trading_bot import TradingBot
        from gui import ModernTradingGUI
        
        print("1. Creando GUI...")
        gui = ModernTradingGUI(None)
        print(f"✅ GUI creada")
        
        print("2. Creando bot...")
        bot = TradingBot(gui)
        print(f"✅ Bot creado con GUI: {bot.gui is not None}")
        
        print("3. Asignando bot a GUI...")
        gui.bot = bot
        print(f"✅ Bot asignado a GUI: {gui.bot is not None}")
        
        print("4. Conectando GUI a componentes del bot...")
        bot.connect_gui(gui)
        print("✅ GUI completamente conectada")
        
        print("5. Configurando controles...")
        gui.enable_bot_controls()
        
        print("6. Iniciando bot...")
        bot.start()
        print("✅ Bot iniciado")
        
        # ✅ LOG INICIAL
        gui.log_trade("🚀 System Initialized", 'GREEN')
        
        print("🎯 Aplicación ejecutándose correctamente...")
        
        # ✅ LOOP PRINCIPAL ROBUSTO CON MANEJO DE EXCEPCIONES
        last_update_time = time.time()
        update_interval = 1  # 1second
        
        while True:
            try:
                current_time = time.time()
                
                # ✅ ACTUALIZAR GUI CADA 1S
                if current_time - last_update_time >= update_interval:
                    gui.root.update()
                    gui.process_data_queue()
                    last_update_time = current_time
                else:
                    # ✅ PEQUEÑA PAUSA PARA NO SATURAR CPU
                    time.sleep(0.1)
                    
            except tk.TclError as e:
                if "application has been destroyed" in str(e) or "main thread is not in main loop" in str(e):
                    print("🔴 GUI cerrada, terminando aplicación...")
                    break
                else:
                    print(f"⚠️ TclError: {e}")
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"⚠️ Error en loop principal: {e}")
                time.sleep(0.1)
                
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔴 Cerrando aplicación...")
        if 'bot' in locals():
            bot.stop_completely()
        sys.exit(0)

if __name__ == "__main__":
    main()