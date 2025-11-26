# main.py - VERSIÓN CORREGIDA CON ORDEN ADECUADO
import logging
import time

logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Iniciando aplicación...")
    
    try:
        from trading_bot import TradingBot
        from gui import ModernTradingGUI
        
        print("1. Creando GUI...")
        gui = ModernTradingGUI(None)  # ✅ PRIMERO crear GUI sin bot
        print(f"✅ GUI creada")
        
        print("2. Creando bot...")
        bot = TradingBot(gui)  # ✅ LUEGO crear bot CON GUI
        print(f"✅ Bot creado con GUI: {bot.gui is not None}")
        
        print("3. Asignando bot a GUI...")
        gui.bot = bot  # ✅ ASIGNAR referencia bidireccional
        print(f"✅ Bot asignado a GUI: {gui.bot is not None}")
        
        print("4. Conectando GUI a componentes del bot...")
        bot.connect_gui(gui)  # ✅ CONECTAR GUI a account y manager
        print("✅ GUI completamente conectada")
        
        print("5. Verificando conexiones iniciales...")
        gui.verify_initial_connection()  # ✅ VERIFICAR que todo está conectado
        
        print("6. Configurando controles...")
        gui.enable_bot_controls()  # ✅ HABILITAR botones
        
        # ✅ ESPERAR A QUE LA GUI ESTÉ COMPLETAMENTE LISTA
        print("7. Esperando inicialización completa de GUI...")
        time.sleep(2)  # ✅ PEQUEÑA PAUSA PARA ESTABILIZAR
        
        print("8. Iniciando bot...")
        bot.start()  # ✅ SOLO AHORA iniciar el bot
        print("✅ Bot iniciado")
        
        # ✅ LOG INICIAL
        gui.log_trade("🚀 Sistema completamente inicializado y funcionando", 'GREEN')
        
        print("🎯 Aplicación ejecutándose correctamente...")
        
        # ✅ LOOP PRINCIPAL MEJORADO
        try:
            while True:
                try:
                    gui.root.update()
                    gui.process_data_queue()
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