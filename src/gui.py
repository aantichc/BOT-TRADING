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
        
        # ✅ NO HAY self.root.mainloop() AL FINAL

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

    def create_widgets(self):        
        """Crea todos los widgets de la interfaz"""
        # Header
        header = tk.Frame(self.root, bg=DARK_BG, height=80)
        header.pack(fill=tk.X, padx=20, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="🚀 CRYPTO TRADING BOT", 
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
        
        self.create_button(control_frame, "🔄 REINICIAR", SECONDARY_COLOR, self.safe_restart_app).pack(side=tk.LEFT, padx=5)  # ← NUEVO BOTÓN
        
        # En create_widgets(), después de crear los botones:
        if self.bot is None:
            self.start_btn.config(state='disabled', bg='gray')
            self.stop_btn.config(state='disabled', bg='gray') 
            self.rebalance_btn.config(state='disabled', bg='gray')
        
        # Selector de timeframe - CORREGIDO con estilo oscuro
        tk.Label(control_frame, text="TIMEFRAME:", bg=DARK_BG, fg=TEXT_SECONDARY, 
                font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(20,5))
        self.tf_var = tk.StringVar(value="1h")
        tf_combo = ttk.Combobox(control_frame, textvariable=self.tf_var, 
                            values=["15m", "30m", "1h", "2h", "4h", "1D"], 
                            width=8, state="readonly", font=("Arial", 10),
                            style='Dark.TCombobox')  # Aplicar estilo oscuro

        tf_combo.pack(side=tk.LEFT)

        # Contenedor principal
        main_container = tk.Frame(self.root, bg=DARK_BG)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Fila superior: Métricas y Gráfico
        top_row = tk.Frame(main_container, bg=DARK_BG)
        top_row.pack(fill=tk.X, pady=(0, 20))

        # Métricas principales
        metrics_frame = tk.Frame(top_row, bg=DARK_BG)
        metrics_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.total_balance_label = self.create_metric_card(
            metrics_frame, "💰 BALANCE TOTAL", "$0.00", ACCENT_COLOR
        )
        self.daily_change_label = self.create_metric_card(
            metrics_frame, "📊 CAMBIO 24H", "+0.00%", TEXT_SECONDARY
        )
        self.active_trades_label = self.create_metric_card(
            metrics_frame, "🔢 ACTIVOS ACTIVOS", "0/0", TEXT_SECONDARY
        )
        self.bot_status_label = self.create_metric_card(
            metrics_frame, "🤖 ESTADO BOT", "DETENIDO", DANGER_COLOR
        )

        # Gráfico principal
        chart_frame = tk.Frame(top_row, bg=DARK_BG)
        chart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(20, 0))

        tk.Label(chart_frame, text="📈 EVOLUCIÓN DE CAPITAL", bg=DARK_BG, fg=TEXT_COLOR,
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

        tk.Label(tokens_frame, text="🎯 SEÑALES DE TRADING", bg=DARK_BG, fg=TEXT_COLOR,
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

        tk.Label(portfolio_frame, text="💼 CARTERA BINANCE", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(anchor="w")

        # Gráfico de cartera
        self.portfolio_fig = Figure(figsize=(4, 3), facecolor=DARK_BG)
        self.portfolio_ax = self.portfolio_fig.add_subplot(111)
        self.portfolio_ax.set_facecolor(CARD_BG)
        self.portfolio_canvas = FigureCanvasTkAgg(self.portfolio_fig, portfolio_frame)
        self.portfolio_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        # Lista de activos
        self.portfolio_tree = ttk.Treeview(portfolio_frame, columns=('Asset', 'Balance', 'USD', '%'), 
                                          show='headings', height=8)
        self.portfolio_tree.heading('Asset', text='ACTIVO')
        self.portfolio_tree.heading('Balance', text='BALANCE')
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

        tk.Label(log_frame, text="📋 LOGS DE TRADING", bg=DARK_BG, fg=TEXT_COLOR,
                font=("Arial", 12, "bold")).pack(anchor="w")

        self.log_text = tk.Text(log_frame, height=15, bg=CARD_BG, fg=TEXT_COLOR, 
                               font=("Consolas", 9), wrap=tk.WORD)
        self.setup_log_tags()
        scrollbar_log = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.config(yscrollcommand=scrollbar_log.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(5, 0))
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)

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
        """Crea una tarjeta individual de token con mejor distribución"""
        card = tk.Frame(self.tokens_container, bg=CARD_BG, relief='flat', bd=1,
                    highlightbackground=TEXT_SECONDARY, highlightthickness=1,
                    width=280, height=190)
        card.pack_propagate(False)
        
        # Header del token
        header = tk.Frame(card, bg=CARD_BG)
        header.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Label(header, text=symbol.replace("USDC", ""), bg=CARD_BG, fg=ACCENT_COLOR,
                font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        price_label = tk.Label(header, text="$0.0000", bg=CARD_BG, fg=TEXT_COLOR,
                            font=("Arial", 12, "bold"))
        price_label.pack(side=tk.RIGHT)
        
        # Información de balance
        balance_frame = tk.Frame(card, bg=CARD_BG)
        balance_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        balance_label = tk.Label(balance_frame, text="0.000000 → $0.00 (0.0%)", 
                            bg=CARD_BG, fg=TEXT_SECONDARY, font=("Arial", 9))
        balance_label.pack(anchor="w")
        
        # CONTENEDOR PARA SEMÁFOROS
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
            tf_frame.pack(side=tk.LEFT, padx=12)
            
            # Canvas para el círculo
            canvas = tk.Canvas(tf_frame, width=30, height=30, bg=CARD_BG, highlightthickness=0)
            canvas.pack()
            
            # Círculo centrado
            circle_id = canvas.create_oval(5, 5, 25, 25, fill="gray", outline=TEXT_SECONDARY, width=2)
            
            # Guardar tanto el canvas como el circle_id
            circles[tf] = {
                'canvas': canvas,
                'circle_id': circle_id
            }
            
            # Texto del timeframe DEBAJO del círculo
            tk.Label(tf_frame, text=tf, bg=CARD_BG, fg=TEXT_SECONDARY, 
                    font=("Arial", 8, "bold")).pack()
        
        # Peso y señal general
        signal_frame = tk.Frame(card, bg=CARD_BG)
        signal_frame.pack(fill=tk.X, padx=10, pady=(8, 8))
        
        # Contenedor para centrar
        center_frame = tk.Frame(signal_frame, bg=CARD_BG)
        center_frame.pack(expand=True)
        
        weight_label = tk.Label(center_frame, text="PESO: 0.00", bg=CARD_BG, fg=WARNING_COLOR,
                            font=("Arial", 11, "bold"))
        weight_label.pack(side=tk.LEFT, padx=(0, 10))
        
        signal_label = tk.Label(center_frame, text="SEÑAL: N/A", bg=CARD_BG, fg=TEXT_SECONDARY,
                            font=("Arial", 10, "bold"))
        signal_label.pack(side=tk.LEFT)
        
        # Guardar referencias
        card.data = {
            "symbol": symbol,
            "price_label": price_label,
            "balance_label": balance_label,
            "circles": circles,  # Ahora es un diccionario con canvas y circle_id
            "weight_label": weight_label,
            "signal_label": signal_label
        }
        
        return card

    def load_history(self):
        """Carga el historial desde archivo - optimizado para muchos datos"""
        history_file = "capital_history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    data = json.load(f)
                
                loaded_history = [(datetime.fromisoformat(d[0]), d[1]) for d in data]
                print(f"📈 Historial cargado: {len(loaded_history)} puntos")
                
                # ✅ SI HAY MÁS DE 5000 PUNTOS, CONSERVAR SOLO LOS MÁS RECIENTES
                if len(loaded_history) > 5000:
                    loaded_history = loaded_history[-5000:]
                    print(f"📊 Historial recortado a {len(loaded_history)} puntos más recientes")
                
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
        
    def compress_old_data(self):
        """Comprime datos antiguos para ahorrar espacio manteniendo tendencias"""
        if len(self.history) < 1000:  # Solo comprimir si hay muchos datos
            print("📊 No hay suficientes datos para comprimir")
            return
        
        print(f"🔍 Comprimiendo {len(self.history)} puntos de historial...")
        
        # Separar datos recientes (últimas 24 horas) y antiguos
        cutoff_time = datetime.now() - timedelta(hours=24)
        recent_data = [point for point in self.history if point[0] >= cutoff_time]
        old_data = [point for point in self.history if point[0] < cutoff_time]
        
        if len(old_data) <= 500:
            print("📊 No hay suficientes datos antiguos para comprimir")
            return
        
        print(f"📊 Comprimiendo {len(old_data)} puntos antiguos...")
        
        # Comprimir datos antiguos: conservar 1 punto por hora
        compressed_old = []
        current_hour = None
        hour_points = []
        
        # Ordenar por tiempo (por si acaso)
        old_data.sort(key=lambda x: x[0])
        
        for time_point, value in old_data:
            hour_key = time_point.replace(minute=0, second=0, microsecond=0)
            if hour_key != current_hour:
                if hour_points:  # Guardar el punto medio de la hora anterior
                    # Usar el punto del medio de la hora para mejor representación
                    mid_index = len(hour_points) // 2
                    compressed_old.append(hour_points[mid_index])
                
                current_hour = hour_key
                hour_points = []
            
            hour_points.append((time_point, value))
        
        # Agregar la última hora
        if hour_points:
            mid_index = len(hour_points) // 2
            compressed_old.append(hour_points[mid_index])
        
        # Combinar datos comprimidos con recientes
        self.history = compressed_old + recent_data
        self.history.sort(key=lambda x: x[0])  # Re-ordenar por tiempo
        
        print(f"✅ Compresión completada: {len(compressed_old)} puntos antiguos + {len(recent_data)} recientes = {len(self.history)} total")
        
        # Guardar después de comprimir
        self.save_history()

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

    # Métodos de actualización y comunicación (similares a los anteriores)
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

    def process_data_queue(self):
        """Procesa la cola de datos de forma thread-safe EN EL HILO PRINCIPAL"""
        try:
            while True:
                item = self.data_queue.get_nowait()
                if item[0] == "log":
                    self._add_log_message(item[1], item[2])
                elif item[0] == "token_data":
                    self._update_token_ui(item[1])
                elif item[0] == "metrics":
                    self._update_metrics_ui(item[1])
                elif item[0] == "portfolio":
                    self._update_portfolio_ui(item[1])
                elif item[0] == "chart_update":
                    # ✅ ACTUALIZAR EL GRÁFICO CON EL NUEVO BALANCE
                    self._update_main_chart(item[1])
        except queue.Empty:
            pass
        finally:
            # ✅ PROGRAMAR SIGUIENTE ACTUALIZACIÓN SI EL BOT ESTÁ EJECUTÁNDOSE
            if (hasattr(self, 'bot') and self.bot is not None and 
                hasattr(self.bot, 'running') and self.bot.running and
                not self.updating):
                self.root.after(5000, self.safe_update_ui)  # 5 segundos
            else:
                self.root.after(1000, self.process_data_queue)  # Revisar cada segundo

    def _add_log_message(self, msg, color="white"):
        """Agrega mensaje al log con colores específicos"""
        ts = datetime.now().strftime("%H:%M:%S")
        
        # Mapear colores a tags específicos
        color_tags = {
            'GREEN': 'green_log',
            'RED': 'red_log', 
            'BLUE': 'blue_log',
            'YELLOW': 'yellow_log'
        }
        
        tag = color_tags.get(color, 'white_log')
        
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n", tag)
        self.log_text.see(tk.END)
        
        # Limitar el tamaño del log para evitar crecimiento excesivo
        if int(self.log_text.index('end-1c').split('.')[0]) > 500:  # 500 líneas máximo
            self.log_text.delete(1.0, "50.0")  # Borrar las primeras 50 líneas

    def setup_log_tags(self):
        """Configura los tags de color para el log"""
        self.log_text.tag_config('green_log', foreground="#00ff88")   # Compras/éxito
        self.log_text.tag_config('red_log', foreground="#ff4444")     # Ventas/errores
        self.log_text.tag_config('blue_log', foreground="#0088ff")    # Cambios de señal ← NUEVO
        self.log_text.tag_config('yellow_log', foreground="#ffaa00")  # Advertencias
        self.log_text.tag_config('white_log', foreground="#ffffff")   # Normal


    def _update_token_ui(self, symbol_data):
        """Actualiza la UI de tokens con la nueva estructura"""
        for symbol, data in symbol_data.items():
            if symbol in self.token_frames:
                frame_data = self.token_frames[symbol].data
                try:
                    # Actualizar precio
                    frame_data["price_label"].config(text=f"${data['price']:,.4f}")
                    
                    # Actualizar balance
                    frame_data["balance_label"].config(
                        text=f"{data['balance']:.6f} → ${data['usd']:,.2f} ({data['pct']:.1f}%)"
                    )
                    
                    # Actualizar círculos de timeframes
                    for tf, circle_data in frame_data["circles"].items():
                        color = "gray"  # Por defecto
                        if tf in data['signals']:
                            signal = data['signals'][tf]
                            color = "#00ff00" if signal == "GREEN" else "#ffff00" if signal == "YELLOW" else "#ff4444"
                        
                        # Actualizar el color del círculo usando el canvas y circle_id
                        circle_data['canvas'].itemconfig(circle_data['circle_id'], fill=color)
                    
                    # Actualizar peso y señal general
                    weight = data['weight']
                    if weight >= 0.8:
                        weight_color = "#00ff00"
                        signal_text = "FUERTE COMPRA"
                    elif weight >= 0.5:
                        weight_color = "#ffff00"
                        signal_text = "COMPRA"
                    elif weight >= 0.3:
                        weight_color = WARNING_COLOR
                        signal_text = "NEUTRAL"
                    else:
                        weight_color = DANGER_COLOR
                        signal_text = "VENTA"
                    
                    frame_data["weight_label"].config(
                        text=f"PESO: {weight:.2f}", 
                        fg=weight_color
                    )
                    frame_data["signal_label"].config(
                        text=f"SEÑAL: {signal_text}",
                        font=("Arial", 9)
                    )
                    
                except Exception as e:
                    print(f"Error updating {symbol} UI: {e}")

    def _update_metrics_ui(self, metrics):
        """Actualiza las métricas principales"""
        self.total_balance_label.config(text=f"${metrics['total_balance']:,.2f}")
        self.daily_change_label.config(text=metrics['daily_change'])
        self.active_trades_label.config(text=metrics['active_trades'])
        self.bot_status_label.config(
            text=metrics['bot_status'], 
            fg=ACCENT_COLOR if metrics['bot_status'] == "EJECUTANDO" else DANGER_COLOR
        )

    def _update_portfolio_ui(self, portfolio_data):
        """Actualiza la visualización de la cartera"""
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
            
            self.portfolio_ax.set_title('Distribución de Cartera', color='white', fontsize=12, weight='bold')
        
        self.portfolio_canvas.draw()

    def safe_update_ui(self):
        """Inicia actualización en hilo separado de forma segura"""
        if (not self.updating and self.bot is not None and 
            hasattr(self.bot, 'running') and self.bot.running):
            self.updating = True
            threading.Thread(target=self._background_update, daemon=True).start()

    def _background_update(self):
        """Actualización en background - solo obtener datos, UI en hilo principal"""
        try:
            # Verificar si el bot está completamente conectado y ejecutándose
            if (not hasattr(self.bot, 'gui') or self.bot.gui is None or 
                not hasattr(self.bot, 'running') or not self.bot.running):
                print("⏳ Bot no listo, omitiendo actualización...")
                return
            
            # SOLO OBTENER DATOS EN EL HILO SECUNDARIO
            total_balance = self.bot.account.get_balance_usdc()
            
            # ✅ ACTUALIZAR HISTORIAL - ESTO ES LO QUE FALTABA
            now = datetime.now()
            self._update_history(now, total_balance)
            
            symbol_data = {}
            for symbol in self.token_frames.keys():
                try:
                    signals = self.bot.manager.get_signals(symbol)
                    weight = self.bot.manager.calculate_weight(signals)
                    price = self.bot.account.get_current_price(symbol)
                    balance = self.bot.account.get_symbol_balance(symbol)
                    usd_value = balance * price
                    pct = (usd_value / total_balance * 100) if total_balance > 0 else 0

                    symbol_data[symbol] = {
                        'signals': signals,
                        'weight': weight,
                        'price': price,
                        'balance': balance,
                        'usd': usd_value,
                        'pct': pct
                    }
                except Exception as e:
                    print(f"Error updating {symbol}: {e}")
                    continue

            portfolio_data = self.get_portfolio_data(total_balance)
            
            metrics = {
                'total_balance': total_balance,
                'daily_change': self.calculate_daily_change(),
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
        finally:
            self.updating = False  # ✅ IMPORTANTE: Marcar como no actualizando

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

    def calculate_daily_change(self):
        """Calcula el cambio porcentual diario"""
        if len(self.history) < 2:
            return "+0.00%"
        
        # Encontrar el primer registro de hoy
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_data = [val for dt, val in self.history if dt >= today_start]
        
        if len(today_data) < 2:
            return "+0.00%"
        
        start_value = today_data[0]
        current_value = today_data[-1]
        change = ((current_value - start_value) / start_value) * 100
        
        color = ACCENT_COLOR if change >= 0 else DANGER_COLOR
        sign = "+" if change >= 0 else ""
        return f"{sign}{change:.2f}%"

    def _update_history(self, now, total_balance):
        """Actualiza el historial - GUARDA SIEMPRE y límite mayor"""
        # Evitar puntos duplicados en el mismo minuto
        if self.history:
            last_time = self.history[-1][0]
            time_diff = (now - last_time).total_seconds()
            
            # Solo agregar si han pasado al menos 30 segundos
            if time_diff < 30:
                return
        
        self.history.append((now, total_balance))
        
        # ✅ COMPRIMIR SI TENEMOS MÁS DE 2000 PUNTOS
        if len(self.history) > 2000:
            self.compress_old_data()
        
        # ✅ LIMITAR A 5000 PUNTOS (por si la compresión no fue suficiente)
        if len(self.history) > 5000:
            self.history = self.history[-5000:]
        
        # ✅ GUARDAR SIEMPRE CADA ACTUALIZACIÓN
        self.save_history()

    def _update_main_chart(self, total_balance):
        """Actualiza el gráfico principal optimizado para muchos datos"""
        try:
            tf = self.tf_var.get()
            cutoff = datetime.now() - self.get_timedelta_from_tf(tf)
            
            # Filtrar datos según el timeframe seleccionado
            filtered = [(t, v) for t, v in self.history if t >= cutoff]
            
            # Si hay pocos datos filtrados, mostrar más historial
            if len(filtered) < 10 and self.history:
                # Mostrar últimos 100 puntos como mínimo
                filtered = self.history[-100:]
            
            if not filtered:
                filtered = [(datetime.now(), total_balance)]

            times, values = zip(*filtered)
            self.ax.clear()
            
            # ✅ OPTIMIZAR: Solo suavizar si hay suficientes puntos
            if len(times) > 10:
                try:
                    x_num = np.array([t.timestamp() for t in times])
                    x_smooth = np.linspace(x_num.min(), x_num.max(), min(300, len(times)))
                    spl = make_interp_spline(x_num, values, k=3)
                    y_smooth = spl(x_smooth)
                    smooth_times = [datetime.fromtimestamp(ts) for ts in x_smooth]
                    self.ax.plot(smooth_times, y_smooth, color=ACCENT_COLOR, linewidth=3)
                except:
                    # Fallback a línea normal si falla el suavizado
                    self.ax.plot(times, values, color=ACCENT_COLOR, linewidth=3)
            else:
                self.ax.plot(times, values, color=ACCENT_COLOR, linewidth=3)

            self.ax.set_title(f"Evolución del Capital - ${total_balance:,.2f}", 
                            color=TEXT_COLOR, fontsize=14, pad=20)
            self.ax.set_facecolor(CARD_BG)
            self.ax.grid(True, alpha=0.3, color=TEXT_SECONDARY)
            self.ax.tick_params(colors=TEXT_SECONDARY)
            
            # Formatear ejes
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
            
            self.canvas.draw()

        except Exception as e:
            print(f"Error updating main chart: {e}")

    def get_timedelta_from_tf(self, tf):
        """Convierte timeframe a timedelta"""
        if tf == "15m": return timedelta(minutes=15)
        elif tf == "30m": return timedelta(minutes=30)
        elif tf == "1h": return timedelta(hours=1)
        elif tf == "2h": return timedelta(hours=2)
        elif tf == "4h": return timedelta(hours=4)
        elif tf == "1D": return timedelta(days=1)
        else: return timedelta(hours=1)

    def on_close(self):
        """Maneja el cierre de la aplicación"""
        if self.closing:
            return
        
        self.closing = True
        print("Cerrando aplicación...")
        
        if self.update_job:
            self.root.after_cancel(self.update_job)
        
        if hasattr(self.bot, 'stop_completely'):
            self.bot.stop_completely()
        
        self.save_history()
        self.root.destroy()
        
        print("Aplicación cerrada correctamente")
        import os
        os._exit(0)

    def _perform_restart(self):
        """Ejecuta el reinicio completo"""
        import sys
        import os
        import subprocess
        
        try:
            # Guardar historial antes de cerrar
            self.save_history()
            
            # Obtener la ruta del script actual
            python = sys.executable
            script = sys.argv[0]
            
            self.log_trade("✅ Cerrando aplicación para reinicio...", 'GREEN')
            
            # Reiniciar el proceso
            subprocess.Popen([python, script])
            
            # Cerrar la ventana actual
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            error_msg = f"❌ Error al reiniciar: {str(e)}"
            self.log_trade(error_msg, 'RED')
            print(error_msg)