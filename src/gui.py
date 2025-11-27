# src/gui.py - INTERFAZ OSCURA MODERNA CON CARTERA
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
from matplotlib.figure import Figure
import json
import os
import threading
import queue
import numpy as np
from scipy.interpolate import make_interp_spline
import subprocess  
from config import DEFAULT_CHART_TIMEFRAME
import time
from concurrent.futures import ThreadPoolExecutor
import random 

# Configuración de colores
DARK_BG = "#0f0f0f"
CARD_BG = "#1a1a1a"
ACCENT_COLOR = "#00ff88"
SECONDARY_COLOR = "#0088ff"
WARNING_COLOR = "#ffaa00"
DANGER_COLOR = "#ff4444"
TEXT_COLOR = "#ffffff"
TEXT_SECONDARY = "#bbbbbb"

class ModernTradingGUI:
    def __init__(self, bot=None):
        print("🎨 Inicializando GUI...")
        
        self.bot = bot
        print(f"✅ Bot asignado a GUI: {self.bot is not None}")
        
        self.update_job = None
        self.data_queue = queue.Queue()
        self.updating = False
        self.closing = False
        self._performance_cache = {}
        self._cache_time = {}        

        # ✅ INICIALIZAR CACHE DE COMISIONES
        self._cached_fees_period = self.get_empty_fees()
        self._last_fees_calc = datetime.now() - timedelta(hours=2)  # Forzar primera actualización
        
        # 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 🆕 
        # ✅ NUEVAS VARIABLES PARA OPTIMIZACIÓN
        self.update_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="GUI_Update")
                # ✅ INICIALIZAR CON TIMESTAMP ACTUAL (no cero)
        self.last_update_time = {
            'metrics': time.time(),
            'portfolio': time.time(), 
            'tokens': time.time(),
            'chart': time.time(),
            'fees': time.time(),
            'daily_change': time.time()
        } 
        self.update_intervals = {
            'metrics': 180,       # 3 minutos
            'portfolio': 180,     # 3 minutos  
            'tokens': 60,         # 1 minutos
            'chart': 180,         # 3 minutos
            'fees': 7200,         # 2 horas
            'daily_change': 180   # 3 minutos
        }
        self.is_updating = {key: False for key in self.update_intervals}
        self._cached_daily_changes = {}
        self._cached_fees = self.get_empty_fees()
        
        # ✅ VARIABLES PARA INDICADORES DE SECCIÓN
        self.last_update_times = {
            'tokens': "Nunca",
            'metrics': "Nunca", 
            'portfolio': "Nunca",
            'chart': "Nunca",
            'fees': "Nunca"
        }
        self.section_indicators = {}  # Para guardar referencias a los indicadores
        
        # ✅ CONTADORES PARA FEEDBACK
        self.update_count = 0
        self.tooltip = None

        # Configuración de matplotlib...
        plt.rcParams['figure.facecolor'] = DARK_BG
        plt.rcParams['axes.facecolor'] = CARD_BG
        plt.rcParams['axes.edgecolor'] = TEXT_SECONDARY
        plt.rcParams['axes.labelcolor'] = TEXT_COLOR
        plt.rcParams['xtick.color'] = TEXT_SECONDARY
        plt.rcParams['ytick.color'] = TEXT_SECONDARY
        plt.rcParams['text.color'] = TEXT_COLOR
        plt.rcParams['font.size'] = 10
        
        # Configurar la ventana
        self.setup_window()
        self.setup_styles()
        self.create_widgets()
        self.root.after(30000, self._simple_health_check) 
        self.root.after(2000, self.start_all_continuous_pulses)
        self.history = self.load_history()
        self.process_data_queue()
        
        # ✅ INICIALMENTE DESHABILITAR BOTONES
        self.start_btn.config(state='disabled', bg='gray')
        self.stop_btn.config(state='disabled', bg='gray') 
        self.rebalance_btn.config(state='disabled', bg='gray')
        
        # ✅ NO USAR mainloop() AQUÍ - se controlará desde main.py con update()
        print("✅ GUI inicializada (esperando configuración desde main.py)")
        
        # INICIALIZAR LIMPIEZA PERIÓDICA
        self.root.after(60000, self.setup_memory_cleanup)  # Empezar después de 1 minuto

                        # ✅ VERIFICAR COLORES INICIALES DE INDICADORES
        print("🎨 Verificando colores iniciales de indicadores:")
        for section in ['tokens', 'metrics', 'portfolio', 'chart']:
            indicator = self.section_indicators.get(section)
            if indicator:
                try:
                    color = indicator.cget('foreground')
                    print(f"   {section}: {color}")
                except Exception as e:
                    print(f"   {section}: Error obteniendo color - {e}")

            
                # ✅ SISTEMA DE COLA PARA INDICADORES DESDE HILOS SECUNDARIOS
        self.indicator_actions = queue.Queue()
        self.setup_indicator_queue_processor()
        
        print("🔧 Sistema de cola de indicadores inicializado")
        
                # ✅ CONTROL DE ANIMACIONES ACTIVAS
        self.active_pulses = {}  # {section_name: animation_id}
        
        print("🎬 Sistema de pulsos continuos inicializado")

    def setup_indicator_queue_processor(self):
        """✅ PROCESADOR DE ACCIONES DE INDICADORES DESDE CUALQUIER HILO"""
        def process_indicator_actions():
            try:
                # Procesar todas las acciones pendientes
                while not self.indicator_actions.empty():
                    try:
                        action = self.indicator_actions.get_nowait()
                        action()  # Ejecutar la acción
                    except queue.Empty:
                        break
            except Exception as e:
                print(f"❌ Error procesando cola de indicadores: {e}")
            finally:
                # Programar siguiente verificación (solo si no estamos cerrando)
                if not self.closing and hasattr(self, 'root') and self.root:
                    self.root.after(100, process_indicator_actions)
        
        # Iniciar el procesamiento
        if hasattr(self, 'root') and self.root:
            self.root.after(100, process_indicator_actions)

    def update_section_indicator(self, section_name):
        """✅ ACTIVAR INDICADOR - VERSIÓN SUPER SIMPLE"""
        # Solo usar cola para evitar errores de threading
        if hasattr(self, 'indicator_actions') and not self.closing:
            self.indicator_actions.put(lambda: self._do_activate_indicator(section_name))

    def _test_all_indicators(self):
        """✅ PRUEBA VISUAL DE TODOS LOS INDICADORES"""
        if self.closing:
            return
            
        print("🧪 EJECUTANDO PRUEBA VISUAL DE INDICADORES...")
        
        # Activar todos los indicadores uno por uno
        sections = ['tokens', 'metrics', 'portfolio', 'chart']
        
        def activate_section(index):
            if index >= len(sections) or self.closing:
                return
                
            section = sections[index]
            print(f"🧪 Activando indicador: {section}")
            self._do_activate_indicator(section)
            
            # Siguiente indicador en 2 segundos
            if hasattr(self, 'root') and self.root:
                self.root.after(2000, lambda: activate_section(index + 1))
        
        # Iniciar la secuencia
        activate_section(0)

    def setup_indicator_system(self):
        """✅ CONFIGURAR PROCESAMIENTO SEGURO DE INDICADORES"""
        def process_indicator_queue():
            try:
                # Procesar todos los comandos pendientes
                while not self.indicator_queue.empty():
                    try:
                        command = self.indicator_queue.get_nowait()
                        command()
                    except queue.Empty:
                        break
            except Exception as e:
                print(f"❌ Error procesando cola de indicadores: {e}")
            finally:
                # Programar siguiente verificación
                if not self.closing and hasattr(self, 'root') and self.root:
                    self.root.after(100, process_indicator_queue)
        
        # Iniciar el procesamiento
        if hasattr(self, 'root') and self.root:
            self.root.after(100, process_indicator_queue)        
        
    def _simple_health_check(self):
        """✅ VERIFICACIÓN SIMPLE DE SALUD"""
        if self.closing:
            return
            
        try:
            print(f"📊 Estado: Cola={self.data_queue.qsize()}, Activos={sum(self.is_updating.values())}")
        except:
            pass
        finally:
            if not self.closing:
                self.root.after(30000, self._simple_health_check)

    def start_pulse_effect(self, section_name, duration=4):
        """✅ EFECTO DE PULSO - verde brillante que se desvanece suavemente a gris en X segundos"""
        if self.closing:
            return
            
        indicator = self.section_indicators.get(section_name)
        if not indicator or not indicator.winfo_exists():
            return
        
        start_time = time.time()
        total_steps = int(duration * 10)  # 10 FPS = suave pero ligero
        
        def pulse_frame(step=0):
            if self.closing or not indicator or not indicator.winfo_exists():
                return
                
            # Calcular progreso (0.0 a 1.0)
            progress = step / total_steps if total_steps > 0 else 1.0
            
            if progress >= 1.0:
                # Fin de la animación - volver a gris permanente
                try:
                    indicator.config(fg=TEXT_SECONDARY)
                    print(f"   ⚪ Efecto pulso {section_name} completado")
                except:
                    pass
                return
            
            # ✅ ALGORITMO DE FADE: Verde brillante → Gris suavemente
            # En progreso 0.0: VERDE PURO (#00ff00)
            # En progreso 1.0: GRIS (#bbbbbb)
            
            # Componentes RGB del color inicial (verde) y final (gris)
            start_r, start_g, start_b = 0, 255, 0      # #00ff00
            end_r, end_g, end_b = 187, 187, 187        # #bbbbbb
            
            # Interpolar entre verde y gris
            current_r = int(start_r + (end_r - start_r) * progress)
            current_g = int(start_g + (end_g - start_g) * progress) 
            current_b = int(start_b + (end_b - start_b) * progress)
            
            # Asegurar valores dentro de rango
            current_r = max(0, min(255, current_r))
            current_g = max(0, min(255, current_g))
            current_b = max(0, min(255, current_b))
            
            color = f"#{current_r:02x}{current_g:02x}{current_b:02x}"
            
            try:
                indicator.config(fg=color)
            except:
                pass  # Ignorar errores si el indicador fue destruido
            
            # Siguiente frame en 100ms (10 FPS)
            if hasattr(self, 'root') and self.root and not self.closing:
                self.root.after(100, lambda: pulse_frame(step + 1))
        
        # ✅ INICIAR EN VERDE BRILLANTE
        try:
            indicator.config(fg="#00ff00")
            print(f"   🟢 Efecto pulso iniciado para {section_name}")
        except:
            return
            
        # Iniciar animación después de breve pausa para que se vea el verde
        if hasattr(self, 'root') and self.root:
            self.root.after(50, lambda: pulse_frame(1))  # Empezar en paso 1 (ya mostramos el verde en paso 0)

       
    def _test_indicators_manual(self):
        """✅ PRUEBA MANUAL DIRECTA DE INDICADORES"""
        print("🧪 INICIANDO PRUEBA MANUAL DE INDICADORES")
        
        # Probar cada indicador manualmente
        sections = ['tokens', 'metrics', 'portfolio', 'chart']
        
        def test_section(index):
            if index < len(sections):
                section = sections[index]
                print(f"🧪 PROBANDO MANUALMENTE: {section}")
                self.update_section_indicator(section)
                # Siguiente sección en 3 segundos
                self.root.after(3000, lambda: test_section(index + 1))
        
        # Iniciar prueba
        test_section(0)

    def setup_log_tags(self):
        """Configura los tags de color para el log"""
        self.log_text.tag_config('green_log', foreground="#00ff88")   # Compras/éxito
        self.log_text.tag_config('red_log', foreground="#ff4444")     # Ventas/errores
        self.log_text.tag_config('blue_log', foreground="#0088ff")    # Cambios de señal ← NUEVO
        self.log_text.tag_config('yellow_log', foreground="#ffaa00")  # Advertencias
        self.log_text.tag_config('white_log', foreground="#ffffff")   # Normal

    def _add_log_message(self, msg, color="white"):
            ts = datetime.now().strftime("%H:%M:%S")
            
            color_tags = {
                'GREEN': 'green_log',
                'RED': 'red_log', 
                'BLUE': 'blue_log',
                'YELLOW': 'yellow_log'
            }
            
            tag = color_tags.get(color, 'white_log')
            
            self.log_text.insert(tk.END, f"[{ts}] {msg}\n", tag)
            self.log_text.see(tk.END)
            
            # ¡LIMPIAR MÁS AGRESIVAMENTE!
            current_lines = int(self.log_text.index('end-1c').split('.')[0])
            if current_lines > 300:  # Reducir de 500 a 300
                self.log_text.delete(1.0, "100.0")  # Borrar 100 líneas cada vez
            
            # Limitar tamaño máximo absoluto
            if current_lines > 1000:
                self.log_text.delete(1.0, "500.0")  # Borrar 500 líneas drásticamente

    def cleanup_memory(self):
        """Limpieza más agresiva"""
        if self.closing:
            return
            
        # Forzar garbage collection
        import gc
        collected = gc.collect()
        
        # Limpiar cache de rendimiento viejo
        current_time = time.time()
        old_keys = [k for k, t in self._cache_time.items() 
                    if current_time - t > 300]  # 5 minutos
        for key in old_keys:
            self._performance_cache.pop(key, None)
            self._cache_time.pop(key, None)
        
        # Limpiar cola si es necesario
        if self.data_queue.qsize() > 30:
            self._clean_queue_aggressive()
        
        # Programar siguiente limpieza
        if not self.closing:
            self.root.after(120000, self.cleanup_memory)

    def _update_token_ui(self, symbol_data):
        """✅ ACTUALIZAR UI DE TOKENS - LOGS REDUCIDOS"""
        if self.closing or not hasattr(self, 'token_frames'):
            return
            
        # ✅ LOG INICIAL MÁS LIMPIO
        print(f"🎯 Actualizando UI de {len(symbol_data)} tokens...")
        
        for symbol, data in symbol_data.items():
            if symbol in self.token_frames and not self.closing:
                frame_data = self.token_frames[symbol].data
                try:
                    # ✅ SOLO LOG ESENCIAL - SEÑALES OO
                    signals = data.get('signals', {})
                    print(f"   📊 {symbol}: {signals}")
                    
                    # Actualizar precio (sin log)
                    frame_data["price_label"].config(text=f"${data['price']:,.4f}")
                    
                    # Actualizar %24H (sin log)
                    daily_change_str = data.get('daily_change', '+0.00%')
                    if isinstance(daily_change_str, str):
                        change_value_str = daily_change_str.strip('+%')
                        try:
                            daily_change_value = float(change_value_str)
                        except ValueError:
                            daily_change_value = 0.0
                    else:
                        daily_change_value = 0.0
                        daily_change_str = "+0.00%"
                    
                    # Color del %24H
                    if daily_change_value > 0:
                        change_color = ACCENT_COLOR
                    elif daily_change_value < 0:
                        change_color = DANGER_COLOR
                    else:
                        change_color = TEXT_SECONDARY
                    
                    frame_data["daily_change_header_label"].config(
                        text=f" {daily_change_str}",
                        fg=change_color
                    )
                    
                    # Actualizar balance (sin log)
                    frame_data["balance_label"].config(
                        text=f"{data['balance']:.6f} → ${data['usd']:,.2f} ({data['pct']:.1f}%)"
                    )
                    
                    # ✅ ACTUALIZAR CÍRCULOS DE SEÑALES OO (CON LOG REDUCIDO)
                    for tf, circle_data in frame_data["circles"].items():
                        # Color del círculo basado en señal OO
                        color = "gray"  # Por defecto
                        if tf in signals:
                            signal = signals[tf]
                            if signal == "GREEN":
                                color = "#00ff00"
                            elif signal == "YELLOW":
                                color = "#ffff00" 
                            elif signal == "RED":
                                color = "#ff4444"
                        
                        circle_data['canvas'].itemconfig(circle_data['circle_id'], fill=color)
                        
                        # Valor: % cambio de precio (sin log)
                        percent_change = self.get_price_change_percentage(symbol, tf)
                        
                        # Color del valor basado en % cambio
                        if percent_change > 0.5:
                            value_color = "#00ff00"
                        elif percent_change > 0.1:
                            value_color = "#00ff00"
                        elif percent_change > -0.1:
                            value_color = "#ffff00"
                        elif percent_change > -0.5:
                            value_color = "#ff4444"
                        else:
                            value_color = "#ff4444"
                        
                        sign = "+" if percent_change > 0 else ""
                        value_text = f"{sign}{percent_change:.1f}%"
                        
                        circle_data['value_label'].config(
                            text=value_text,
                            fg=value_color
                        )
                    
                    # Actualizar peso y señal general (sin log)
                    weight = data.get('weight', 0)
                    if weight >= 0.8:
                        weight_color = "#00ff00"
                        signal_text = "STRONG BUY"
                    elif weight >= 0.5:
                        weight_color = "#ffff00"
                        signal_text = "BUY"
                    elif weight >= 0.3:
                        weight_color = WARNING_COLOR
                        signal_text = "SELL"
                    else:
                        weight_color = DANGER_COLOR
                        signal_text = "STRONG SELL"
                    
                    frame_data["weight_label"].config(
                        text=f"WEIGHT: {weight:.2f}", 
                        fg=weight_color
                    )
                    frame_data["signal_label"].config(
                        text=f"SIGNAL: {signal_text}",
                        fg=weight_color,
                        font=("Arial", 9, "bold")
                    )
                    
                    # ✅ LOG FINAL MÁS LIMPIO
                    print(f"   ✅ {symbol} UI actualizado")
                    
                except Exception as e:
                    print(f"❌ Error actualizando {symbol} UI: {e}")
        
        # ✅ LOG FINAL RESUMIDO
        print(f"✅ UI actualizada: {len(symbol_data)} tokens")

    def get_price_change_percentage(self, symbol, timeframe):
        """Calcula el % de cambio de precio para un timeframe específico"""
        try:
            # Mapear timeframe a parámetros de Binance
            tf_map = {
                "30m": "30m",
                "1h": "1h", 
                "2h": "2h"
            }
            
            if timeframe not in tf_map:
                return 0.0
                
            # Obtener klines para el timeframe
            klines = self.bot.client.get_klines(
                symbol=symbol, 
                interval=tf_map[timeframe],
                limit=2  # Solo necesitamos 2 velas: actual y anterior
            )
            
            if len(klines) < 2:
                return 0.0
                
            # Precio de cierre actual y anterior
            current_close = float(klines[-1][4])  # Última vela, precio de cierre
            previous_close = float(klines[-2][4]) # Vela anterior, precio de cierre
            
            # Calcular % de cambio
            if previous_close == 0:
                return 0.0
                
            percent_change = ((current_close - previous_close) / previous_close) * 100
            return percent_change
            
        except Exception as e:
            print(f"Error calculando % cambio para {symbol} {timeframe}: {e}")
            return 0.0

    def verify_initial_connection(self):
        """✅ VERIFICAR CONEXIÓN COMPLETA Y FORZAR PRIMERA ACTUALIZACIÓN"""
        if self.bot:
            bot_has_gui = hasattr(self.bot, 'gui') and self.bot.gui is not None
            manager_has_gui = hasattr(self.bot, 'manager') and hasattr(self.bot.manager, 'gui') and self.bot.manager.gui is not None
            account_has_gui = hasattr(self.bot, 'account') and hasattr(self.bot.account, 'gui') and self.bot.account.gui is not None
            
            print(f"🔍 Verificación conexiones - Bot: {bot_has_gui}, Manager: {manager_has_gui}, Account: {account_has_gui}")
            
            if bot_has_gui and manager_has_gui and account_has_gui:
                print("✅ GUI completamente conectada a todos los componentes")
                self.log_trade("✅ GUI completamente conectada al bot", 'GREEN')
                
                # ✅ FORZAR PRIMERA ACTUALIZACIÓN INMEDIATA
                self.root.after(1000, self._force_initial_update)
            else:
                missing_components = []
                if not bot_has_gui: missing_components.append("Bot")
                if not manager_has_gui: missing_components.append("Manager")
                if not account_has_gui: missing_components.append("Account")
                
                print(f"⚠️ Conexiones incompletas: {', '.join(missing_components)}")
                self.log_trade(f"⚠️ Conexiones incompletas: {', '.join(missing_components)}", 'YELLOW')

    def _force_initial_update(self):
        """✅ FORZAR ACTUALIZACIÓN INICIAL PARA PROBAR CONEXIÓN"""
        print("🔨 Forzando actualización inicial...")
        try:
            # Probar con un símbolo específico
            if self.bot and hasattr(self.bot, 'account'):
                total_balance = self.bot.account.get_balance_usdc()
                print(f"💰 Balance inicial: ${total_balance:,.2f}")
                
                # Actualizar UI inmediatamente
                self.safe_update_ui()
                
                self.log_trade(f"💰 Balance inicial: ${total_balance:,.2f}", 'GREEN')
                
        except Exception as e:
            print(f"❌ Error en actualización inicial: {e}")
            self.log_trade(f"❌ Error en conexión: {e}", 'RED')

    def _update_metrics_ui(self, metrics):
        """Actualiza todas las métricas incluyendo comisiones por período"""
        if self.closing:
           return
        self.total_balance_label.config(text=f"${metrics['total_balance']:,.2f}")
        
        # Performance capital
        self.change_30m_label.config(text=metrics['change_30m'])
        self.change_1h_label.config(text=metrics['change_1h'])
        self.change_2h_label.config(text=metrics['change_2h'])
        self.change_4h_label.config(text=metrics['change_4h'])
        self.change_1d_label.config(text=metrics['change_1d'])
        self.change_1w_label.config(text=metrics['change_1w'])
        self.change_1m_label.config(text=metrics['change_1m'])
        self.change_1y_label.config(text=metrics['change_1y'])
        
        # Comisiones por período
        self.fees_1d_label.config(text=metrics['fees_1d'])
        self.fees_1w_label.config(text=metrics['fees_1w'])
        self.fees_1m_label.config(text=metrics['fees_1m'])
        self.fees_1y_label.config(text=metrics['fees_1y'])
        
        # Aplicar colores
        self.apply_change_colors(metrics)
    
    def enable_bot_controls(self):
        """✅ HABILITAR controles del bot después de conexión exitosa"""
        print("🎛️ Habilitando controles del bot en GUI...")
        self.start_btn.config(state='normal', bg=ACCENT_COLOR)
        self.stop_btn.config(state='normal', bg=DANGER_COLOR)
        self.rebalance_btn.config(state='normal', bg=WARNING_COLOR)
        
        # ✅ FORZAR PRIMERA ACTUALIZACIÓN COMPLETA INMEDIATA
        print("🔨 Forzando primera actualización completa...")
        self.root.after(1000, self._force_complete_initial_update)
    
    def _force_complete_initial_update(self):
        """✅ ACTUALIZACIÓN INICIAL COMPLETA Y FORZADA"""
        print("🚀 EJECUTANDO ACTUALIZACIÓN INICIAL COMPLETA...")
        
        try:
            # ✅ 1. VERIFICAR CONEXIÓN BÁSICA
            if not self.bot or not hasattr(self.bot, 'account'):
                print("❌ Bot no disponible para actualización inicial")
                return
            
            # ✅ 2. OBTENER DATOS BÁSICOS
            total_balance = self.bot.account.get_balance_usdc()
            print(f"💰 Balance inicial obtenido: ${total_balance:,.2f}")
            
            # ✅ 3. ACTUALIZAR HISTORIAL INMEDIATAMENTE
            now = datetime.now()
            self._update_history(now, total_balance)
            
            # ✅ 4. FORZAR ACTUALIZACIÓN DE GRÁFICO
            print("📊 Forzando actualización de gráfico...")
            self._update_main_chart(total_balance)
            
            # ✅ 5. FORZAR ACTUALIZACIÓN DE CARTERA
            print("💼 Forzando actualización de portfolio...")
            portfolio_data = self.get_portfolio_data(total_balance)
            self._update_portfolio_ui(portfolio_data)
            
            # ✅ 6. FORZAR ACTUALIZACIÓN DE MÉTRICAS
            print("📈 Forzando actualización de métricas...")
            metrics = {
                'total_balance': total_balance,
                'change_30m': "+0.00%",
                'change_1h': "+0.00%", 
                'change_2h': "+0.00%",
                'change_4h': "+0.00%",
                'change_1d': "+0.00%",
                'change_1w': "+0.00%", 
                'change_1m': "+0.00%",
                'change_1y': "+0.00%",
                'fees_1d': "$0.00",
                'fees_1w': "$0.00",
                'fees_1m': "$0.00", 
                'fees_1y': "$0.00"
            }
            self._update_metrics_ui(metrics)
            
            # ✅ 7. FORZAR ACTUALIZACIÓN DE TOKENS
            print("🎯 Forzando actualización de tokens...")
            self._schedule_background_task(self._update_tokens_background)
            
            # ✅ 8. INICIAR ACTUALIZACIONES AUTOMÁTICAS
            print("🔄 Iniciando ciclo de actualizaciones automáticas...")
            self.root.after(5000, self.safe_update_ui)  # Primera en 5 segundos
            
            self.log_trade(f"✅ Sistema inicializado - Balance: ${total_balance:,.2f}", 'GREEN')
            print("✅ Actualización inicial completada correctamente")
            
        except Exception as e:
            print(f"❌ Error en actualización inicial: {e}")
            import traceback
            traceback.print_exc()
            self.log_trade(f"❌ Error en inicialización: {e}", 'RED')    
    
    def check_tkinter_health(self):
        """✅ VERIFICAR SALUD DE TKINTER"""
        try:
            if not hasattr(self, 'root') or not self.root:
                return "NO_ROOT"
                
            if not hasattr(self.root, 'tk'):
                return "NO_TK"
                
            if not hasattr(self.root, '_windowingsystem'):
                return "NO_WINDOWING"
                
            # Probar una operación simple de Tkinter
            try:
                self.root.tk.call('info', 'exists', '.')
                return "HEALTHY"
            except:
                return "TK_CALL_FAILED"
                
        except Exception as e:
            return f"ERROR: {str(e)}"

    def safe_update_ui(self):
        """✅ ACTUALIZACIÓN CORRECTA - solo activar indicadores cuando realmente se actualice"""
        if self.closing:
            return
            
        # ✅ VERIFICACIÓN BÁSICA
        if not self.bot or not hasattr(self.bot, 'running') or not self.bot.running:
            if not self.closing:
                self.root.after(30000, self.safe_update_ui)
            return
        
        current_time = time.time()
        
        # ❌ ELIMINAR ESTA LÍNEA:
        # self.update_section_indicator('metrics')
        
        # ✅ SOLO ACTIVAR INDICADORES CUANDO REALMENTE SE ACTUALICE
        updates_scheduled = 0
        
        if self._should_update('tokens', current_time) and updates_scheduled < 2:
            print("🔄 Programando actualización de tokens...")
            self._schedule_background_task(self._update_tokens_background)
            updates_scheduled += 1
            
        if self._should_update('metrics', current_time) and updates_scheduled < 2:  
            print("🔄 Programando actualización de métricas...")
            self._schedule_background_task(self._update_metrics_background)
            # ✅ EL INDICADOR SE ACTIVA DENTRO de _update_metrics_background
            updates_scheduled += 1
            
        if self._should_update('portfolio', current_time) and updates_scheduled < 2:
            print("🔄 Programando actualización de portfolio...")
            self._schedule_background_task(self._update_portfolio_background)
            # ✅ EL INDICADOR SE ACTIVA DENTRO de _update_portfolio_background
            updates_scheduled += 1
            
        if self._should_update('chart', current_time) and updates_scheduled < 2:
            print("🔄 Programando actualización de gráfico...")
            self._schedule_background_task(self._update_chart_background)
            # ✅ EL INDICADOR SE ACTIVA DENTRO de _update_chart_background
            updates_scheduled += 1
        
        # ✅ PROGRAMAR SIGUIENTE
        next_interval = 30000 if updates_scheduled > 0 else 15000
        if not self.closing:
            self.root.after(next_interval, self.safe_update_ui)

    def safe_start_updates(self):
        """Iniciar actualizaciones de forma segura después de que el loop esté activo"""
        print("🔄 Iniciando actualizaciones automáticas...")
        # ✅ INICIAR LA PRIMERA ACTUALIZACIÓN
        self.safe_update_ui()

    def setup_window(self):
        """Configura la ventana principal - MAXIMIZADA PERO NO PANTALLA COMPLETA"""
        self.root = tk.Tk()
        self.root.title("🚀 CRYPTO TRADING BOT - DASHBOARD")
        self.root.configure(bg=DARK_BG)
        
        # ✅ VENTANA MAXIMIZADA (con barra de título y controles)
        self.root.state('zoomed')  # Esto maximiza la ventana en Windows
        
        # Opcional: También puedes usar geometry para asegurar
        # screen_width = self.root.winfo_screenwidth()
        # screen_height = self.root.winfo_screenheight()
        # self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        print("🖥️ Ventana configurada en modo maximizado")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        """Configura estilos personalizados"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # ✅ VERIFICAR QUE LOS COLORES ESTÉN BIEN DEFINIDOS
        print("🎨 Verificando configuración de colores:")
        print(f"   ACCENT_COLOR: {ACCENT_COLOR}")
        print(f"   TEXT_SECONDARY: {TEXT_SECONDARY}")
        
        # Configurar colores para ttk widgets
        style.configure('TFrame', background=DARK_BG)
        style.configure('TLabel', background=DARK_BG, foreground=TEXT_COLOR)
        style.configure('TButton', background=ACCENT_COLOR, foreground='black')
        
        # Estilo para Combobox en tema oscuro - CORREGIDO
        style.configure('Dark.TCombobox', 
                    fieldbackground=CARD_BG, 
                    background=CARD_BG, 
                    foreground=TEXT_COLOR,
                    insertcolor=TEXT_COLOR,  # Color del cursor
                    borderwidth=1,
                    relief='flat')
        
        # Configurar el mapa para los estados del Combobox
        style.map('Dark.TCombobox',
                fieldbackground=[('readonly', CARD_BG)],
                background=[('readonly', CARD_BG)],
                foreground=[('readonly', TEXT_COLOR)])
        
        # Estilo para Treeview en tema oscuro
        style.configure('Treeview',
                    background=CARD_BG,
                    foreground=TEXT_COLOR,
                    fieldbackground=CARD_BG,
                    borderwidth=0)
        style.map('Treeview', background=[('selected', SECONDARY_COLOR)])
        
        style.configure('Treeview.Heading',
                    background=DARK_BG,
                    foreground=TEXT_COLOR,
                    relief='flat')

    def create_compact_metric(self, parent, timeframe, value, color):
        """Crea métrica ultra-compacta para timeframes"""
        metric_frame = tk.Frame(parent, bg=CARD_BG, relief='flat', bd=1,
                            highlightbackground=TEXT_SECONDARY, highlightthickness=1,
                            width=80, height=45)
        metric_frame.pack(side=tk.LEFT, padx=(0, 5))
        metric_frame.pack_propagate(False)
        
        # Timeframe (pequeño)
        tk.Label(metric_frame, text=timeframe, bg=CARD_BG, fg=TEXT_SECONDARY,
                font=("Arial", 8, "bold")).pack(pady=(5, 0))
        
        # Valor (compacto)
        value_label = tk.Label(metric_frame, text=value, bg=CARD_BG, fg=color,
                            font=("Arial", 9, "bold"))
        value_label.pack(pady=(0, 5))
        
        return value_label

    def create_widgets(self):        
        """Crea todos los widgets de la interfaz"""
        # Header
        header = tk.Frame(self.root, bg=DARK_BG, height=80)
        header.pack(fill=tk.X, padx=20, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="🚀 CRYPTO TRADING BOT - by Alan Antich", 
                bg=DARK_BG, fg=ACCENT_COLOR, font=("Arial", 24, "bold")).pack(side=tk.LEFT)
        
        # Botones de control
        control_frame = tk.Frame(header, bg=DARK_BG)
        control_frame.pack(side=tk.RIGHT)
        
        self.start_btn = self.create_button(control_frame, "▶ START", ACCENT_COLOR, self.safe_start)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = self.create_button(control_frame, "⏹ STOP", DANGER_COLOR, self.safe_stop)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.rebalance_btn = self.create_button(control_frame, "⚖ REBALANCE", WARNING_COLOR, self.safe_rebalance)
        self.rebalance_btn.pack(side=tk.LEFT, padx=5)
        
        self.create_button(control_frame, "🔄 RESTART", SECONDARY_COLOR, self.safe_restart_app).pack(side=tk.LEFT, padx=5)
        
        # En create_widgets(), después de crear los botones:
        if self.bot is None:
            self.start_btn.config(state='disabled', bg='gray')
            self.stop_btn.config(state='disabled', bg='gray') 
            self.rebalance_btn.config(state='disabled', bg='gray')
        
        # Selector de timeframe SIMPLIFICADO
        tk.Label(control_frame, text="TIMEFRAME:", bg=DARK_BG, fg=TEXT_SECONDARY, 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(20,5))
        self.tf_var = tk.StringVar(value=DEFAULT_CHART_TIMEFRAME)
        tf_combo = ttk.Combobox(control_frame, textvariable=self.tf_var, 
                            values=["1h", "1D", "1W"],  # SOLO 3 TIMEFRAMES
                            width=8, state="readonly", font=("Arial", 10),
                            style='Dark.TCombobox')
        tf_combo.pack(side=tk.LEFT)
        tf_combo.bind('<<ComboboxSelected>>', self._on_timeframe_change)

        # Contenedor principal
        main_container = tk.Frame(self.root, bg=DARK_BG)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Fila superior: Métricas y Gráfico
        top_row = tk.Frame(main_container, bg=DARK_BG)
        top_row.pack(fill=tk.X, pady=(0, 20))

        # Métricas principales - VERSIÓN COMPACTADA CON COMISIONES POR PERÍODO
        metrics_frame = tk.Frame(top_row, bg=DARK_BG)
        metrics_frame.pack(side=tk.LEFT, fill=tk.Y)

        # 🎯 HEADER DE MÉTRICAS - ASEGURAR VISIBILIDAD
        metrics_header = tk.Frame(metrics_frame, bg=DARK_BG, height=30)
        metrics_header.pack(fill=tk.X)
        metrics_header.pack_propagate(False)  # ✅ IMPORTANTE: Mantener tamaño
        
        tk.Label(metrics_header, text="📊 PERFORMANCE METRICS", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, pady=5)
        
        # ✅ INDICADOR - ASEGURAR VISIBILIDAD
        self.metrics_indicator = tk.Label(metrics_header, text="●", fg=TEXT_SECONDARY, 
                                        font=("Arial", 16), bg=DARK_BG, cursor="hand2")  # ✅ Tamaño aumentado
        self.metrics_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        self.section_indicators['metrics'] = self.metrics_indicator

        self.total_balance_label = self.create_metric_card(
            metrics_frame, "💰 TOTAL BALANCE", "$0.00", ACCENT_COLOR
        )

        # CONTENEDOR COMPACTO PARA PERFORMANCE CAPITAL
        capital_container = tk.Frame(metrics_frame, bg=DARK_BG)
        capital_container.pack(fill=tk.X, pady=(0, 10))

        tk.Label(capital_container, text="📈 PERFORMANCE", bg=DARK_BG, fg=TEXT_SECONDARY,
                font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 5))

        # Fila 1: Performance capital corto
        capital_short_frame = tk.Frame(capital_container, bg=DARK_BG)
        capital_short_frame.pack(fill=tk.X, pady=(0, 5))

        self.change_30m_label = self.create_compact_metric(capital_short_frame, "30m", "+0.00%", TEXT_SECONDARY)
        self.change_1h_label = self.create_compact_metric(capital_short_frame, "1h", "+0.00%", TEXT_SECONDARY)
        self.change_2h_label = self.create_compact_metric(capital_short_frame, "2h", "+0.00%", TEXT_SECONDARY)
        self.change_4h_label = self.create_compact_metric(capital_short_frame, "4h", "+0.00%", TEXT_SECONDARY)

        # Fila 2: Performance capital largo
        capital_long_frame = tk.Frame(capital_container, bg=DARK_BG)
        capital_long_frame.pack(fill=tk.X, pady=(0, 10))

        self.change_1d_label = self.create_compact_metric(capital_long_frame, "1D", "+0.00%", TEXT_SECONDARY)
        self.change_1w_label = self.create_compact_metric(capital_long_frame, "1W", "+0.00%", TEXT_SECONDARY)
        self.change_1m_label = self.create_compact_metric(capital_long_frame, "1M", "+0.00%", TEXT_SECONDARY)
        self.change_1y_label = self.create_compact_metric(capital_long_frame, "1Y", "+0.00%", TEXT_SECONDARY)

        # CONTENEDOR COMPACTO PARA COMISIONES
        fees_container = tk.Frame(metrics_frame, bg=DARK_BG)
        fees_container.pack(fill=tk.X, pady=(0, 10))

        tk.Label(fees_container, text="💸 ESTIMATED BINANCE FEES", bg=DARK_BG, fg=TEXT_SECONDARY,
                font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 5))

        # Fila única: Comisiones por período
        fees_frame = tk.Frame(fees_container, bg=DARK_BG)
        fees_frame.pack(fill=tk.X)

        self.fees_1d_label = self.create_compact_metric(fees_frame, "1D", "$0.00", DANGER_COLOR)
        self.fees_1w_label = self.create_compact_metric(fees_frame, "1W", "$0.00", DANGER_COLOR)
        self.fees_1m_label = self.create_compact_metric(fees_frame, "1M", "$0.00", DANGER_COLOR)
        self.fees_1y_label = self.create_compact_metric(fees_frame, "1Y", "$0.00", DANGER_COLOR)

        # Gráfico principal
        chart_frame = tk.Frame(top_row, bg=DARK_BG)
        chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))

        # 🎯 HEADER DE GRÁFICO - ASEGURAR VISIBILIDAD
        chart_header = tk.Frame(chart_frame, bg=DARK_BG, height=30)
        chart_header.pack(fill=tk.X)
        chart_header.pack_propagate(False)  # ✅ IMPORTANTE: Mantener tamaño
        
        tk.Label(chart_header, text="📈 BALANCE GRAPH", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, pady=5)
        
        # ✅ INDICADOR - ASEGURAR VISIBILIDAD
        self.chart_indicator = tk.Label(chart_header, text="●", fg=TEXT_SECONDARY,
                                    font=("Arial", 16), bg=DARK_BG, cursor="hand2")  # ✅ Tamaño aumentado
        self.chart_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        self.section_indicators['chart'] = self.chart_indicator
        
        self.fig = Figure(figsize=(10, 4), facecolor=DARK_BG)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(CARD_BG)
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Fila inferior: Tokens y Cartera
        bottom_row = tk.Frame(main_container, bg=DARK_BG)
        bottom_row.pack(fill=tk.BOTH, expand=True)

        # Panel de tokens
        tokens_frame = tk.Frame(bottom_row, bg=DARK_BG)
        tokens_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 🎯 HEADER DE TOKENS - ASEGURAR VISIBILIDAD
        tokens_header = tk.Frame(tokens_frame, bg=DARK_BG, height=30)
        tokens_header.pack(fill=tk.X)
        tokens_header.pack_propagate(False)  # ✅ IMPORTANTE: Mantener tamaño
        
        tk.Label(tokens_header, text="🎯 TRADING SIGNALS", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, pady=5)
        
        # ✅ INDICADOR - ASEGURAR VISIBILIDAD
        self.tokens_indicator = tk.Label(tokens_header, text="●", fg=TEXT_SECONDARY, 
                                    font=("Arial", 16), bg=DARK_BG, cursor="hand2")  # ✅ Tamaño aumentado
        self.tokens_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        self.section_indicators['tokens'] = self.tokens_indicator


        # Contenedor para tokens en grid (3 columnas)
        self.tokens_container = tk.Frame(tokens_frame, bg=DARK_BG)
        self.tokens_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.token_frames = {}
        self.create_token_cards_grid()

        # Panel de cartera
        portfolio_frame = tk.Frame(bottom_row, bg=DARK_BG, width=400)
        portfolio_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(20, 0))
        portfolio_frame.pack_propagate(False)

        # 🎯 HEADER DE CARTERA - ASEGURAR VISIBILIDAD
        portfolio_header = tk.Frame(portfolio_frame, bg=DARK_BG, height=30)
        portfolio_header.pack(fill=tk.X)
        portfolio_header.pack_propagate(False)  # ✅ IMPORTANTE: Mantener tamaño
        
        tk.Label(portfolio_header, text="💼 BINANCE WALLET", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, pady=5)
        
        # ✅ INDICADOR - ASEGURAR VISIBILIDAD
        self.portfolio_indicator = tk.Label(portfolio_header, text="●", fg=TEXT_SECONDARY,
                                        font=("Arial", 16), bg=DARK_BG, cursor="hand2")  # ✅ Tamaño aumentado
        self.portfolio_indicator.pack(side=tk.LEFT, padx=5, pady=5)
        self.section_indicators['portfolio'] = self.portfolio_indicator


        # Gráfico de cartera
        self.portfolio_fig = Figure(figsize=(4, 2.8), facecolor=DARK_BG)
        self.portfolio_ax = self.portfolio_fig.add_subplot(111)
        self.portfolio_ax.set_facecolor(CARD_BG)
        self.portfolio_canvas = FigureCanvasTkAgg(self.portfolio_fig, portfolio_frame)
        self.portfolio_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        # Lista de activos
        self.portfolio_tree = ttk.Treeview(portfolio_frame, columns=('Asset', 'Balance', 'USD', '%'), 
                                        show='headings', height=8)
        self.portfolio_tree.heading('Asset', text='SYMBOL')
        self.portfolio_tree.heading('Balance', text='AMMOUNT')
        self.portfolio_tree.heading('USD', text='USD')
        self.portfolio_tree.heading('%', text='%')
        
        self.portfolio_tree.column('Asset', width=80)
        self.portfolio_tree.column('Balance', width=100)
        self.portfolio_tree.column('USD', width=100)
        self.portfolio_tree.column('%', width=60)

        self.portfolio_tree.pack(fill=tk.BOTH, expand=True)

        # Logs de trading
        log_frame = tk.Frame(bottom_row, bg=DARK_BG, width=400)
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(20, 0))
        log_frame.pack_propagate(False)

        tk.Label(log_frame, text="📋 LOGS", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(anchor="w")

        self.log_text = tk.Text(log_frame, height=15, bg=CARD_BG, fg=TEXT_COLOR, 
                            font=("Consolas", 9), wrap=tk.WORD)
        self.setup_log_tags()
        scrollbar_log = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar_log.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 0))
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)

        # ✅ CONFIGURAR TOOLTIPS DESPUÉS DE CREAR TODOS LOS INDICADORES
        self.setup_tooltips()

    def start_all_continuous_pulses(self):
        """✅ INICIAR TODOS LOS PULSOS AL ARRANCAR - VERSIÓN MEJORADA"""
        if self.closing:
            return
            
        print("🔄 Iniciando pulsos continuos para todas las secciones...")
        
        for section_name in ['tokens', 'metrics', 'portfolio', 'chart']:
            # ✅ VERIFICAR SI ESTA SECCIÓN TIENE TIMESTAMP VÁLIDO
            if section_name in self.last_update_time:
                current_time = time.time()
                last_update = self.last_update_time[section_name]
                update_interval = self.update_intervals.get(section_name, 60)
                
                # Solo iniciar pulso si la última actualización fue reciente
                # (evita pulsos eternos si la sección nunca se actualizó realmente)
                time_since_update = current_time - last_update
                
                if time_since_update < update_interval * 2:  # Máximo 2x el intervalo
                    self.start_continuous_pulse(section_name)
                    print(f"   ✅ Pulso iniciado para {section_name} (hace {time_since_update:.1f}s)")
                else:
                    # Si hace mucho que no se actualiza, dejar en gris
                    indicator = self.section_indicators.get(section_name)
                    if indicator:
                        indicator.config(fg=TEXT_SECONDARY)
                        print(f"   ⚪ {section_name} en gris (sin actualización reciente)")
            else:
                # Si nunca se actualizó, dejar en gris
                indicator = self.section_indicators.get(section_name)
                if indicator:
                    indicator.config(fg=TEXT_SECONDARY)
                print(f"   ⚪ {section_name} en gris (sin timestamp)")

    def setup_tooltips(self):
        """✅ CONFIGURAR TOOLTIPS - VERSIÓN MEJORADA"""
        print("🔧 Configurando tooltips para indicadores...")
        
        # Verificar que todos los indicadores existen
        for section in ['tokens', 'metrics', 'portfolio', 'chart']:
            indicator = self.section_indicators.get(section)
            debug_label = getattr(self, f"{section}_debug_label", None)
            print(f"   ✅ {section}: Indicador={indicator is not None}, DebugLabel={debug_label is not None}")
            
            if indicator:
                # Remover bindings existentes para evitar duplicados
                indicator.unbind("<Enter>")
                indicator.unbind("<Leave>")
                
                # Configurar nuevos bindings
                indicator.bind("<Enter>", lambda e, s=section: self.show_tooltip(e, s))
                indicator.bind("<Leave>", self.hide_tooltip)
                print(f"   🎯 Tooltip configurado para {section}")

    def show_tooltip(self, event, section_name):
        """Mostrar tooltip con última actualización"""
        last_time = self.last_update_times.get(section_name, "Nunca")
        tooltip_text = f"Última actualización: {last_time}"
        
        # Crear tooltip
        self.tooltip = tk.Toplevel()
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = tk.Label(self.tooltip, text=tooltip_text, background="#ffffe0", 
                        relief='solid', borderwidth=1, font=("Arial", 9))
        label.pack()

    def hide_tooltip(self, event=None):
        """Ocultar tooltip"""
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()

    def start_continuous_pulse(self, section_name):
        """✅ PULSO CONTINUO - desde actualización hasta próxima actualización"""
        if self.closing:
            return
            
        indicator = self.section_indicators.get(section_name)
        if not indicator or not indicator.winfo_exists():
            return
        
        # ✅ CALCULAR DURACIÓN TOTAL HASTA PRÓXIMA ACTUALIZACIÓN
        current_time = time.time()
        last_update = self.last_update_time.get(section_name, current_time)
        update_interval = self.update_intervals.get(section_name, 60)
        
        # Tiempo total del pulso (desde última actualización hasta próxima)
        total_pulse_duration = update_interval
        
        # Tiempo ya transcurrido desde última actualización
        time_elapsed = current_time - last_update
        
        # Tiempo restante para completar el pulso
        time_remaining = max(0.1, total_pulse_duration - time_elapsed)
        
        print(f"   🔄 Pulso continuo {section_name}: {time_remaining:.1f}s restantes")
        
        def continuous_pulse_frame(start_time=current_time):
            if self.closing or not indicator or not indicator.winfo_exists():
                return
                
            # Calcular progreso del pulso (0.0 = inicio, 1.0 = fin)
            current_elapsed = time.time() - start_time
            progress = min(current_elapsed / total_pulse_duration, 1.0)
            
            if progress >= 1.0:
                # ✅ PULSO COMPLETADO - volver a gris y esperar próxima actualización
                try:
                    indicator.config(fg=TEXT_SECONDARY)
                    print(f"   ⚪ Pulso continuo {section_name} completado")
                except:
                    pass
                return
            
            # ✅ ALGORITMO DE FADE CONTINUO
            # Progreso 0.0: VERDE BRILLANTE (#00ff00) - acaba de actualizarse
            # Progreso 1.0: GRIS (#bbbbbb) - próxima actualización
            
            start_r, start_g, start_b = 0, 255, 0      # #00ff00
            end_r, end_g, end_b = 187, 187, 187        # #bbbbbb
            
            current_r = int(start_r + (end_r - start_r) * progress)
            current_g = int(start_g + (end_g - start_g) * progress) 
            current_b = int(start_b + (end_b - start_b) * progress)
            
            current_r = max(0, min(255, current_r))
            current_g = max(0, min(255, current_g))
            current_b = max(0, min(255, current_b))
            
            color = f"#{current_r:02x}{current_g:02x}{current_b:02x}"
            
            try:
                indicator.config(fg=color)
            except:
                pass
            
            # ✅ SIGUIENTE FRAME EN 100ms (ACTUALIZACIÓN CONTINUA)
            if hasattr(self, 'root') and self.root and not self.closing:
                self.root.after(100, continuous_pulse_frame)
        
        # ✅ INICIAR PULSO CONTINUO
        try:
            # Empezar desde el color correspondiente al progreso actual
            initial_progress = time_elapsed / total_pulse_duration
            initial_r = int(0 + (187 - 0) * initial_progress)
            initial_g = int(255 + (187 - 255) * initial_progress)
            initial_b = int(0 + (187 - 0) * initial_progress)
            
            initial_color = f"#{initial_r:02x}{initial_g:02x}{initial_b:02x}"
            indicator.config(fg=initial_color)
            
            print(f"   🟢 Pulso continuo iniciado para {section_name}")
        except:
            return
            
        # Iniciar animación continua
        if hasattr(self, 'root') and self.root:
            self.root.after(100, continuous_pulse_frame)

    def _do_activate_indicator(self, section_name):
        """✅ ACTIVACIÓN CON CONTROL DE DUPLICADOS"""
        if self.closing:
            return
            
        # ✅ ACTUALIZAR TIMESTAMP PRIMERO
        current_time = time.time()
        self.last_update_time[section_name] = current_time
        
        current_time_str = datetime.now().strftime("%H:%M:%S")
        self.last_update_times[section_name] = current_time_str
        
        # ✅ INICIAR PULSO (el método ahora controla duplicados)
        self.start_continuous_pulse(section_name)

    def thread_safe_reset(self, section_name):
        """✅ RESET SEGURO DESDE CUALQUIER HILO"""
        try:
            if self.closing:
                return
                
            def safe_reset_operation():
                try:
                    if self.closing or not hasattr(self, 'root') or not self.root:
                        return
                        
                    indicator = self.section_indicators.get(section_name)
                    if indicator and indicator.winfo_exists():
                        indicator.config(fg=TEXT_SECONDARY)
                        print(f"   ⚪ Indicador {section_name} RESETEADO visualmente")
                        
                except Exception as e:
                    if "main thread is not in main loop" not in str(e) and "has been destroyed" not in str(e):
                        print(f"❌ Error en safe_reset_operation {section_name}: {e}")
            
            # ✅ EJECUTAR EN HILO PRINCIPAL
            if hasattr(self, 'root') and self.root:
                self.root.after(0, safe_reset_operation)
                
        except Exception as e:
            print(f"❌ Error en thread_safe_reset {section_name}: {e}")

    def _on_timeframe_change(self, event=None):
        """Actualizar gráfico cuando cambia el timeframe"""
        print(f"🔄 Cambiando timeframe a: {self.tf_var.get()}")
        if hasattr(self, 'history') and self.history:
            total_balance = self.history[-1][1] if self.history else 0
            # Forzar actualización inmediata
            self._update_main_chart(total_balance)
        else:
            print("⚠️ No hay historial para mostrar")

    def create_button(self, parent, text, color, command):
        """Crea un botón estilizado"""
        return tk.Button(parent, text=text, bg=color, fg='black', 
                        font=("Arial", 10, "bold"), relief='flat',
                        padx=15, pady=8, command=command, cursor='hand2')

    def create_metric_card(self, parent, title, value, color):
        """Crea una tarjeta de métrica"""
        card = tk.Frame(parent, bg=CARD_BG, relief='flat', bd=1, 
                       highlightbackground=TEXT_SECONDARY, highlightthickness=1)
        card.pack(fill=tk.X, pady=(0, 10), padx=(0, 10))
        
        tk.Label(card, text=title, bg=CARD_BG, fg=TEXT_SECONDARY,
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        value_label = tk.Label(card, text=value, bg=CARD_BG, fg=color,
                             font=("Arial", 18, "bold"))
        value_label.pack(anchor="w", padx=10, pady=(0, 10))
        
        return value_label

    def create_token_cards_grid(self):
        """Crea las tarjetas de tokens en grid de 3 columnas"""
        from config import SYMBOLS
        
        # Calcular número de filas necesarias
        num_tokens = len(SYMBOLS)
        num_columns = 3
        num_rows = (num_tokens + num_columns - 1) // num_columns  # Redondeo hacia arriba
        
        # Configurar grid
        for i in range(num_columns):
            self.tokens_container.grid_columnconfigure(i, weight=1, uniform="col")
        for i in range(num_rows):
            self.tokens_container.grid_rowconfigure(i, weight=1)
        
        # Crear tarjetas en grid
        for i, symbol in enumerate(SYMBOLS):
            row = i // num_columns
            col = i % num_columns
            
            card = self.create_token_card(symbol)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.token_frames[symbol] = card

    def create_token_card(self, symbol):
        """Crea una tarjeta individual de token con símbolo + %24H + precio en misma línea"""
        card = tk.Frame(self.tokens_container, bg=CARD_BG, relief='flat', bd=1,
                    highlightbackground=TEXT_SECONDARY, highlightthickness=1,
                    width=280, height=200)
        card.pack_propagate(False)
        
        # Header del token - TODO EN MISMA LÍNEA
        header = tk.Frame(card, bg=CARD_BG)
        header.pack(fill=tk.X, padx=10, pady=8)
        
        # ✅ SÍMBOLO + %24H (izquierda)
        symbol_change_frame = tk.Frame(header, bg=CARD_BG)
        symbol_change_frame.pack(side=tk.LEFT)
        
        # Símbolo y %24H en horizontal
        symbol_label = tk.Label(symbol_change_frame, text=symbol.replace("USDC", ""), 
                            bg=CARD_BG, fg=ACCENT_COLOR, font=("Arial", 14, "bold"))
        symbol_label.pack(side=tk.LEFT)
        
        # ✅ %24H AL LADO DEL SÍMBOLO
        daily_change_header_label = tk.Label(symbol_change_frame, text=" +0.00%", 
                                        bg=CARD_BG, fg=TEXT_SECONDARY, font=("Arial", 11))
        daily_change_header_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # ✅ PRECIO ACTUAL (derecha)
        price_label = tk.Label(header, text="$0.0000", bg=CARD_BG, fg=TEXT_COLOR,
                            font=("Arial", 12, "bold"))
        price_label.pack(side=tk.RIGHT)
        
        # Información de balance
        balance_frame = tk.Frame(card, bg=CARD_BG)
        balance_frame.pack(fill=tk.X, padx=10, pady=(8, 5))
        
        balance_label = tk.Label(balance_frame, text="0.000000 → $0.00 (0.0%)", 
                                bg=CARD_BG, fg=TEXT_SECONDARY, font=("Arial", 9))
        balance_label.pack(anchor="w")
        
        # CONTENEDOR PARA SEÑALES NUMÉRICAS
        signals_container = tk.Frame(card, bg=CARD_BG)
        signals_container.pack(fill=tk.X, padx=10, pady=8)
        
        # Crear timeframes en fila horizontal
        timeframe_frame = tk.Frame(signals_container, bg=CARD_BG)
        timeframe_frame.pack()
        
        circles = {}
        timeframes = ["30m", "1h", "2h"]
        
        for i, tf in enumerate(timeframes):
            # Frame individual para cada timeframe
            tf_frame = tk.Frame(timeframe_frame, bg=CARD_BG)
            tf_frame.pack(side=tk.LEFT, padx=10)
            
            # Canvas para el círculo
            canvas = tk.Canvas(tf_frame, width=28, height=28, bg=CARD_BG, highlightthickness=0)
            canvas.pack()
            
            # Círculo centrado
            circle_id = canvas.create_oval(4, 4, 24, 24, fill="gray", outline=TEXT_SECONDARY, width=1)
            
            # Label para el valor numérico
            value_label = tk.Label(tf_frame, text="0.00", bg=CARD_BG, fg=TEXT_SECONDARY, 
                                font=("Arial", 8, "bold"))
            value_label.pack()
            
            # Texto del timeframe
            tk.Label(tf_frame, text=tf, bg=CARD_BG, fg=TEXT_SECONDARY, 
                    font=("Arial", 8, "bold")).pack()
            
            # Guardar canvas, circle_id y value_label
            circles[tf] = {
                'canvas': canvas,
                'circle_id': circle_id,
                'value_label': value_label
            }
        
        # Peso y señal general
        signal_frame = tk.Frame(card, bg=CARD_BG)
        signal_frame.pack(fill=tk.X, padx=10, pady=(8, 8))
        
        # Contenedor para centrar
        center_frame = tk.Frame(signal_frame, bg=CARD_BG)
        center_frame.pack(expand=True)
        
        weight_label = tk.Label(center_frame, text="WEIGHT: 0.00", bg=CARD_BG, fg=WARNING_COLOR,
                            font=("Arial", 11, "bold"))
        weight_label.pack(side=tk.LEFT, padx=(0, 10))
        
        signal_label = tk.Label(center_frame, text="SIGNAL: N/A", bg=CARD_BG, fg=TEXT_SECONDARY,
                            font=("Arial", 10, "bold"))
        signal_label.pack(side=tk.LEFT)
        
        # ✅ Guardar referencias
        card.data = {
            "symbol": symbol,
            "price_label": price_label,
            "daily_change_header_label": daily_change_header_label,  # ← %24H
            "balance_label": balance_label,
            "circles": circles,
            "weight_label": weight_label,
            "signal_label": signal_label
        }
        
        return card

    def calculate_all_tokens_daily_change(self):
        """✅ CAMBIOS DIARIOS - LOGS REDUCIDOS"""
        try:
            # ✅ LOG INICIAL REDUCIDO
            all_tickers = self.bot.client.get_ticker()
            
            daily_changes = {}
            symbols_found = 0
            
            for ticker in all_tickers:
                symbol = ticker['symbol']
                if symbol in self.token_frames:
                    if 'priceChangePercent' in ticker:
                        price_change_percent = float(ticker['priceChangePercent'])
                        sign = "+" if price_change_percent >= 0 else ""
                        daily_changes[symbol] = f"{sign}{price_change_percent:.2f}%"
                        symbols_found += 1
                    else:
                        daily_changes[symbol] = "+0.00%"
            
            # ✅ ASEGURAR VALORES (SIN LOG)
            for symbol in self.token_frames.keys():
                if symbol not in daily_changes:
                    daily_changes[symbol] = "+0.00%"
            
            # ✅ LOG FINAL RESUMIDO
            print(f"   📈 Cambios diarios: {symbols_found}/{len(self.token_frames)} tokens")
            return daily_changes
                
        except Exception as e:
            print(f"   ❌ Error cambios diarios: {e}")
            return {symbol: "+0.00%" for symbol in self.token_frames.keys()}

    def load_history(self):
        """Carga el historial y comprime datos antiguos"""
        history_file = "capital_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    data = json.load(f)
                
                loaded_history = [(datetime.fromisoformat(d[0]), d[1]) for d in data]
                print(f"📈 Historial cargado: {len(loaded_history)} puntos")
                
                # COMPRIMIR DATOS ANTIGUOS: mantener solo 1 punto por hora para datos > 1 semana
                if len(loaded_history) > 1000:
                    compressed = self._compress_old_data(loaded_history)
                    print(f"📊 Historial comprimido: {len(compressed)} puntos")
                    return compressed
                
                return loaded_history
                
            except Exception as e:
                print(f"❌ Error cargando historial: {e}")
            
        # ✅ Si no hay historial, crear uno inicial
        if self.bot and hasattr(self.bot, 'account'):
            try:
                initial_balance = self.bot.account.get_balance_usdc()
                initial_history = [(datetime.now(), initial_balance)]
                print(f"💰 Historial inicial creado: ${initial_balance:,.2f}")
                return initial_history
            except:
                pass
        
    def _compress_old_data(self, history):
        """Comprime datos antiguos manteniendo 1 punto por hora"""
        if len(history) <= 1000:
            return history
        
        # Separar datos recientes (última semana) y antiguos
        one_week_ago = datetime.now() - timedelta(days=7)
        recent_data = [point for point in history if point[0] >= one_week_ago]
        old_data = [point for point in history if point[0] < one_week_ago]
        
        if len(old_data) <= 500:
            return history
        
        # Comprimir datos antiguos: 1 punto por hora
        compressed_old = []
        current_hour = None
        
        for time_point, value in sorted(old_data, key=lambda x: x[0]):
            hour_key = time_point.replace(minute=0, second=0, microsecond=0)
            if hour_key != current_hour:
                compressed_old.append((time_point, value))
                current_hour = hour_key
        
        return compressed_old + recent_data

    def save_history(self):
        """Guarda el historial inmediatamente"""
        try:
            history_file = "capital_history.json"
            data_to_save = [(dt.isoformat(), val) for dt, val in self.history]
            
            # ✅ GUARDADO RÁPIDO sin indentación para mejor performance
            with open(history_file, "w") as f:
                json.dump(data_to_save, f)
            
            # ✅ SOLO MOSTRAR DEBUG OCASIONALMENTE para no saturar la consola
            if len(self.history) % 10 == 0:  # Cada 10 updates
                print(f"💾 Historial guardado: {len(self.history)} puntos")
                
        except Exception as e:
            print(f"❌ Error guardando historial: {e}")

    def safe_start(self):
        """Inicia el bot de forma segura"""
        if self.bot is None:
            self.log_trade("❌ No hay bot conectado. Usa 'Reiniciar App'", 'RED')
            return
        threading.Thread(target=self.bot.start, daemon=True).start()

    def safe_stop(self):
        """Detiene el bot de forma segura"""
        if self.bot is None:
            self.log_trade("❌ No hay bot conectado", 'RED')
            return
        self.bot.stop()

    def safe_rebalance(self):
        """Rebalance manual seguro"""
        if self.bot is None:
            self.log_trade("❌ No hay bot conectado", 'RED')
            return
        threading.Thread(target=self.bot.rebalance_manual, daemon=True).start()

    def safe_restart_app(self):
        """Reinicia toda la aplicación completamente"""
        from tkinter import messagebox
        import sys
        import os
        import subprocess
        
        result = messagebox.askyesno(
            "Reiniciar Aplicación", 
            "¿Reiniciar toda la aplicación?"
        )
        
        if result:
            self.log_trade("🔄 Reiniciando aplicación...", 'BLUE')
            if self.bot:
                self.bot.stop_completely()
            self.root.after(1000, self._perform_restart)

    def safe_ui_update(self, func, *args, **kwargs):
        """✅ EJECUTAR FUNCIÓN DE UI - CON DETECCIÓN DE ESTADO DE TKINTER"""
        # ✅ VERIFICAR ESTADO COMPLETO DE TKINTER
        if (self.closing or 
            not hasattr(self, 'root') or 
            not self.root or 
            not hasattr(self.root, 'tk') or
            not hasattr(self.root, '_windowingsystem')):
            return
            
        def safe_wrapper():
            # ✅ VERIFICAR NUEVAMENTE ANTES DE EJECUTAR
            if (self.closing or 
                not hasattr(self, 'root') or 
                not self.root or 
                not hasattr(self.root, 'tk')):
                return
                
            try:
                func(*args, **kwargs)
            except Exception as e:
                if "main thread is not in main loop" not in str(e) and "application has been destroyed" not in str(e):
                    print(f"❌ UI update error in {func.__name__}: {e}")
        
        try:
            # ✅ VERIFICAR QUE TKINTER ESTÉ ACTIVO
            if hasattr(self.root, 'tk') and hasattr(self.root.tk, 'call'):
                self.root.after(0, safe_wrapper)
            else:
                print("⚠️ Tkinter no está disponible para safe_ui_update")
        except Exception as e:
            if "main thread is not in main loop" not in str(e):
                print(f"❌ Error scheduling {func.__name__}: {e}")

    def log_trade(self, msg, color="white"):
        """Agrega mensaje al log de forma thread-safe"""
        # Auto-detectar tipo de mensaje por contenido si no se especifica color
        if color == "white":
            if "COMPRA" in msg.upper() or "🟢" in msg:
                color = "GREEN"
            elif "VENTA" in msg.upper() or "🔴" in msg:
                color = "RED" 
            elif "ERROR" in msg.upper() or "❌" in msg:
                color = "RED"
            elif "CICLO" in msg.upper() or "🔄" in msg:
                color = "BLUE"
            elif "ADVERTENCIA" in msg.upper() or "⚠️" in msg:
                color = "YELLOW"
        
        self.data_queue.put(("log", msg, color))

    def update_token_data(self, symbol_data):
        self.data_queue.put(("token_data", symbol_data))

    def update_metrics(self, metrics):
        self.data_queue.put(("metrics", metrics))

    def update_portfolio(self, portfolio_data):
        self.data_queue.put(("portfolio", portfolio_data))

    def setup_memory_cleanup(self):
        """Limpieza periódica de memoria"""
        self.root.after(120000, self.cleanup_memory)  # Cada 2 minutos

    def apply_change_colors(self, metrics):
        """Aplica colores según cambios positivos/negativos y comisiones"""
        # Performance capital (verde/rojo)
        capital_changes = {
            'change_30m': self.change_30m_label,
            'change_1h': self.change_1h_label,
            'change_2h': self.change_2h_label,
            'change_4h': self.change_4h_label,
            'change_1d': self.change_1d_label,
            'change_1w': self.change_1w_label,
            'change_1m': self.change_1m_label,
            'change_1y': self.change_1y_label
        }
        
        for change_key, label in capital_changes.items():
            value = metrics.get(change_key, "+0.00%")
            if value.startswith('+'):
                label.config(fg=ACCENT_COLOR)  # Verde para positivo
            elif value.startswith('-'):
                label.config(fg=DANGER_COLOR)  # Rojo para negativo
            else:
                label.config(fg=TEXT_SECONDARY)  # Gris para neutro
        
        # Comisiones (siempre rojo/naranja según monto)
        fees_changes = {
            'fees_1d': self.fees_1d_label,
            'fees_1w': self.fees_1w_label,
            'fees_1m': self.fees_1m_label,
            'fees_1y': self.fees_1y_label
        }
        
        for fee_key, label in fees_changes.items():
            value = metrics.get(fee_key, "$0.00")
            fee_amount = float(value.replace('$', '').replace(',', ''))
            
            if fee_amount > 10.0:
                label.config(fg=DANGER_COLOR)  # Rojo para comisiones altas
            elif fee_amount > 1.0:
                label.config(fg=WARNING_COLOR)  # Naranja para comisiones medias
            else:
                label.config(fg=TEXT_SECONDARY)  # Gris para comisiones bajas

    def _schedule_background_task(self, task_function):
        """Programa una tarea en background de forma segura"""
        def background_wrapper():
            try:
                task_function()
            except Exception as e:
                print(f"Error en tarea background: {e}")
                
        # Usar executor en lugar de threading directo
        future = self.update_executor.submit(background_wrapper)
        future.add_done_callback(self._handle_task_completion)
        
    def _handle_task_completion(self, future):
        """Maneja la finalización de tareas"""
        try:
            future.result()  # Esto propaga cualquier excepción
        except Exception as e:
            print(f"Error en tarea completada: {e}")

    def _should_update(self, update_type, current_time):
        """Verifica si debe ejecutarse una actualización"""
        if self.is_updating.get(update_type, False):
            return False
            
        last_time = self.last_update_time.get(update_type, 0)
        interval = self.update_intervals[update_type]
        
        should_update = (current_time - last_time) >= interval
        
        if should_update:
            print(f"✅ {update_type} necesita actualización - último: {last_time}, actual: {current_time}, intervalo: {interval}")
        
        return should_update


    def _update_tokens_background(self):
        """✅ ACTUALIZACIÓN DE TOKENS - LOGS REDUCIDOS"""
        print("🔄 Actualizando tokens...")
        
        if self.closing or not self.bot:
            return
            
        if self.is_updating['tokens']:
            return
            
        self.is_updating['tokens'] = True
        try:
            # ✅ ACTIVAR INDICADOR (LOG REDUCIDO)
            self.update_section_indicator('tokens')
            
            symbol_data = {}
            
            # ✅ OBTENER CAMBIOS DIARIOS (LOG REDUCIDO)
            daily_changes = self.calculate_all_tokens_daily_change()
            
            # ✅ PROCESAR TOKENS (LOG REDUCIDO)
            all_symbols = list(self.token_frames.keys())
            
            for symbol in all_symbols:
                try:
                    # ✅ SOLO LOG ESENCIAL POR TOKEN
                    signals = self.bot.manager.get_signals(symbol)
                    weight = self.bot.manager.calculate_weight(signals)
                    price = self.bot.account.get_current_price(symbol)
                    balance = self.bot.account.get_symbol_balance(symbol)
                    usd_value = balance * price
                    total_balance = self.bot.account.get_balance_usdc()
                    pct = (usd_value / total_balance * 100) if total_balance > 0 else 0
                    
                    daily_change = daily_changes.get(symbol, "+0.00%")
                    
                    symbol_data[symbol] = {
                        'signals': signals,
                        'weight': weight,
                        'price': price,
                        'balance': balance,
                        'usd': usd_value,
                        'pct': pct,
                        'daily_change': daily_change
                    }
                    
                    # ✅ SOLO LOG RESUMIDO
                    print(f"   ✅ {symbol}: ${price:.4f}, {daily_change}, peso:{weight:.2f}")
                    
                except Exception as e:
                    print(f"   ❌ {symbol}: {e}")
                    continue

            # ✅ ENVIAR DATOS (LOG REDUCIDO)
            if symbol_data:
                self.data_queue.put(("token_data", symbol_data))
                print(f"✅ {len(symbol_data)} tokens procesados")
            else:
                print("⚠️ No se obtuvieron datos")
                
        except Exception as e:
            print(f"❌ Error en tokens: {e}")
        finally:
            self.is_updating['tokens'] = False
            self.last_update_time['tokens'] = time.time()

    def _update_metrics_background(self):
        """✅ ACTUALIZACIÓN OPTIMIZADA DE MÉTRICAS"""
        if self.closing or not self.bot:
            return
            
        self.is_updating['metrics'] = True
        try:
                # ✅ ACTIVAR INDICADOR
            self.update_section_indicator('metrics')
            
            total_balance = self.bot.account.get_balance_usdc()
            
            # ✅ ACTUALIZAR HISTORIAL (RÁPIDO)
            now = datetime.now()
            self._update_history(now, total_balance)
            
            # ✅ MÉTRICAS BÁSICAS (RÁPIDAS)
            performance_data = self.calculate_all_performance_metrics(total_balance)
            
            # ✅ COMISIONES CACHEADAS (NO calcular cada vez)
            fees_data = self._get_cached_fees()
            
            metrics = {
                'total_balance': total_balance,
                'change_30m': performance_data['change_30m'],
                'change_1h': performance_data['change_1h'],
                'change_2h': performance_data['change_2h'],
                'change_4h': performance_data['change_4h'],
                'change_1d': performance_data['change_1d'],
                'change_1w': performance_data['change_1w'],
                'change_1m': performance_data['change_1m'],
                'change_1y': performance_data['change_1y'],
                'fees_1d': f"${fees_data['1d']:.2f}",
                'fees_1w': f"${fees_data['1w']:.2f}",
                'fees_1m': f"${fees_data['1m']:.2f}",
                'fees_1y': f"${fees_data['1y']:.2f}",
            }
            
            self.data_queue.put(("metrics", metrics))
            
        finally:
            self.is_updating['metrics'] = False
            self.last_update_time['metrics'] = time.time()

    def _update_portfolio_background(self):
        """✅ ACTUALIZACIÓN OPTIMIZADA DE CARTERA - MENOS FRECUENTE"""
        if self.closing or not self.bot:
            return
        
        self.is_updating['portfolio'] = True
        try:
                        # ✅ ACTIVAR INDICADOR
            self.update_section_indicator('portfolio')
            total_balance = self.bot.account.get_balance_usdc()
            portfolio_data = self.get_portfolio_data(total_balance)
            self.data_queue.put(("portfolio", portfolio_data))
            
        finally:
            self.is_updating['portfolio'] = False
            self.last_update_time['portfolio'] = time.time()

    def _update_chart_background(self):
        """✅ ACTUALIZACIÓN OPTIMIZADA DEL GRÁFICO"""
        if self.closing:
            return
        self.is_updating['chart'] = True
        try:
            # ✅ ACTIVAR INDICADOR DEL GRÁFICO
            self.update_section_indicator('chart')
            print("   📊 Indicador del gráfico activado")
            total_balance = self.bot.account.get_balance_usdc() if self.bot else 0
            self.data_queue.put(("chart_update", total_balance))
            
        finally:
            self.is_updating['chart'] = False
            self.last_update_time['chart'] = time.time()

    def _get_cached_daily_changes(self):
        """✅ OBTENER CAMBIOS DIARIOS CACHEADOS"""
        current_time = time.time()
        last_time = self.last_update_time.get('daily_change', 0)
        
        if (current_time - last_time) >= self.update_intervals['daily_change']:
            # Actualizar cache
            self._cached_daily_changes = self.calculate_all_tokens_daily_change()
            self.last_update_time['daily_change'] = current_time
            
        return getattr(self, '_cached_daily_changes', {})

    def _get_cached_fees(self):
        """✅ OBTENER COMISIONES CACHEADAS"""
        current_time = time.time()
        last_time = self.last_update_time.get('fees', 0)
        
        if (current_time - last_time) >= self.update_intervals['fees']:
            # Actualizar cache cada 5 minutos
            self._cached_fees = self.calculate_fees_by_period()
            self.last_update_time['fees'] = current_time
            
        return getattr(self, '_cached_fees', self.get_empty_fees())

    def process_data_queue(self):
        """Procesar cola con límite más estricto y limpieza"""
        try:
            # Limpiar cola si tiene más de 50 elementos
            if self.data_queue.qsize() > 50:
                self._clean_queue_aggressive()
                
            processed = 0
            MAX_PROCESS = 10  # Aumentar ligeramente
            
            while processed < MAX_PROCESS and not self.data_queue.empty():
                try:
                    item = self.data_queue.get_nowait()
                    processed += 1
                    
                    # ✅ VERIFICAR TKINTER ANTES DE CADA ACTUALIZACIÓN
                    if self.check_tkinter_health() != "HEALTHY":
                        break
                        
                    if item[0] == "log":
                        self._add_log_message(item[1], item[2])
                    elif item[0] == "token_data":
                        self._update_token_ui(item[1])
                    elif item[0] == "metrics":
                        self._update_metrics_ui(item[1])
                    elif item[0] == "portfolio":
                        self._update_portfolio_ui(item[1])
                    elif item[0] == "chart_update":
                        self._update_main_chart(item[1])
                        
                except queue.Empty:
                    break
                    
        except Exception as e:
            print(f"❌ Error procesando cola: {e}")
            self._clean_queue_aggressive()

    def _clean_queue_aggressive(self):
        """✅ LIMPIEZA AGRESIVA DE COLA SATURADA"""
        try:
            print(f"🧹 Limpiando cola saturada: {self.data_queue.qsize()} elementos")
            
            # Mantener solo los elementos más recientes de cada tipo
            recent_items = []
            seen_types = set()
            
            # Recoger elementos en orden inverso (más recientes primero)
            all_items = []
            while True:
                try:
                    all_items.append(self.data_queue.get_nowait())
                except queue.Empty:
                    break
            
            # Mantener el más reciente de cada tipo
            for item in reversed(all_items):
                item_type = item[0]
                if item_type not in seen_types:
                    recent_items.append(item)
                    seen_types.add(item_type)
            
            # Reinsertar los elementos más recientes
            for item in recent_items:
                try:
                    self.data_queue.put_nowait(item)
                except queue.Full:
                    break
                    
            print(f"✅ Cola limpiada: {len(recent_items)} elementos mantenidos")
            
        except Exception as e:
            print(f"❌ Error limpiando cola: {e}")

    def on_close(self):
        """✅ CIERRO MEJORADO - MARCAR EXPLÍCITAMENTE COMO CERRANDO"""
        if self.closing:
            return
        
        self.closing = True
        print("🔴 CERRANDO APLICACIÓN - Desactivando todas las actualizaciones...")
        
        # ✅ DETENER TODOS LOS HILOS Y ACTUALIZACIONES
        self.updating = False
        
        # ✅ DETENER EJECUTOR
        if hasattr(self, 'update_executor'):
            self.update_executor.shutdown(wait=False)
        
        # ✅ DETENER BOT
        if hasattr(self, 'bot') and self.bot:
            self.bot.force_stop = True
            self.bot.running = False
        
        # ✅ GUARDAR HISTORIAL
        try:
            self.save_history()
        except:
            pass
        
        # ✅ CERRAR VENTANA DE FORMA SEGURA
        try:
            if hasattr(self, 'root') and self.root:
                self.root.quit()
                self.root.destroy()
        except:
            pass
        
        print("✅ Aplicación cerrada correctamente")

    def calculate_all_performance_metrics(self, total_balance):
        """Cálculos cacheados por 30 segundos"""
        current_time = time.time()
        cache_key = f"performance_{total_balance:.0f}"
        
        # Usar cache si está fresco
        if (cache_key in self._performance_cache and 
            current_time - self._cache_time.get(cache_key, 0) < 30):
            return self._performance_cache[cache_key]
        
        # Calcular solo si es necesario
        result = {
            'change_30m': self.calculate_period_change(minutes=30),
            'change_1h': self.calculate_period_change(hours=1),
            'change_2h': self.calculate_period_change(hours=2),
            'change_4h': self.calculate_period_change(hours=4),
            'change_24h': self.calculate_period_change(hours=24),
            'change_1d': self.calculate_period_change(hours=24),  # Alias para 24h
            'change_1w': self.calculate_period_change(days=7),
            'change_1m': self.calculate_period_change(days=30),
            'change_1y': self.calculate_period_change(days=365),
        }
                
        # Actualizar cache
        self._performance_cache[cache_key] = result
        self._cache_time[cache_key] = current_time
        
        return result
        

    def calculate_period_change(self, hours=0, minutes=0, days=0):
        """Calcula cambio porcentual para cualquier período"""
        if len(self.history) < 2:
            return "+0.00%"
        
        # Calcular timestamp de inicio del período
        period_start = datetime.now()
        if days > 0:
            period_start -= timedelta(days=days)
        elif hours > 0:
            period_start -= timedelta(hours=hours)
        elif minutes > 0:
            period_start -= timedelta(minutes=minutes)
        
        # Encontrar valor más cercano al inicio del período
        start_value = None
        closest_time_diff = float('inf')
        
        for dt, val in self.history:
            time_diff = abs((dt - period_start).total_seconds())
            if time_diff < closest_time_diff:
                closest_time_diff = time_diff
                start_value = val
        
        current_value = self.history[-1][1] if self.history else 0
        
        if start_value is None or start_value == 0:
            return "+0.00%"
        
        change = ((current_value - start_value) / start_value) * 100
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.2f}%"

    def get_real_fee_rates(self):
        """Obtiene las tarifas REALES de comisión de tu cuenta Binance - CORREGIDO"""
        try:
            # get_trade_fee devuelve una lista de diccionarios
            fee_info_list = self.bot.client.get_trade_fee(symbol="BNBUSDC")
            
            if not fee_info_list:
                print("❌ No se pudieron obtener tarifas, lista vacía")
                return 0.0010
                
            # Tomar el primer elemento de la lista
            fee_info = fee_info_list[0]
            
            maker_fee = float(fee_info['makerCommission'])
            taker_fee = float(fee_info['takerCommission'])
            
            # Promedio conservador
            avg_fee = (maker_fee + taker_fee) / 2
            
            print(f"💰 Tarifas reales: Maker {maker_fee*100:.3f}%, Taker {taker_fee*100:.3f}%, Promedio {avg_fee*100:.3f}%")
            
            return avg_fee
            
        except Exception as e:
            print(f"❌ No se pudieron obtener tarifas reales, usando 0.1% por defecto: {e}")
            return 0.0010  # 0.1% por defecto

    def calculate_fees_by_period(self):
        """Calcula comisiones por período - CON TARIFAS REALES"""
        try:
            current_time = datetime.now()

            if hasattr(self, '_last_fees_calc') and \
            (current_time - self._last_fees_calc).total_seconds() < 3600:
                return getattr(self, '_cached_fees_period', self.get_empty_fees())            
            
            print("🔄 Calculando comisiones con tarifas reales...")
            
            # ✅ OBTENER TARIFAS REALES DE TU CUENTA
            real_fee_rate = self.get_real_fee_rates()
            print(f"📊 Usando tarifa real: {real_fee_rate*100:.3f}%")
            
            # Períodos reales
            real_periods = {
                '1d': timedelta(days=1),
                '30d': timedelta(days=30)
            }
            
            fees_real = {'1d': 0.0, '30d': 0.0}
            
            # Procesar símbolos
            symbols_to_process = list(self.token_frames.keys())[:5]
            
            for symbol in symbols_to_process:
                try:
                    start_time_30d = int((current_time - timedelta(days=30)).timestamp() * 1000)
                    trades = self.bot.client.get_my_trades(
                        symbol=symbol, 
                        startTime=start_time_30d,
                        limit=200
                    )
                    
                    for trade in trades:
                        trade_time = datetime.fromtimestamp(trade['time'] / 1000)
                        quote_qty = float(trade['quoteQty'])
                        
                        # ✅ USAR TARIFA REAL en lugar de 0.00085
                        trade_fee = quote_qty * real_fee_rate
                        
                        # Asignar a períodos
                        if trade_time >= (current_time - real_periods['1d']):
                            fees_real['1d'] += trade_fee
                        
                        fees_real['30d'] += trade_fee
                    
                    print(f"✅ {symbol}: {len(trades)} trades")
                            
                except Exception as e:
                    print(f"⚠️ Error en {symbol}: {e}")
                    continue
            
            # Estimaciones basadas en datos reales
            monthly_fees = fees_real['30d']
            
            if monthly_fees > 0:
                # Si tenemos datos de 1D real, proyectar 1W más inteligentemente
                if fees_real['1d'] > 0:
                    daily_avg = monthly_fees / 30
                    current_day_ratio = fees_real['1d'] / daily_avg if daily_avg > 0 else 1.0
                    # Ajustar proyección según actividad reciente
                    weekly_estimate = monthly_fees * 0.3 * current_day_ratio
                else:
                    weekly_estimate = monthly_fees * 0.3
                
                yearly_estimate = monthly_fees * 8.5
            else:
                weekly_estimate = 0.0
                yearly_estimate = 0.0
            
            fees_by_period = {
                '1d': fees_real['1d'],
                '1w': weekly_estimate, 
                '1m': monthly_fees,
                '1y': yearly_estimate
            }
            
            # Cachear resultados
            self._cached_fees_period = fees_by_period
            self._last_fees_calc = current_time
            
            print(f"💰 Comisiones REALES calculadas:")
            print(f"  Tarifa usada: {real_fee_rate*100:.3f}%")
            print(f"  1D: ${fees_by_period['1d']:.2f}")
            print(f"  1M: ${fees_by_period['1m']:.2f}")
            
            return fees_by_period
            
        except Exception as e:
            print(f"❌ Error cálculo comisiones: {e}")
            return self.get_empty_fees()

    def force_token_update(self, symbol):
        """Actualización inmediata y SEGURA de un token específico"""
        if self.closing:
            return
            
        def update_token():
            try:
                if self.closing or not hasattr(self, 'bot') or self.bot is None:
                    return
                    
                # Obtener datos frescos del token
                signals = self.bot.manager.get_signals(symbol)
                weight = self.bot.manager.calculate_weight(signals)
                price = self.bot.account.get_current_price(symbol)
                balance = self.bot.account.get_symbol_balance(symbol)
                usd_value = balance * price
                total_balance = self.bot.account.get_balance_usdc()
                pct = (usd_value / total_balance * 100) if total_balance > 0 else 0
                
                # Obtener cambio diario
                daily_changes = self.calculate_all_tokens_daily_change()
                daily_change = daily_changes.get(symbol, "+0.00%")
                
                # Actualizar UI
                symbol_data = {
                    symbol: {
                        'signals': signals,
                        'weight': weight,
                        'price': price,
                        'balance': balance,
                        'usd': usd_value,
                        'pct': pct,
                        'daily_change': daily_change
                    }
                }
                self._update_token_ui(symbol_data)
                
            except Exception as e:
                if "main thread is not in main loop" not in str(e):
                    print(f"Error en actualización inmediata de {symbol}: {e}")
        
        # Usar el método seguro
        self.safe_ui_update(update_token)

    def get_empty_fees(self):
        """Retorna estructura vacía de comisiones"""
        return {'1d': 0.0, '1w': 0.0, '1m': 0.0, '1y': 0.0}

    def calculate_token_performance(self, symbol, current_price):
        """Calcula rendimiento individual de un token"""
        try:
            # Por simplicidad, calculamos vs precio de compra promedio
            # En una implementación real, llevarías registro de precios de compra
            if not hasattr(self, 'token_purchase_prices'):
                self.token_purchase_prices = {}
            
            purchase_price = self.token_purchase_prices.get(symbol, current_price * 0.95)  # Placeholder
            
            if purchase_price == 0:
                return "+0.00%"
            
            change = ((current_price - purchase_price) / purchase_price) * 100
            sign = "+" if change >= 0 else ""
            return f"{sign}{change:.2f}%"
            
        except:
            return "+0.00%"

    def get_portfolio_data(self, total_balance):
        """Obtiene datos completos de la cartera"""
        try:
            account_info = self.bot.client.get_account()
            assets = []
            
            for balance in account_info['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    # Calcular valor en USD
                    if asset == 'USDC':
                        usd_value = total
                    else:
                        symbol = f"{asset}USDC"
                        try:
                            price = self.bot.account.get_current_price(symbol)
                            usd_value = total * price
                        except:
                            usd_value = 0
                    
                    if usd_value > 0.1:  # Filtrar activos insignificantes
                        assets.append({
                            'asset': asset,
                            'balance': total,
                            'usd_value': usd_value,
                            'percentage': (usd_value / total_balance * 100) if total_balance > 0 else 0
                        })
            
            # Ordenar por valor descendente
            assets.sort(key=lambda x: x['usd_value'], reverse=True)
            
            return {
                'total_balance': total_balance,
                'assets': assets
            }
            
        except Exception as e:
            print(f"Error getting portfolio: {e}")
            return {'total_balance': total_balance, 'assets': []}

    def _update_history(self, now, total_balance):
        """Historial más agresivo - 1 punto cada 5 minutos para datos antiguos"""
        if not self.history:
            self.history.append((now, total_balance))
            return
            
        last_time = self.history[-1][0]
        time_diff = (now - last_time).total_seconds()
        
        # Para datos recientes (< 1 día): 1 punto por minuto
        # Para datos antiguos (> 1 día): 1 punto cada 5 minutos
        one_day_ago = now - timedelta(days=1)
        min_interval = 300 if last_time < one_day_ago else 60
        
        if time_diff >= min_interval:
            self.history.append((now, total_balance))
            
            # Limitar más agresivamente
            if len(self.history) > 2000:  # Reducir de 5000 a 2000
                self.history = self.history[-2000:]
                
            # Guardar solo cada 20 puntos
            if len(self.history) % 20 == 0:
                self.save_history()

    def _update_main_chart(self, total_balance):
        """✅ GRÁFICO MEJORADO CON MEJORES LOGS"""
        try:
            tf = self.tf_var.get()
            print(f"   📈 Actualizando gráfico ({tf})...")
            
            if not self.history:
                print("   📊 Creando historial inicial para gráfico...")
                self.history = [(datetime.now(), total_balance)]
                self.save_history()
            
            # Filtrar datos según timeframe
            filtered = self._filter_data_by_timeframe(tf)
            
            if not filtered:
                print("   📊 Creando datos de ejemplo para gráfico...")
                filtered = [
                    (datetime.now() - timedelta(hours=2), total_balance * 0.98),
                    (datetime.now() - timedelta(hours=1), total_balance * 0.99),
                    (datetime.now(), total_balance)
                ]
            
            times, values = zip(*filtered)
            
            # LIMPIAR Y DIBUJAR GRÁFICO
            self.ax.clear()
            
            # Línea del gráfico
            self.ax.plot(times, values, color=ACCENT_COLOR, linewidth=2)
            
            # Configuración
            self.ax.set_facecolor(CARD_BG)
            self.ax.grid(True, alpha=0.2, color=TEXT_SECONDARY)
            self.ax.tick_params(colors=TEXT_SECONDARY)
            
            # Título
            self.ax.set_title(f"Balance History - {tf}", color=TEXT_COLOR, fontsize=12, pad=10)
            
            # Formatear ejes
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # Formatear eje X
            self._format_xaxis(tf, times)
            
            # Ajustar layout
            self.fig.tight_layout()
            
            self.canvas.draw()
            print(f"   ✅ Gráfico actualizado: {len(filtered)} puntos")
            
        except Exception as e:
            print(f"❌ Error actualizando gráfico: {e}")
            self._create_emergency_chart()

    def _create_emergency_chart(self):
        """✅ GRÁFICO DE EMERGENCIA CUANDO FALLA EL PRINCIPAL"""
        try:
            self.ax.clear()
            self.ax.text(0.5, 0.5, 'Cargando datos...', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=self.ax.transAxes, color=TEXT_COLOR, fontsize=14)
            self.ax.set_facecolor(CARD_BG)
            self.canvas.draw()
        except:
            pass

    def _format_xaxis(self, tf, times):
        """Formatea el eje X según el timeframe"""
        if not times:
            return
            
        # Rotar labels para mejor legibilidad
        plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Formato de fecha según timeframe
        if tf == "1h":
            # Para 1h: mostrar hora
            self.ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
        elif tf == "1D":
            # Para 1D: mostrar fecha completa
            self.ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m/%d'))
        elif tf == "1W":
            # Para 1W: mostrar mes/día
            self.ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m/%d'))

    def _filter_data_by_timeframe(self, tf):
        """Filtra datos según timeframe seleccionado"""
        if not self.history:
            return []
        
        now = datetime.now()
        
        if tf == "1h":
            cutoff = now - timedelta(hours=24)  # Últimas 24 horas
            max_points = 200
        elif tf == "1D":
            cutoff = now - timedelta(days=30)   # Últimos 30 días
            max_points = 500
        elif tf == "1W":
            cutoff = now - timedelta(days=365)  # Último año
            max_points = 300
        else:
            cutoff = now - timedelta(days=30)   # Por defecto 30 días
            max_points = 500
        
        # Filtrar datos
        filtered = [(t, v) for t, v in self.history if t >= cutoff]
        
        # Si hay muchos puntos, muestrear para mejor rendimiento
        if len(filtered) > max_points:
            step = max(1, len(filtered) // max_points)
            filtered = filtered[::step]
            print(f"📈 Muestreo aplicado: {len(filtered)} puntos (step: {step})")
        
        return filtered

    def _perform_restart(self):
        """Ejecuta el reinicio completo - CON DELAY DE ESTABILIZACIÓN"""
        import sys
        import os
        import time
        
        try:
            print("🔴 INICIANDO REINICIO COMPLETO...")
            
            # ✅ MARCAR COMO CERRANDO
            self.closing = True
            self.updating = False
            
            # ✅ DETENER BOT
            if hasattr(self, 'bot') and self.bot is not None:
                print("🛑 Deteniendo bot...")
                self.bot.force_stop = True
                self.bot.running = False
            
            # ✅ PEQUEÑO DELAY PARA ESTABILIZAR
            time.sleep(0.5)
            
            # ✅ GUARDAR HISTORIAL
            try:
                self.save_history()
                print("💾 Historial guardado")
            except:
                pass
            
            # ✅ CERRAR VENTANA
            try:
                self.root.quit()
                print("✅ Ventana cerrada")
            except:
                pass
            
            # ✅ PEQUEÑO DELAY ANTES DEL REINICIO
            time.sleep(0.5)
            
            # ✅ REINICIAR
            python = sys.executable
            script = sys.argv[0]
            print(f"🔄 Lanzando nuevo proceso: {python} {script}")
            
            subprocess.Popen([python, script])
            
            # ✅ SALIR
            os._exit(0)
            
        except Exception as e:
            print(f"❌ Error crítico en reinicio: {e}")
            os._exit(1)

    def _update_portfolio_ui(self, portfolio_data):
        """✅ CARTERA MEJORADA - COLORES ÚNICOS PARA CADA ASSET"""
        if self.closing:
            return
            
        try:
            # Limpiar treeview
            for item in self.portfolio_tree.get_children():
                self.portfolio_tree.delete(item)
            
            if not portfolio_data.get('assets'):
                self.portfolio_tree.insert('', 'end', values=(
                    "Cargando...", "---", "---", "---"
                ))
            else:
                total_balance = portfolio_data['total_balance']
                for asset in portfolio_data['assets']:
                    if asset['usd_value'] > 1:
                        self.portfolio_tree.insert('', 'end', values=(
                            asset['asset'],
                            f"{asset['balance']:.6f}",
                            f"${asset['usd_value']:,.2f}",
                            f"{asset['percentage']:.1f}%"
                        ))
            
            # ✅ ACTUALIZAR GRÁFICO DE TORTA CON COLORES ÚNICOS
            self.portfolio_ax.clear()
            
            assets = [a for a in portfolio_data.get('assets', []) if a['usd_value'] > total_balance * 0.01]
            if assets:
                labels = [a['asset'] for a in assets]
                sizes = [a['usd_value'] for a in assets]
                
                # ✅ PALETA DE COLORES MÁS GRANDE Y ÚNICA
                expanded_colors = [
                    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                    '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
                    '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2',
                    '#F9E79F', '#AED6F1', '#A3E4D7', '#FAD7A0', '#D2B4DE'
                ]
                
                # ✅ USAR COLORES ÚNICOS - tomar solo los necesarios
                colors = expanded_colors[:len(assets)]
                
                wedges, texts, autotexts = self.portfolio_ax.pie(
                    sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                    startangle=90, textprops={'color': 'white', 'fontsize': 8}
                )
                
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_weight('bold')
            else:
                self.portfolio_ax.text(0.5, 0.5, 'Cargando...', 
                                    horizontalalignment='center', verticalalignment='center',
                                    transform=self.portfolio_ax.transAxes, color=TEXT_COLOR, fontsize=10)
            
            self.portfolio_ax.set_facecolor(CARD_BG)
            self.portfolio_canvas.draw()
            print("✅ Gráfico de portfolio actualizado con colores únicos")
            
        except Exception as e:
            print(f"❌ Error actualizando portfolio UI: {e}")

    def _background_update(self):
        """Actualización en background con gestión inteligente de comisiones"""
        try:
            # Verificar si el bot está completamente conectado y ejecutándose
            if (not hasattr(self.bot, 'gui') or self.bot.gui is None or 
                not hasattr(self.bot, 'running') or not self.bot.running):
                print("⏳ Bot no listo, omitiendo actualización...")
                return
            
            # SOLO OBTENER DATOS EN EL HILO SECUNDARIO
            total_balance = self.bot.account.get_balance_usdc()
            
            # ✅ ACTUALIZAR HISTORIAL
            now = datetime.now()
            self._update_history(now, total_balance)
            
            # ✅ CALCULAR COMISIONES POR PERÍODO
            fees_data = self.calculate_fees_by_period()  # ← DEFINIR fees_data AQUÍ
            
            # ✅ CALCULAR TODAS LAS NUEVAS MÉTRICAS DE RENDIMIENTO
            performance_data = self.calculate_all_performance_metrics(total_balance)

            # ✅ CALCULAR CAMBIOS DIARIOS PARA TODOS LOS TOKENS A LA VEZ
            daily_changes = self.calculate_all_tokens_daily_change()
            
            # ✅ OBTENER DATOS DE TOKENS (existente)
            symbol_data = {}
            for symbol in self.token_frames.keys():
                try:
                    signals = self.bot.manager.get_signals(symbol)
                    weight = self.bot.manager.calculate_weight(signals)
                    price = self.bot.account.get_current_price(symbol)
                    balance = self.bot.account.get_symbol_balance(symbol)
                    usd_value = balance * price
                    pct = (usd_value / total_balance * 100) if total_balance > 0 else 0
                    daily_change = daily_changes.get(symbol, "+0.00%")
                    
                    symbol_data[symbol] = {
                        'signals': signals,
                        'weight': weight,
                        'price': price,
                        'balance': balance,
                        'usd': usd_value,
                        'pct': pct,
                        'daily_change': daily_change
                    }
                except Exception as e:
                    print(f"Error updating {symbol}: {e}")
                    continue

            # ✅ OBTENER DATOS DE CARTERA (existente)
            portfolio_data = self.get_portfolio_data(total_balance)
            
            # ✅ MÉTRICAS COMPLETAS CON NUEVOS CAMPOS
            metrics = {
                # Métricas principales
                'total_balance': total_balance,
                
                # Cambios temporales
                'change_30m': performance_data['change_30m'],
                'change_1h': performance_data['change_1h'],
                'change_2h': performance_data['change_2h'],
                'change_4h': performance_data['change_4h'],
                'change_1d': performance_data['change_1d'],
                'change_1w': performance_data['change_1w'],
                'change_1m': performance_data['change_1m'],
                'change_1y': performance_data['change_1y'],
                
                # Comisiones por período
                'fees_1d': f"${fees_data['1d']:.2f}",
                'fees_1w': f"${fees_data['1w']:.2f}",
                'fees_1m': f"${fees_data['1m']:.2f}",
                'fees_1y': f"${fees_data['1y']:.2f}",
                
                # Métricas existentes
                'active_trades': f"{sum(1 for s in symbol_data.values() if s['usd'] > 1)}/{len(symbol_data)}",
                'bot_status': "EJECUTANDO" if self.bot.running else "DETENIDO"
            }
            
            # ✅ Pasar datos al hilo principal para actualizar UI
            self.data_queue.put(("token_data", symbol_data))
            self.data_queue.put(("metrics", metrics))
            self.data_queue.put(("portfolio", portfolio_data))
            self.data_queue.put(("chart_update", total_balance))
            
        except Exception as e:
            print(f"Error in background update: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.updating = False