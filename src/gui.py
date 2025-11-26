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

        # ✅ INICIALIZAR CACHE DE COMISIONES
        self._cached_fees_period = self.get_empty_fees()
        self._last_fees_calc = datetime.now() - timedelta(hours=2)  # Forzar primera actualización
        
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
        """Limpieza RÁPIDA cada 5 minutos - máximo rendimiento"""
        if self.closing:
            return
            
        # SOLO LOG EN DEBUG para no saturar
        import random
        if random.randint(1, 10) == 1:  # Solo 10% de los cleanups
            print("⚡ Limpieza rápida (5min) - manteniendo fluidez...")
        
        # 1. GARBAGE COLLECTION (instantáneo)
        import gc
        gc.collect()
        
        # 2. LIMPIEZA PREVENTIVA DE QUEUE
        if self.data_queue.qsize() > 40:
            try:
                # Dejar solo los 20 más recientes
                while self.data_queue.qsize() > 20:
                    self.data_queue.get_nowait()
            except queue.Empty:
                pass
        
        # 3. LIMPIEZA SUAVE DE LOGS
        current_lines = int(self.log_text.index('end-1c').split('.')[0])
        if current_lines > 150:  # Más agresivo para fluidez
            self.log_text.delete(1.0, "30.0")  # Solo 30 líneas
        
        # 4. PROGRAMAR SIGUIENTE - SIEMPRE 5 MINUTOS
        if not self.closing:
            self.root.after(300000, self.cleanup_memory)

    def process_data_queue(self):
        """Procesar cola con actualizaciones SEGURAS"""
        try:
            processed_count = 0
            MAX_PROCESS_PER_CYCLE = 20
            
            while processed_count < MAX_PROCESS_PER_CYCLE:
                item = self.data_queue.get_nowait()
                processed_count += 1
                
                if item[0] == "log":
                    self.safe_ui_update(self._add_log_message, item[1], item[2])
                elif item[0] == "token_data":
                    self.safe_ui_update(self._update_token_ui, item[1])
                elif item[0] == "metrics":
                    self.safe_ui_update(self._update_metrics_ui, item[1])
                elif item[0] == "portfolio":
                    self.safe_ui_update(self._update_portfolio_ui, item[1])
                elif item[0] == "chart_update":
                    self.safe_ui_update(self._update_main_chart, item[1])
                        
        except queue.Empty:
            pass
        finally:
            # LIMPIAR COLA SI SE ESTÁ LLENANDO DEMASIADO
            if self.data_queue.qsize() > 100:
                print("⚠️ Limpiando queue sobrecargada...")
                try:
                    while self.data_queue.qsize() > 50:
                        self.data_queue.get_nowait()
                except queue.Empty:
                    pass
            
            # Programar siguiente actualización
            if (hasattr(self, 'bot') and self.bot is not None and 
                hasattr(self.bot, 'running') and self.bot.running and
                not self.updating):
                self.root.after(20000, self.safe_update_ui)
            else:
                self.root.after(2000, self.process_data_queue)

    def _update_token_ui(self, symbol_data):
        """Actualiza la UI de tokens de forma SEGURA"""
        # Esta función ahora siempre se ejecuta en el hilo principal
        if self.closing or not hasattr(self, 'token_frames'):
            return
            
        for symbol, data in symbol_data.items():
            if symbol in self.token_frames and not self.closing:
                frame_data = self.token_frames[symbol].data
                try:
                    # Actualizar precio
                    frame_data["price_label"].config(text=f"${data['price']:,.4f}")
                    
                    # ✅ ACTUALIZAR %24H AL LADO DEL SÍMBOLO (con colores)
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
                    
                    # Determinar color del %24H
                    if daily_change_value > 0:
                        change_color = ACCENT_COLOR  # Verde
                    elif daily_change_value < 0:
                        change_color = DANGER_COLOR  # Rojo
                    else:
                        change_color = TEXT_SECONDARY  # Gris
                    
                    # ✅ ACTUALIZAR %24H JUNTO AL SÍMBOLO
                    frame_data["daily_change_header_label"].config(
                        text=f" {daily_change_str}",  # Espacio antes para separar del símbolo
                        fg=change_color
                    )
                    
                    # Actualizar balance
                    frame_data["balance_label"].config(
                        text=f"{data['balance']:.6f} → ${data['usd']:,.2f} ({data['pct']:.1f}%)"
                    )
                    
                    # Círculos con señales OO + valores con % cambio
                    for tf, circle_data in frame_data["circles"].items():
                        # Color del círculo: señal OO
                        color = "gray"
                        if tf in data['signals']:
                            signal = data['signals'][tf]
                            color = "#00ff00" if signal == "GREEN" else "#ffff00" if signal == "YELLOW" else "#ff4444"
                        
                        circle_data['canvas'].itemconfig(circle_data['circle_id'], fill=color)
                        
                        # Valor: % cambio de precio
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
                    
                    # Actualizar peso y señal general (basado en señales OO)
                    weight = data['weight']
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
                        font=("Arial", 9)
                    )
                    
                except Exception as e:
                    if "main thread is not in main loop" not in str(e):
                        print(f"Error updating {symbol} UI: {e}")

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
        
        # ✅ INICIAR ACTUALIZACIONES DESPUÉS DE QUE EL LOOP PRINCIPAL ESTÉ EJECUTÁNDOSE
        self.root.after(1000, self.safe_start_updates)  # Esperar 1 segundo
        print("✅ Controles habilitados - actualizaciones programadas")

    def safe_start_updates(self):
        """Iniciar actualizaciones de forma segura después de que el loop esté activo"""
        print("🔄 Iniciando actualizaciones automáticas...")
        # ✅ INICIAR LA PRIMERA ACTUALIZACIÓN
        self.safe_update_ui()

    def verify_initial_connection(self):
        """Verifica el estado inicial de la conexión"""
        if self.bot:
            bot_has_gui = hasattr(self.bot, 'gui') and self.bot.gui is not None
            manager_has_gui = hasattr(self.bot, 'manager') and hasattr(self.bot.manager, 'gui') and self.bot.manager.gui is not None
            account_has_gui = hasattr(self.bot, 'account') and hasattr(self.bot.account, 'gui') and self.bot.account.gui is not None
            
            print(f"🔍 Conexiones iniciales - Bot: {bot_has_gui}, Manager: {manager_has_gui}, Account: {account_has_gui}")
            
            if bot_has_gui and manager_has_gui and account_has_gui:
                print("✅ GUI completamente conectada a todos los componentes")
                self.log_trade("✅ GUI completamente conectada al bot", 'GREEN')
            else:
                missing_components = []
                if not bot_has_gui: missing_components.append("Bot")
                if not manager_has_gui: missing_components.append("Manager")
                if not account_has_gui: missing_components.append("Account")
                
                print(f"⚠️ Conexiones incompletas: {', '.join(missing_components)}")
                self.log_trade(f"⚠️ Conexiones incompletas: {', '.join(missing_components)}", 'YELLOW')
        else:
            print("❌ No hay bot conectado a la GUI")
            self.log_trade("❌ No hay bot conectado - use 'Reiniciar App'", 'RED')

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
        
        self.create_button(control_frame, "🔄 RESTART", SECONDARY_COLOR, self.safe_restart_app).pack(side=tk.LEFT, padx=5)  # ← NUEVO BOTÓN
        
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

        tk.Label(chart_frame, text="📈 BALANCE GRAPH", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(anchor="w")
        
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

        tk.Label(tokens_frame, text="🎯 TRADING SIGNALS", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(anchor="w")

        # Contenedor para tokens en grid (3 columnas)
        self.tokens_container = tk.Frame(tokens_frame, bg=DARK_BG)
        self.tokens_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.token_frames = {}
        self.create_token_cards_grid()

        # Panel de cartera
        portfolio_frame = tk.Frame(bottom_row, bg=DARK_BG, width=400)
        portfolio_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(20, 0))
        portfolio_frame.pack_propagate(False)

        tk.Label(portfolio_frame, text="💼 BINANCE WALLET", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(anchor="w")

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
        """Calcula cambios diarios para todos los tokens de una vez (más eficiente)"""
        try:
            # Obtener todos los tickers de una sola llamada a la API
            all_tickers = self.bot.client.get_ticker()
            
            daily_changes = {}
            for ticker in all_tickers:
                symbol = ticker['symbol']
                if symbol in self.token_frames:
                    if 'priceChangePercent' in ticker:
                        price_change_percent = float(ticker['priceChangePercent'])
                        sign = "+" if price_change_percent >= 0 else ""
                        daily_changes[symbol] = f"{sign}{price_change_percent:.2f}%"
                    else:
                        daily_changes[symbol] = "+0.00%"
            
            # Asegurar que todos los símbolos tengan un valor
            for symbol in self.token_frames.keys():
                if symbol not in daily_changes:
                    daily_changes[symbol] = "+0.00%"
            
            return daily_changes
            
        except Exception as e:
            print(f"Error calculando cambios diarios: {e}")
            # Devolver valores por defecto para todos los símbolos
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
        """Ejecuta una función de UI de forma segura en el hilo principal"""
        if self.closing or not hasattr(self, 'root') or not self.root:
            return
            
        def safe_wrapper():
            if not self.closing and hasattr(self, 'root') and self.root:
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    if "main thread is not in main loop" not in str(e):
                        print(f"UI update error: {e}")
        
        try:
            self.root.after(0, safe_wrapper)
        except Exception as e:
            if "main thread is not in main loop" not in str(e):
                print(f"Error scheduling UI update: {e}")

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
        self.root.after(300000, self.cleanup_memory)  # Cada 5 minutos

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

    def safe_update_ui(self):
        """Inicia actualización en hilo separado de forma segura - EVITA DUPLICADOS"""
        if self.closing:
            return
            
        if (not self.updating and self.bot is not None and 
            hasattr(self.bot, 'running') and self.bot.running):
            self.updating = True
            threading.Thread(target=self._background_update, daemon=True).start()
        
        # ✅ SOLO PROGRAMAR SIGUIENTE SI NO ESTAMOS CERRANDO
        if not self.closing and self.bot is not None and self.bot.running:
            self.root.after(20000, self.safe_update_ui)  # 20 segundos

    def calculate_all_performance_metrics(self, total_balance):
        """Calcula todas las métricas de rendimiento"""
        return {
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
        """Historial SIMPLIFICADO - solo 1 punto por minuto"""
        # Solo agregar si ha pasado al menos 1 minuto desde el último punto
        if self.history:
            last_time = self.history[-1][0]
            time_diff = (now - last_time).total_seconds()
            if time_diff < 60:  # Menos de 1 minuto
                return
        
        self.history.append((now, total_balance))
        
        # LIMITAR A 5000 PUNTOS MÁXIMO
        if len(self.history) > 5000:
            self.history = self.history[-5000:]
            print("📊 Historial recortado a 5000 puntos")
        
        # Guardar solo cada 10 puntos para reducir I/O
        if len(self.history) % 10 == 0:
            self.save_history()
            print(f"💾 Historial guardado: {len(self.history)} puntos")

    def _update_main_chart(self, total_balance):
        """Gráfico SIMPLIFICADO - sin suavizado, solo línea directa"""
        try:
            tf = self.tf_var.get()
            
            # Filtrar datos según timeframe
            filtered = self._filter_data_by_timeframe(tf)
            
            if not filtered:
                # Si no hay datos filtrados, usar punto actual
                filtered = [(datetime.now(), total_balance)]
                # Y agregar al historial si es nuevo
                if not self.history or (datetime.now() - self.history[-1][0]).total_seconds() >= 60:
                    self.history.append((datetime.now(), total_balance))

            times, values = zip(*filtered)
            
            # LIMPIAR Y DIBUJAR GRÁFICO SIMPLE
            self.ax.clear()
            
            # Línea directa SIN suavizado
            self.ax.plot(times, values, color=ACCENT_COLOR, linewidth=2)
            
            # Configuración básica
            self.ax.set_facecolor(CARD_BG)
            self.ax.grid(True, alpha=0.2, color=TEXT_SECONDARY)
            self.ax.tick_params(colors=TEXT_SECONDARY)
            
            # Título dinámico
            self.ax.set_title(f"Balance History - {tf}", color=TEXT_COLOR, fontsize=12, pad=10)
            
            # Formatear ejes
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            # Formatear eje X según timeframe
            self._format_xaxis(tf, times)
            
            # Ajustar layout
            self.fig.tight_layout()
            
            self.canvas.draw()

        except Exception as e:
            print(f"Error updating main chart: {e}")

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

    def on_close(self):
        """Maneja el cierre de la aplicación - SALIDA INMEDIATA"""
        if self.closing:
            return
        
        self.closing = True
        print("🔴 CERRANDO APLICACIÓN...")
        
        # ✅ DETENER TODO INMEDIATAMENTE
        self.updating = False
        
        if hasattr(self, 'bot') and self.bot is not None:
            self.bot.force_stop = True
            self.bot.running = False
        
        # ✅ GUARDAR RÁPIDAMENTE
        try:
            self.save_history()
        except:
            pass
        
        # ✅ CERRAR VENTANA
        try:
            self.root.quit()
        except:
            pass
        
        # ✅ SALIR
        import os
        os._exit(0)

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
        """Actualiza la visualización de la cartera"""
        if self.closing:
           return
        # Limpiar treeview
        for item in self.portfolio_tree.get_children():
            self.portfolio_tree.delete(item)
        
        # Agregar datos
        total_balance = portfolio_data['total_balance']
        for asset in portfolio_data['assets']:
            if asset['usd_value'] > 1:  # Mostrar solo activos con valor significativo
                self.portfolio_tree.insert('', 'end', values=(
                    asset['asset'],
                    f"{asset['balance']:.6f}",
                    f"${asset['usd_value']:,.2f}",
                    f"{asset['percentage']:.1f}%"
                ))
        
        # Actualizar gráfico de torta - CORREGIDO con colores más saturados y texto blanco
        self.portfolio_ax.clear()
        
        assets = [a for a in portfolio_data['assets'] if a['usd_value'] > total_balance * 0.01]  # > 1% del total
        if assets:
            labels = [a['asset'] for a in assets]
            sizes = [a['usd_value'] for a in assets]
            
            # Colores más saturados y oscuros - paleta mejorada
            saturated_colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
                '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
            ]
            
            # Asegurar que tenemos suficientes colores
            colors = saturated_colors * (len(assets) // len(saturated_colors) + 1)
            colors = colors[:len(assets)]
            
            # Gráfico de torta con texto en BLANCO y colores saturados
            wedges, texts, autotexts = self.portfolio_ax.pie(
                sizes, 
                labels=labels, 
                colors=colors, 
                autopct='%1.1f%%',
                startangle=90, 
                textprops={'color': 'white', 'fontsize': 8, 'weight': 'bold'},
                wedgeprops={'edgecolor': 'white', 'linewidth': 0.5}
            )
            
            # Configurar el color de los textos de porcentaje a BLANCO
            for autotext in autotexts:
                autotext.set_color('black')
                autotext.set_weight('bold')
            
            # Configurar el color de las etiquetas a BLANCO
            for text in texts:
                text.set_color('white')
                text.set_weight('bold')
        
        self.portfolio_canvas.draw()

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