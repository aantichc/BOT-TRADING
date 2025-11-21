import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import threading
import time
import json
import os
from datetime import datetime, timedelta

from binance_account import BinanceAccount
from config import *

class TradingBotGUI:
    def __init__(self, root, bot_instance):
        self.root = root
        self.bot = bot_instance
        self.account_manager = BinanceAccount()
        self.balance_history = []  # Historial de balances
        self.data_file = "balance_history.json"  # Archivo para guardar datos
        self.load_balance_history()  # Cargar historial al iniciar
        
        self.setup_ui()
        self.setup_account_updater()
    
    def load_balance_history(self):
        """Carga el historial de balances desde archivo"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Convertir strings de fecha a objetos datetime
                    for item in data:
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    self.balance_history = data
                print(f"✅ Historial cargado: {len(self.balance_history)} registros")
            else:
                print("📁 No se encontró archivo de historial, se creará uno nuevo")
        except Exception as e:
            print(f"❌ Error cargando historial: {e}")
            self.balance_history = []
    
    def save_balance_history(self):
        """Guarda el historial de balances en archivo"""
        try:
            # Convertir datetime a strings para JSON
            save_data = []
            for item in self.balance_history:
                item_copy = item.copy()
                item_copy['timestamp'] = item['timestamp'].isoformat()
                save_data.append(item_copy)
            
            with open(self.data_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            print(f"❌ Error guardando historial: {e}")
    
    def add_balance_record(self, total_usd):
        """Añade un registro al historial de balances"""
        record = {
            'timestamp': datetime.now(),
            'total_balance': total_usd
        }
        self.balance_history.append(record)
        
        # Mantener solo últimos 7 días de datos
        week_ago = datetime.now() - timedelta(days=7)
        self.balance_history = [r for r in self.balance_history if r['timestamp'] > week_ago]
        
        # Guardar automáticamente
        self.save_balance_history()

    def setup_ui(self):
        """Configura toda la interfaz gráfica con nuevas funcionalidades"""
        self.root.title("🤖 Trading Bot - Multiple Symbols (BINANCE) - HEIKIN ASHI")
        self.root.geometry("1400x950")  # Más alto para la gráfica
        self.root.configure(bg=DARK_BG)
        
        # Configurar tema oscuro global
        self.setup_dark_theme()
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=3)  # Bot trading
        main_frame.columnconfigure(1, weight=1)  # Info cuenta
        
        # Title
        title_label = tk.Label(main_frame, 
                            text="🤖 TRADING BOT - LIVE PRICE + CANDLE % MOVEMENT - HEIKIN ASHI", 
                            font=('Arial', 16, 'bold'),
                            fg=GOLD,
                            bg=DARK_BG)
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky=tk.W+tk.E)
        
        # Subtitle
        subtitle_label = tk.Label(main_frame,
                                text="💰 LIVE PRICE | 📊 % CURRENT CANDLE MOVEMENT | 🕯️ HEIKIN ASHI | 💼 ACCOUNT INFO | 📈 BALANCE CHART",
                                font=('Arial', 10),
                                fg=TEXT_GRAY,
                                bg=DARK_BG)
        subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 20), sticky=tk.W+tk.E)
        
        # Control frame
        control_frame = tk.Frame(main_frame, bg=DARK_BG)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
        
        # Control buttons - NUEVO BOTÓN SELL ALL
        self.start_button = tk.Button(control_frame, 
                                    text="▶️ START BOT", 
                                    command=self.start_bot,
                                    font=('Arial', 12, 'bold'),
                                    bg=GREEN,
                                    fg=DARK_BG,
                                    width=15,
                                    height=2,
                                    relief='flat',
                                    bd=0,
                                    activebackground='#00aa00',
                                    activeforeground=DARK_BG)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = tk.Button(control_frame, 
                                    text="⏸️ STOP BOT", 
                                    command=self.stop_bot,
                                    font=('Arial', 12, 'bold'),
                                    bg=RED,
                                    fg=DARK_BG,
                                    width=15,
                                    height=2,
                                    state=tk.DISABLED,
                                    relief='flat',
                                    bd=0,
                                    activebackground='#cc0000',
                                    activeforeground=DARK_BG)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # NUEVO BOTÓN SELL ALL
        self.sell_all_button = tk.Button(control_frame, 
                                    text="💸 SELL ALL", 
                                    command=self.sell_all_assets,
                                    font=('Arial', 12, 'bold'),
                                    bg=PURPLE,
                                    fg=TEXT_LIGHT,
                                    width=15,
                                    height=2,
                                    relief='flat',
                                    bd=0,
                                    activebackground='#9944ff',
                                    activeforeground=TEXT_LIGHT)
        self.sell_all_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Bot status
        self.status_label = tk.Label(control_frame,
                                    text="🛑 BOT STOPPED",
                                    font=('Arial', 12, 'bold'),
                                    fg=RED,
                                    bg=DARK_BG)
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Timing info label
        self.timing_label = tk.Label(control_frame,
                                text="⏱️ Timing: --",
                                font=('Arial', 10),
                                fg=TEXT_GRAY,
                                bg=DARK_BG)
        self.timing_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # ✅ NUEVO: Indicador de MODO TEST/LIVE
        mode_text = "🔒 MODO TEST" if not TRADING_ENABLED else "🚀 MODO LIVE"
        mode_color = YELLOW if not TRADING_ENABLED else GREEN
        
        self.mode_label = tk.Label(control_frame,
                                text=mode_text,
                                font=('Arial', 10, 'bold'),
                                fg=mode_color,
                                bg=DARK_BG)
        self.mode_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # ============ PANEL IZQUIERDO: BOT TRADING ============
        trading_frame = tk.Frame(main_frame, bg=DARK_BG)
        trading_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Frames for symbol results
        self.symbol_frames = {}
        for i, symbol in enumerate(SYMBOLS):
            symbol_frame = tk.Frame(trading_frame, 
                                bg=DARK_FRAME, 
                                relief='ridge', 
                                bd=1,
                                highlightbackground=BORDER_COLOR,
                                highlightthickness=1)
            symbol_frame.grid(row=0, column=i, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=(0, 10))
            symbol_frame.columnconfigure(0, weight=1)
            
            # Symbol title
            title_label = tk.Label(symbol_frame, 
                                text=f"📊 {symbol}", 
                                font=('Arial', 12, 'bold'),
                                fg=GOLD,
                                bg=DARK_FRAME)
            title_label.grid(row=0, column=0, sticky=tk.W, pady=(10, 5), padx=10)
            
            # Current price
            price_label = tk.Label(symbol_frame, 
                                text="Price: --", 
                                font=('Arial', 11, 'bold'), 
                                fg=GOLD,
                                bg=DARK_FRAME)
            price_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 8), padx=10)
            
            # Symbol information
            time_label = tk.Label(symbol_frame, 
                                text="Time: --:--:--", 
                                font=('Arial', 9),
                                fg=TEXT_DARK_GRAY,
                                bg=DARK_FRAME)
            time_label.grid(row=2, column=0, sticky=tk.W, pady=2, padx=10)
            
            # Results by timeframe
            result_labels = {}
            row_idx = 3
            
            for tf_name in TIMEFRAMES.keys():
                label = tk.Label(symbol_frame, 
                                text=f"{tf_name.upper():>4}: -- | %: --", 
                                font=('Arial', 10, 'bold'),
                                fg=TEXT_LIGHT,
                                bg=DARK_FRAME,
                                anchor='w')
                label.grid(row=row_idx, column=0, sticky=tk.W, pady=1, padx=10)
                result_labels[tf_name] = label
                row_idx += 1
            
            # Trading signal
            signal_label = tk.Label(symbol_frame, 
                                text="SIGNAL: --", 
                                font=('Arial', 11, 'bold'),
                                fg=TEXT_LIGHT,
                                bg=NEUTRAL_BG,
                                relief='raised',
                                bd=1)
            signal_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(8, 5), padx=10)
            row_idx += 1
            
            # Candle progress
            progress_labels = {}
            for j, tf_name in enumerate(TIMEFRAMES.keys()):
                label = tk.Label(symbol_frame, 
                                text=f"{tf_name.upper()}: --", 
                                font=('Arial', 8),
                                fg=TEXT_DARK_GRAY,
                                bg=DARK_FRAME)
                label.grid(row=row_idx, column=0, sticky=tk.W, pady=1, padx=10)
                progress_labels[tf_name] = label
                row_idx += 1
            
            self.symbol_frames[symbol] = {
                'price_label': price_label,
                'time_label': time_label,
                'result_labels': result_labels,
                'signal_label': signal_label,
                'progress_labels': progress_labels
            }
        
        # Configure equal width for symbol columns
        for i in range(len(SYMBOLS)):
            trading_frame.columnconfigure(i, weight=1)
        
        # General summary
        summary_frame = tk.Frame(trading_frame, 
                                bg=DARK_FRAME, 
                                relief='ridge', 
                                bd=1,
                                highlightbackground=BORDER_COLOR,
                                highlightthickness=1)
        summary_frame.grid(row=1, column=0, columnspan=len(SYMBOLS), sticky=(tk.W, tk.E), pady=(10, 10))
        
        summary_title = tk.Label(summary_frame, 
                                text="🎯 GENERAL SUMMARY", 
                                font=('Arial', 11, 'bold'),
                                fg=GOLD,
                                bg=DARK_FRAME)
        summary_title.pack(pady=(5, 0))
        
        self.summary_label = tk.Label(summary_frame, 
                                    text="--", 
                                    font=('Arial', 12, 'bold'),
                                    fg=TEXT_LIGHT,
                                    bg=DARK_FRAME)
        self.summary_label.pack(pady=(0, 5))
        
        # ============ NUEVA GRÁFICA DE BALANCE ============
        chart_frame = tk.Frame(trading_frame, 
                            bg=DARK_FRAME, 
                            relief='ridge', 
                            bd=1,
                            highlightbackground=BORDER_COLOR,
                            highlightthickness=1)
        chart_frame.grid(row=2, column=0, columnspan=len(SYMBOLS), sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 10))
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(0, weight=1)
        
        chart_title = tk.Label(chart_frame, 
                            text="📈 BALANCE HISTORY (USDC)", 
                            font=('Arial', 11, 'bold'),
                            fg=GOLD,
                            bg=DARK_FRAME)
        chart_title.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Canvas para la gráfica simple (texto basado)
        self.chart_canvas = tk.Canvas(chart_frame, 
                                    bg=DARKER_BG, 
                                    height=120,
                                    highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # ============ PANEL DERECHO: INFORMACIÓN DE CUENTA ============
        account_frame = tk.Frame(main_frame, bg=DARK_BG)
        account_frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Account info frame
        self.account_info_frame = tk.Frame(account_frame, 
                                        bg=ACCOUNT_BG, 
                                        relief='ridge', 
                                        bd=2,
                                        highlightbackground=PURPLE,
                                        highlightthickness=1)
        self.account_info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Account title
        account_title = tk.Label(self.account_info_frame, 
                            text="💼 BINANCE ACCOUNT", 
                            font=('Arial', 14, 'bold'),
                            fg=PURPLE,
                            bg=ACCOUNT_BG)
        account_title.pack(pady=(15, 10))
        
        # Total balance
        self.total_balance_label = tk.Label(self.account_info_frame, 
                                        text="Total: $--", 
                                        font=('Arial', 18, 'bold'),
                                        fg=GOLD,
                                        bg=ACCOUNT_BG)
        self.total_balance_label.pack(pady=(0, 15))
        
        # Last update time
        self.account_update_label = tk.Label(self.account_info_frame, 
                                        text="Last update: --", 
                                        font=('Arial', 9),
                                        fg=TEXT_GRAY,
                                        bg=ACCOUNT_BG)
        self.account_update_label.pack(pady=(0, 10))
        
        # Balances details frame
        balances_frame = tk.Frame(self.account_info_frame, bg=ACCOUNT_BG)
        balances_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollable text for balances
        self.balances_text = scrolledtext.ScrolledText(balances_frame, 
                                                    height=8, 
                                                    bg=DARKER_BG,
                                                    fg=TEXT_LIGHT,
                                                    font=('Consolas', 8),
                                                    relief='flat',
                                                    bd=0,
                                                    wrap=tk.WORD)
        self.balances_text.pack(fill=tk.BOTH, expand=True)
        self.balances_text.config(state=tk.DISABLED)
        
        # Account control buttons frame
        account_buttons_frame = tk.Frame(self.account_info_frame, bg=ACCOUNT_BG)
        account_buttons_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Refresh account button
        refresh_button = tk.Button(account_buttons_frame, 
                                text="🔄 Refresh Account", 
                                command=self.refresh_account_info,
                                font=('Arial', 10, 'bold'),
                                bg=PURPLE,
                                fg=TEXT_LIGHT,
                                relief='flat',
                                bd=0,
                                width=15)
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Manual rebalance button
        self.rebalance_button = tk.Button(account_buttons_frame, 
                                        text="⚖️ Rebalancear", 
                                        command=self.manual_rebalance,
                                        font=('Arial', 10, 'bold'),
                                        bg=GREEN,
                                        fg=DARK_BG,
                                        relief='flat',
                                        bd=0,
                                        width=15)
        self.rebalance_button.pack(side=tk.LEFT)
        
        # ============ CONSOLA EN PARTE INFERIOR ============
        console_frame = tk.Frame(trading_frame, 
                                bg=DARK_FRAME, 
                                relief='ridge', 
                                bd=1,
                                highlightbackground=BORDER_COLOR,
                                highlightthickness=1)
        console_frame.grid(row=3, column=0, columnspan=len(SYMBOLS), sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        trading_frame.rowconfigure(3, weight=1)
        
        log_title = tk.Label(console_frame, 
                            text="📝 TRADING LOGS", 
                            font=('Arial', 11, 'bold'),
                            fg=GOLD,
                            bg=DARK_FRAME)
        log_title.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Scrollable text area
        self.log_text = scrolledtext.ScrolledText(console_frame, 
                                                height=8, 
                                                bg=DARKER_BG,
                                                fg=TEXT_LIGHT,
                                                font=('Consolas', 8),
                                                relief='flat',
                                                bd=0,
                                                insertbackground=TEXT_LIGHT,
                                                selectbackground=HIGHLIGHT_COLOR)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Configure tags for log colors
        self.log_text.tag_config('GREEN', foreground=GREEN)
        self.log_text.tag_config('RED', foreground=RED)
        self.log_text.tag_config('ERROR', foreground=RED)
        self.log_text.tag_config('INFO', foreground=BLUE)
        self.log_text.tag_config('WARNING', foreground=YELLOW)
        self.log_text.tag_config('BTC', foreground='#f7931a')
        self.log_text.tag_config('FET', foreground='#00d1b2')
        self.log_text.tag_config('XLM', foreground='#14b6ff')
        self.log_text.tag_config('LINK', foreground='#2a5caa')
        self.log_text.tag_config('SOL', foreground='#00ffbd')
        self.log_text.tag_config('SUCCESS', foreground=GREEN)
        self.log_text.tag_config('HEADER', foreground=GOLD, font=('Consolas', 8, 'bold'))
        self.log_text.tag_config('TIMING', foreground=TEXT_GRAY)
        self.log_text.tag_config('TRADE', foreground=PURPLE, font=('Consolas', 8, 'bold'))
        self.log_text.tag_config('SELL_ALL', foreground=RED, font=('Consolas', 8, 'bold'))
        self.log_text.tag_config('TEST_MODE', foreground=YELLOW, font=('Consolas', 8, 'bold'))

    def setup_dark_theme(self):
        """Configura el tema oscuro globalmente"""
        self.root.option_add('*Background', DARK_BG)
        self.root.option_add('*Foreground', TEXT_LIGHT)
        self.root.option_add('*selectBackground', HIGHLIGHT_COLOR)
        self.root.option_add('*selectForeground', TEXT_LIGHT)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure('.', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TFrame', background=DARK_BG)
        self.style.configure('TLabel', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TLabelframe', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TLabelframe.Label', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TButton', background=DARK_FRAME, foreground=TEXT_LIGHT)
        self.style.configure('TScrollbar', background=DARK_FRAME, troughcolor=DARKER_BG)

    def draw_balance_chart(self):
        """Dibuja una gráfica simple del historial de balances"""
        if not self.balance_history:
            return
        
        self.chart_canvas.delete("all")
        
        width = self.chart_canvas.winfo_width()
        height = self.chart_canvas.winfo_height()
        
        if width < 10 or height < 10:
            return
        
        # Calcular min y max para escalar
        balances = [r['total_balance'] for r in self.balance_history]
        min_balance = min(balances)
        max_balance = max(balances)
        balance_range = max_balance - min_balance
        
        if balance_range == 0:
            balance_range = 1  # Evitar división por cero
        
        # Dibujar ejes
        self.chart_canvas.create_line(40, height-20, width-10, height-20, fill=TEXT_GRAY)  # Eje X
        self.chart_canvas.create_line(40, 10, 40, height-20, fill=TEXT_GRAY)  # Eje Y
        
        # Dibujar línea de balance
        points = []
        for i, record in enumerate(self.balance_history):
            x = 40 + (i / (len(self.balance_history) - 1)) * (width - 50) if len(self.balance_history) > 1 else 40
            y = height - 20 - ((record['total_balance'] - min_balance) / balance_range) * (height - 40)
            points.extend([x, y])
        
        if len(points) >= 4:
            self.chart_canvas.create_line(points, fill=GREEN, width=2, smooth=True)
        
        # Mostrar valores actuales
        current_balance = self.balance_history[-1]['total_balance']
        self.chart_canvas.create_text(width//2, 15, 
                                     text=f"Current: ${current_balance:,.2f} | Min: ${min_balance:,.2f} | Max: ${max_balance:,.2f}", 
                                     fill=TEXT_LIGHT, 
                                     font=('Arial', 8))

    def setup_account_updater(self):
        """Configura la actualización automática de la información de la cuenta"""
        self.refresh_account_info()  # Primera actualización
        # Programar actualización cada 30 segundos
        self.root.after(30000, self.setup_account_updater)

    def refresh_account_info(self):
        """Actualiza la información de la cuenta de Binance"""
        def update():
            total_usd, balances_info = self.account_manager.get_spot_balance_usd()
            
            # Actualizar en el hilo principal
            self.root.after(0, lambda: self.update_account_display(total_usd, balances_info))
        
        # Ejecutar en hilo separado para no bloquear la UI
        threading.Thread(target=update, daemon=True).start()

    def update_account_display(self, total_usd, balances_info):
        """Actualiza la visualización de la información de la cuenta"""
        # Actualizar balance total
        if isinstance(total_usd, (int, float)):
            self.total_balance_label.config(text=f"Total: ${total_usd:,.2f}")
            # Añadir al historial y actualizar gráfica
            self.add_balance_record(total_usd)
            self.root.after(100, self.draw_balance_chart)  # Dibujar después de un pequeño delay
        else:
            self.total_balance_label.config(text=f"Total: {total_usd}")
        
        # Actualizar tiempo de última actualización
        current_time = datetime.now().strftime('%H:%M:%S')
        self.account_update_label.config(text=f"Last update: {current_time}")
        
        # Actualizar detalles de balances
        self.balances_text.config(state=tk.NORMAL)
        self.balances_text.delete(1.0, tk.END)
        
        if isinstance(balances_info, list):
            for balance in balances_info:
                self.balances_text.insert(tk.END, f"• {balance}\n")
        else:
            self.balances_text.insert(tk.END, f"• {balances_info}\n")
        
        self.balances_text.config(state=tk.DISABLED)

    def manual_rebalance(self):
        """Rebalanceo manual del portfolio usando señales REALES"""
        if self.bot and self.bot.capital_manager:
            self.log_message("🔄 REBALANCEO MANUAL FORZADO INICIADO...", 'INFO')
            
            def execute_manual_rebalance():
                try:
                    # Obtener señales y precios ACTUALES del bot
                    all_signals = {}
                    all_prices = {}
                    
                    for symbol in SYMBOLS:
                        try:
                            # Obtener precio actual
                            current_price = self.bot.get_current_price(symbol)
                            all_prices[symbol] = current_price
                            
                            # Obtener señales REALES del bot si está corriendo
                            if self.bot.running and hasattr(self.bot, 'current_analysis'):
                                # Intentar obtener análisis actual del bot
                                # Esto requiere que el bot almacene sus análisis recientes
                                if symbol in self.bot.current_analysis:
                                    all_signals[symbol] = self.bot.current_analysis[symbol]
                                else:
                                    # Fallback: obtener datos en tiempo real
                                    results, _, _ = self.bot.analyze_symbol(symbol)
                                    all_signals[symbol] = results
                            else:
                                # Si el bot no está corriendo, obtener análisis fresco
                                results, _, _ = self.bot.analyze_symbol(symbol)
                                all_signals[symbol] = results
                                
                        except Exception as e:
                            self.log_message(f"❌ Error obteniendo datos de {symbol}: {str(e)}", 'ERROR')
                            # En caso de error, usar neutral como fallback
                            all_signals[symbol] = {"30m": "NEUTRAL", "1h": "NEUTRAL", "2h": "NEUTRAL"}
                            all_prices[symbol] = 0.0
                    
                    # Forzar rebalanceo manual con señales REALES
                    success, message = self.bot.capital_manager.rebalance_portfolio(all_signals, all_prices, manual_rebalance=True)
                    self.log_message(f"⚖️ {message}", 'TRADE')
                    
                    if success:
                        self.log_message("✅ REBALANCEO MANUAL COMPLETADO", 'SUCCESS')
                    else:
                        self.log_message("❌ REBALANCEO MANUAL FALLIDO", 'ERROR')
                        
                except Exception as e:
                    self.log_message(f"❌ Error en rebalanceo manual: {str(e)}", 'ERROR')
            
            # Ejecutar en hilo separado
            threading.Thread(target=execute_manual_rebalance, daemon=True).start()
        else:
            self.log_message("❌ Bot no disponible para rebalanceo", 'ERROR')
    def sell_all_assets(self):
        """Vende todos los assets y convierte todo a USDC"""
        def execute_sell_all():
            self.log_message("💸 INICIANDO VENTA TOTAL DE TODOS LOS ASSETS...", 'SELL_ALL')
            
            # Detener el bot si está corriendo
            if self.bot and self.bot.running:
                self.bot.stop_bot()
                self.log_message("🛑 Bot detenido para venta total", 'INFO')
                time.sleep(1)
            
            total_sold = 0
            assets_sold = 0
            
            for symbol in SYMBOLS:
                try:
                    # Obtener balance del asset
                    asset_balance = self.account_manager.get_symbol_balance(symbol)
                    current_price = self.account_manager.get_current_price(symbol)
                    
                    if asset_balance > 0 and current_price > 0:
                        self.log_message(f"💰 Vendiendo {asset_balance:.6f} {symbol}...", 'SELL_ALL')
                        
                        # Vender el asset
                        success, message = self.account_manager.sell_market(symbol, asset_balance)
                        
                        if success:
                            usd_value = asset_balance * current_price
                            total_sold += usd_value
                            assets_sold += 1
                            self.log_message(f"✅ {message}", 'SUCCESS')
                        else:
                            self.log_message(f"❌ Error vendiendo {symbol}: {message}", 'ERROR')
                    
                    time.sleep(0.5)  # Esperar entre órdenes
                    
                except Exception as e:
                    self.log_message(f"❌ Error procesando {symbol}: {str(e)}", 'ERROR')
            
            # Actualizar información de cuenta
            self.refresh_account_info()
            
            if assets_sold > 0:
                self.log_message(f"🎉 VENTA TOTAL COMPLETADA: {assets_sold} assets vendidos por ${total_sold:.2f} USDC", 'SELL_ALL')
            else:
                self.log_message("ℹ️ No se encontraron assets para vender", 'INFO')
        
        # Ejecutar en hilo separado
        threading.Thread(target=execute_sell_all, daemon=True).start()

    def start_bot(self):
        """Inicia el bot a través de la instancia del bot"""
        if self.bot:
            self.bot.start_bot()
    
    def stop_bot(self):
        """Detiene el bot a través de la instancia del bot"""
        if self.bot:
            self.bot.stop_bot()

    # Métodos de actualización de UI que el bot llamará
    def update_display_header(self):
        """Actualiza información general en la interfaz"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for symbol in SYMBOLS:
            self.symbol_frames[symbol]['time_label'].config(text=f"Time: {current_time}")
    
    def update_all_results(self, all_results, all_progresses, all_signals, all_prices, all_percentages):
        """Actualiza resultados de todos los símbolos en la interfaz gráfica"""
        for symbol in SYMBOLS:
            results = all_results[symbol]
            progresses = all_progresses[symbol]
            signal = all_signals[symbol]
            price = all_prices[symbol]
            percentages = all_percentages[symbol]
            
            self.update_symbol_results(symbol, results, progresses, signal, price, percentages)
    
    def update_symbol_results(self, symbol, results, progresses, signal, price, percentages):
        """Actualiza resultados de un símbolo específico"""
        frame_data = self.symbol_frames[symbol]
        
        # Update current price
        frame_data['price_label'].config(text=f"Price: ${price:.4f}")
        
        # Update results by timeframe
        for tf_name, color in results.items():
            label = frame_data['result_labels'][tf_name]
            percentage = percentages.get(tf_name, 0.0)
            
            label_text = f"{tf_name.upper():>4}: {color} | %: {percentage:+.2f}%"
            label.config(text=label_text)
            
            if "GREEN" in color:
                label.config(fg=GREEN, bg=DARK_FRAME)
            elif "RED" in color:
                label.config(fg=RED, bg=DARK_FRAME)
            else:
                label.config(fg=TEXT_GRAY, bg=DARK_FRAME)
        
        # Update progresses
        for tf_name, progress in progresses.items():
            label = frame_data['progress_labels'][tf_name]
            label.config(text=f"{tf_name.upper()}: {progress}")
        
        # Update trading signal
        frame_data['signal_label'].config(text=f"SIGNAL: {signal}")
        
        if "STRONG_BUY" in signal:
            frame_data['signal_label'].config(fg=GREEN, bg=STRONG_BUY_BG)
        elif "STRONG_SELL" in signal:
            frame_data['signal_label'].config(fg=RED, bg=STRONG_SELL_BG)
        elif "BULLISH" in signal:
            frame_data['signal_label'].config(fg=GREEN, bg=BULLISH_BG)
        elif "BEARISH" in signal:
            frame_data['signal_label'].config(fg=RED, bg=BEARISH_BG)
        else:
            frame_data['signal_label'].config(fg=YELLOW, bg=NEUTRAL_BG)
    
    def update_timing_display(self, execution_time, sleep_time, drift):
        """Actualiza la información de timing en la interfaz"""
        timing_text = f"⏱️ Exec: {execution_time:.3f}s | Sleep: {sleep_time:.3f}s | Drift: {drift:+.3f}s"
        self.timing_label.config(text=timing_text)
    
    def update_bot_status(self, running, counter=None):
        """Actualiza el estado del bot en la interfaz"""
        if running:
            self.status_label.config(text="🟢 BOT RUNNING", fg=GREEN)
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.status_label.config(text="🛑 BOT STOPPED", fg=RED)
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            if counter is not None:
                self.timing_label.config(text="⏱️ Timing: --")
    
    def log_message(self, message, tag=None):
        """Añade mensaje al console log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()