import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd

from .config import *
from .indicators import HeikinAshiCalculator, TradingIndicator

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Trading Bot - Multiple Symbols (BINANCE) - HEIKIN ASHI")
        self.root.geometry("1200x900")
        self.root.configure(bg=DARK_BG)
        
        # Configurar tema oscuro global
        self.setup_dark_theme()
        
        # Inicializar variables PRIMERO
        self.initialize_variables()
        
        # Configurar UI PRIMERO
        self.setup_ui()
        
        # Luego configurar Binance client
        self.setup_binance_client()
    
    def setup_dark_theme(self):
        """Configura el tema oscuro globalmente"""
        # Configurar colores de widgets básicos
        self.root.option_add('*Background', DARK_BG)
        self.root.option_add('*Foreground', TEXT_LIGHT)
        self.root.option_add('*selectBackground', HIGHLIGHT_COLOR)
        self.root.option_add('*selectForeground', TEXT_LIGHT)
        
        # Configurar ttk style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configurar todos los estilos para tema oscuro
        self.style.configure('.', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TFrame', background=DARK_BG)
        self.style.configure('TLabel', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TLabelframe', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TLabelframe.Label', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TButton', background=DARK_FRAME, foreground=TEXT_LIGHT)
        self.style.configure('TScrollbar', background=DARK_FRAME, troughcolor=DARKER_BG)
    
    def initialize_variables(self):
        """Inicializa variables de control"""
        self.running = False
        self.counter = 0
        self.current_prices = {}
        self.heikin_ashi_calc = HeikinAshiCalculator()
        self.indicator_calc = TradingIndicator(length=LENGTH)
        self.client = None
        self.last_update_time = None
        self.next_update_time = None
        self.execution_times = []  # Para estadísticas de timing

    def setup_ui(self):
        """Configura la interfaz de usuario con tema oscuro mejorado"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title - MEJORADO
        title_label = tk.Label(main_frame, 
                              text="🤖 TRADING BOT - LIVE PRICE + CANDLE % MOVEMENT - HEIKIN ASHI", 
                              font=('Arial', 16, 'bold'),
                              fg=GOLD,
                              bg=DARK_BG)
        title_label.grid(row=0, column=0, columnspan=len(SYMBOLS), pady=(0, 15))
        
        # Subtitle - MEJORADO
        subtitle_label = tk.Label(main_frame,
                                 text="💰 LIVE PRICE | 📊 % CURRENT CANDLE MOVEMENT | 🕯️ HEIKIN ASHI",
                                 font=('Arial', 10),
                                 fg=TEXT_GRAY,
                                 bg=DARK_BG)
        subtitle_label.grid(row=1, column=0, columnspan=len(SYMBOLS), pady=(0, 20))
        
        # Control frame - MEJORADO
        control_frame = tk.Frame(main_frame, bg=DARK_BG)
        control_frame.grid(row=2, column=0, columnspan=len(SYMBOLS), pady=(0, 20), sticky=(tk.W, tk.E))
        
        # Control buttons - MEJORADO
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
        
        # Bot status - MEJORADO
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
        
        # Frames for symbol results - MEJORADO
        self.symbol_frames = {}
        for i, symbol in enumerate(SYMBOLS):
            # Create custom frame with improved dark theme
            symbol_frame = tk.Frame(main_frame, 
                                   bg=DARK_FRAME, 
                                   relief='ridge', 
                                   bd=1,
                                   highlightbackground=BORDER_COLOR,
                                   highlightthickness=1)
            symbol_frame.grid(row=3, column=i, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=(0, 10))
            symbol_frame.columnconfigure(0, weight=1)
            
            # Symbol title - MEJORADO
            title_label = tk.Label(symbol_frame, 
                                  text=f"📊 {symbol}", 
                                  font=('Arial', 12, 'bold'),
                                  fg=GOLD,
                                  bg=DARK_FRAME)
            title_label.grid(row=0, column=0, sticky=tk.W, pady=(10, 5), padx=10)
            
            # Current price - MEJORADO
            price_label = tk.Label(symbol_frame, 
                                  text="Price: --", 
                                  font=('Arial', 11, 'bold'), 
                                  fg=GOLD,
                                  bg=DARK_FRAME)
            price_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 8), padx=10)
            
            # Symbol information - MEJORADO
            time_label = tk.Label(symbol_frame, 
                                 text="Time: --:--:--", 
                                 font=('Arial', 9),
                                 fg=TEXT_DARK_GRAY,
                                 bg=DARK_FRAME)
            time_label.grid(row=2, column=0, sticky=tk.W, pady=2, padx=10)
            
            # Results by timeframe - MEJORADO
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
            
            # Trading signal - MEJORADO
            signal_label = tk.Label(symbol_frame, 
                                   text="SIGNAL: --", 
                                   font=('Arial', 11, 'bold'),
                                   fg=TEXT_LIGHT,
                                   bg=NEUTRAL_BG,
                                   relief='raised',
                                   bd=1)
            signal_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(8, 5), padx=10)
            row_idx += 1
            
            # Candle progress - MEJORADO
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
            main_frame.columnconfigure(i, weight=1)
        
        # General summary - MEJORADO
        summary_frame = tk.Frame(main_frame, 
                                bg=DARK_FRAME, 
                                relief='ridge', 
                                bd=1,
                                highlightbackground=BORDER_COLOR,
                                highlightthickness=1)
        summary_frame.grid(row=4, column=0, columnspan=len(SYMBOLS), sticky=(tk.W, tk.E), pady=(10, 10))
        
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
        
        # Log console - MEJORADO
        log_frame = tk.Frame(main_frame, 
                            bg=DARK_FRAME, 
                            relief='ridge', 
                            bd=1,
                            highlightbackground=BORDER_COLOR,
                            highlightthickness=1)
        log_frame.grid(row=5, column=0, columnspan=len(SYMBOLS), sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        log_title = tk.Label(log_frame, 
                            text="📝 DETAILED LOGS", 
                            font=('Arial', 11, 'bold'),
                            fg=GOLD,
                            bg=DARK_FRAME)
        log_title.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        # Scrollable text area mejorado
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 height=12, 
                                                 width=100,
                                                 bg=DARKER_BG,
                                                 fg=TEXT_LIGHT,
                                                 font=('Consolas', 9),
                                                 relief='flat',
                                                 bd=0,
                                                 insertbackground=TEXT_LIGHT,  # Cursor visible
                                                 selectbackground=HIGHLIGHT_COLOR)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Configure tags for log colors - MEJORADO
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
        self.log_text.tag_config('HEADER', foreground=GOLD, font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('TIMING', foreground=TEXT_GRAY)

    def setup_binance_client(self):
        """Configura el cliente de Binance"""
        try:
            self.client = Client(API_KEY, API_SECRET)
            self.log_message("✅ Conectado a Binance API", 'INFO')
        except Exception as e:
            self.log_message(f"❌ Error conectando a Binance: {str(e)}", 'ERROR')
            self.log_message("⚠️ Usando cliente no autenticado para datos públicos", 'WARNING')
            try:
                self.client = Client()
            except:
                self.client = None

    def get_current_price(self, symbol):
        """Obtiene el precio actual del símbolo"""
        try:
            if self.client is None:
                return 0.0
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.log_message(f"❌ Error obteniendo precio para {symbol}: {str(e)}", 'ERROR')
            return 0.0

    def calculate_movement_percentage(self, df):
        """Calcula el porcentaje de movimiento de la vela actual"""
        try:
            if len(df) < 1:
                return 0.0
            
            current_candle = df.iloc[-1]
            open_price = current_candle['Open']
            current_price = current_candle['Close']
            
            if open_price == 0:
                return 0.0
            
            percentage = ((current_price - open_price) / open_price) * 100
            return percentage
            
        except Exception as e:
            return 0.0

    def log_message(self, message, tag=None):
        """Añade mensaje al console log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_timing_display(self, execution_time, sleep_time, drift):
        """Actualiza la información de timing en la interfaz"""
        timing_text = f"⏱️ Exec: {execution_time:.3f}s | Sleep: {sleep_time:.3f}s | Drift: {drift:+.3f}s"
        self.timing_label.config(text=timing_text)
    
    def start_bot(self):
        """Inicia el bot en un hilo separado"""
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="🟢 BOT RUNNING", fg=GREEN)
            
            # Inicializar timing
            self.last_update_time = datetime.now()
            self.next_update_time = (self.last_update_time + timedelta(seconds=1)).replace(microsecond=0)
            self.execution_times = []
            
            self.log_message("🤖 Bot started - Showing PRICE + % CANDLE MOVEMENT", 'INFO')
            self.log_message("⏰ PRECISE TIMING: Updating EVERY SECOND synchronized with system clock", 'INFO')
            self.log_message("💰 Live prices + % movement by timeframe", 'INFO')
            self.log_message("📊 Timing statistics will be shown every 30 executions", 'INFO')
            
            # Start bot loop in separate thread
            self.bot_thread = threading.Thread(target=self.run_bot_precise_timing, daemon=True)
            self.bot_thread.start()
    
    def stop_bot(self):
        """Detiene el bot"""
        if self.running:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="🛑 BOT STOPPED", fg=RED)
            self.timing_label.config(text="⏱️ Timing: --")
            
            # Mostrar estadísticas finales de timing
            if self.execution_times:
                avg_time = sum(self.execution_times) / len(self.execution_times)
                max_time = max(self.execution_times)
                min_time = min(self.execution_times)
                self.log_message(f"📊 FINAL TIMING STATS: Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s", 'INFO')
            
            self.log_message(f"⏹️ Bot stopped. Total executions: {self.counter}", 'INFO')
    
    def run_bot_precise_timing(self):
        """Bucle principal del bot con timing preciso de 1 segundo"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Solo ejecutar si es tiempo de actualizar (sincronizado con segundos del reloj)
                if current_time >= self.next_update_time:
                    execution_start = datetime.now()
                    self.counter += 1
                    
                    # Calcular tiempo de la próxima actualización (próximo segundo exacto)
                    self.next_update_time = (execution_start + timedelta(seconds=1)).replace(microsecond=0)
                    
                    # Update interface header inmediatamente
                    self.root.after(0, self.update_display_header)
                    
                    # Only show every 10 executions to avoid log spam
                    if self.counter % 10 == 1:
                        self.log_message(f"\n{'='*80}", 'INFO')
                        self.log_message(f"🔄 EXECUTION #{self.counter} - {execution_start.strftime('%H:%M:%S.%f')[:-3]}", 'INFO')
                    
                    # Analyze all symbols
                    all_results = {}
                    all_progresses = {}
                    all_signals = {}
                    all_prices = {}
                    all_percentages = {}
                    
                    for symbol in SYMBOLS:
                        # Only detailed log every 10 executions
                        if self.counter % 10 == 1:
                            self.log_message(f"\n🔍 Analyzing {symbol}...", symbol.replace('USDT', ''))
                        
                        # Get current price
                        current_price = self.get_current_price(symbol)
                        all_prices[symbol] = current_price
                        
                        results, progresses, percentages = self.analyze_symbol(symbol)
                        signal = self.generate_trading_signal(results, symbol)
                        
                        all_results[symbol] = results
                        all_progresses[symbol] = progresses
                        all_signals[symbol] = signal
                        all_percentages[symbol] = percentages
                    
                    # Update results in interface (ALWAYS)
                    self.root.after(0, lambda: self.update_all_results(all_results, all_progresses, all_signals, all_prices, all_percentages))
                    
                    # Generate general summary (only log every 10 executions)
                    if self.counter % 10 == 1:
                        self.generate_general_summary(all_signals)
                    
                    # Calcular tiempo de ejecución y ajustar sleep
                    execution_end = datetime.now()
                    execution_time = (execution_end - execution_start).total_seconds()
                    self.execution_times.append(execution_time)
                    
                    # Calcular drift (cuánto nos pasamos del tiempo ideal)
                    actual_next_time = datetime.now()
                    drift = (actual_next_time - self.next_update_time).total_seconds()
                    
                    # Calcular sleep time dinámicamente
                    sleep_time = max(0.01, 1.0 - execution_time - drift)
                    
                    # Actualizar display de timing
                    self.root.after(0, lambda: self.update_timing_display(execution_time, sleep_time, drift))
                    
                    # Log timing cada 30 ejecuciones para debugging
                    if self.counter % 30 == 1 and len(self.execution_times) > 1:
                        avg_time = sum(self.execution_times) / len(self.execution_times)
                        max_time = max(self.execution_times)
                        self.log_message(f"📊 TIMING STATS: Current: {execution_time:.3f}s, Avg: {avg_time:.3f}s, Max: {max_time:.3f}s", 'TIMING')
                        self.log_message(f"⏱️ ADJUSTMENT: Sleep: {sleep_time:.3f}s, Drift: {drift:+.3f}s", 'TIMING')
                    
                    # Sleep preciso
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
                else:
                    # Esperar hasta el próximo segundo con polling eficiente
                    time_until_next = (self.next_update_time - datetime.now()).total_seconds()
                    if time_until_next > 0.1:
                        time.sleep(0.1)  # Poll cada 100ms
                    elif time_until_next > 0.01:
                        time.sleep(0.01)  # Poll cada 10ms cuando está cerca
                    # Si está muy cerca, continuar sin sleep
                        
            except Exception as e:
                self.log_message(f"❌ Error in main loop: {str(e)}", 'ERROR')
                time.sleep(1)  # En caso de error, esperar 1 segundo
    
    def update_display_header(self):
        """Actualiza información general en la interfaz con tiempo actual"""
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
        """Actualiza resultados de un símbolo específico con mejoras de tema oscuro"""
        frame_data = self.symbol_frames[symbol]
        
        # Update current price
        frame_data['price_label'].config(text=f"Price: ${price:.4f}")
        
        # Update results by timeframe (WITH % MOVEMENT)
        for tf_name, color in results.items():
            label = frame_data['result_labels'][tf_name]
            percentage = percentages.get(tf_name, 0.0)
            
            # New format: COLOR + %
            label_text = f"{tf_name.upper():>4}: {color} | %: {percentage:+.2f}%"
            label.config(text=label_text)
            
            # Color based on result AND percentage - MEJORADO
            if "GREEN" in color:
                label.config(fg=GREEN, bg=DARK_FRAME)
            elif "RED" in color:
                label.config(fg=RED, bg=DARK_FRAME)
            else:
                label.config(fg=TEXT_GRAY, bg=DARK_FRAME)
        
        # Update progresses - MEJORADO
        for tf_name, progress in progresses.items():
            label = frame_data['progress_labels'][tf_name]
            label.config(text=f"{tf_name.upper()}: {progress}")
        
        # Update trading signal - MEJORADO con mejores colores
        frame_data['signal_label'].config(text=f"SIGNAL: {signal}")
        
        # Color the signal con mejor contraste
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

    def get_real_time_data(self, symbol, timeframe):
        """Obtiene datos de Binance INCLUYENDO la vela actual en formación"""
        try:
            if self.client is None:
                raise Exception("Cliente de Binance no disponible")
                
            # Obtener velas de Binance
            klines = self.client.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=100
            )
            
            if not klines:
                raise Exception("No data from Binance")
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'Close time', 'Quote asset volume', 'Number of trades',
                'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
            ])
            
            # Convertir tipos de datos
            df['Open'] = df['Open'].astype(float)
            df['High'] = df['High'].astype(float)
            df['Low'] = df['Low'].astype(float)
            df['Close'] = df['Close'].astype(float)
            df['Volume'] = df['Volume'].astype(float)
            
            # Convertir timestamp a datetime
            df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
            df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
            
            # Establecer índice
            df.set_index('Open time', inplace=True)
            
            # Convertir a Heikin Ashi
            df = self.heikin_ashi_calc.convert_to_heikin_ashi(df)
            
            return df
            
        except BinanceAPIException as e:
            raise Exception(f"Binance API Error: {e.message}")
        except Exception as e:
            raise Exception(f"Error obteniendo datos: {str(e)}")

    def get_current_candle_progress(self, timeframe):
        """Calcula el progreso de la vela actual"""
        now = datetime.now()
        
        if timeframe == "30m":
            progress = (now.minute % 30) / 30 * 100
            minutes_remaining = 30 - (now.minute % 30)
            return f"{progress:.0f}% ({minutes_remaining}min left)"
        elif timeframe == "1h":
            progress = now.minute / 60 * 100
            minutes_remaining = 60 - now.minute
            return f"{progress:.0f}% ({minutes_remaining}min left)"
        elif timeframe == "2h":
            hour_in_2h_cycle = now.hour % 2
            progress = (hour_in_2h_cycle * 60 + now.minute) / 120 * 100
            hours_remaining = 1 - hour_in_2h_cycle
            minutes_remaining = 60 - now.minute
            return f"{progress:.0f}% ({hours_remaining}h {minutes_remaining}min left)"

    def analyze_symbol(self, symbol):
        """Analiza un símbolo específico usando Heikin Ashi"""
        symbol_short = symbol.replace('USDT', '')
        
        # Solo log detallado cada 10 ejecuciones para evitar spam
        if self.counter % 10 == 1:
            self.log_message(f"📊 ANALYSIS {symbol_short} - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", symbol_short)
            self.log_message("🎯 Using CURRENT HEIKIN ASHI CANDLE + % MOVEMENT", symbol_short)
            self.log_message("-" * 50, symbol_short)
        
        results = {}
        progresses = {}
        percentages = {}
        
        for name, tf in TIMEFRAMES.items():
            try:
                if self.counter % 10 == 1:
                    self.log_message(f"Analyzing {name}...", symbol_short)
                
                df = self.get_real_time_data(symbol, tf)
                
                if len(df) < LENGTH:
                    color = f"ERROR: Only {len(df)} candles"
                    movement_percentage = 0.0
                else:
                    # Calculate current candle movement percentage
                    movement_percentage = self.calculate_movement_percentage(df)
                    
                    # Show last candle timestamp only every 10 executions
                    if self.counter % 10 == 1:
                        last_candle_time = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
                        self.log_message(f"  Current candle: {last_candle_time} | %: {movement_percentage:+.2f}%", symbol_short)
                    
                    color, diff = self.indicator_calc.calculate_indicator_oo(df, symbol)
                
                results[name] = color
                progresses[name] = self.get_current_candle_progress(tf)
                percentages[name] = movement_percentage
                
                # Log with color only every 10 executions
                if self.counter % 10 == 1:
                    if "GREEN" in color:
                        self.log_message(f"{name.upper():>4} → {color} | %: {movement_percentage:+.2f}%", 'GREEN')
                    elif "RED" in color:
                        self.log_message(f"{name.upper():>4} → {color} | %: {movement_percentage:+.2f}%", 'RED')
                    else:
                        self.log_message(f"{name.upper():>4} → {color} | %: {movement_percentage:+.2f}%", 'ERROR')
                    
            except Exception as e:
                error_msg = f"ERROR: {str(e)}"
                results[name] = error_msg
                progresses[name] = "N/A"
                percentages[name] = 0.0
                if self.counter % 10 == 1:
                    self.log_message(f"{name.upper():>4} → {error_msg}", 'ERROR')
        
        if self.counter % 10 == 1:
            self.log_message("-" * 50, symbol_short)
            
            # Show current candle progress
            self.log_message("📈 CURRENT CANDLE PROGRESS:", symbol_short)
            for tf, progress in progresses.items():
                self.log_message(f"  {tf.upper():>4} → {progress}", symbol_short)
        
        return results, progresses, percentages

    def generate_trading_signal(self, results, symbol):
        """Genera señal de trading basada en 3 timeframes"""
        greens = sum(1 for c in results.values() if "GREEN" in c)
        reds = sum(1 for c in results.values() if "RED" in c)
        
        symbol_short = symbol.replace('USDT', '')
        
        # Only log every 10 executions to avoid spam
        if self.counter % 10 == 1:
            self.log_message(f"🎯 {symbol_short} - SIGNAL: {greens}/3 GREEN | {reds}/3 RED", symbol_short)
        
        if greens == 3:
            if self.counter % 10 == 1:
                self.log_message(f"🚀 {symbol_short} - BUY ENTRY - All timeframes GREEN", 'GREEN')
            return "STRONG_BUY 🚀"
        elif reds == 3:
            if self.counter % 10 == 1:
                self.log_message(f"🔻 {symbol_short} - SELL ENTRY - All timeframes RED", 'RED') 
            return "STRONG_SELL 🔻"
        elif greens == 2:
            if self.counter % 10 == 1:
                self.log_message(f"📈 {symbol_short} - BULLISH SESSION - Majority GREEN", 'GREEN')
            return "BULLISH_TREND 📈"
        elif reds == 2:
            if self.counter % 10 == 1:
                self.log_message(f"📉 {symbol_short} - BEARISH SESSION - Majority RED", 'RED')
            return "BEARISH_TREND 📉"
        else:
            if self.counter % 10 == 1:
                self.log_message(f"⚡ {symbol_short} - UNDECIDED MARKET - Mixed signals", 'WARNING')
            return "CONSOLIDATION ⚡"

    def generate_general_summary(self, all_signals):
        """Genera un resumen general de todas las señales"""
        strong_buys = sum(1 for s in all_signals.values() if "STRONG_BUY" in s)
        strong_sells = sum(1 for s in all_signals.values() if "STRONG_SELL" in s)
        bullish = sum(1 for s in all_signals.values() if "BULLISH" in s)
        bearish = sum(1 for s in all_signals.values() if "BEARISH" in s)
        
        summary = f"📈 BUYS: {strong_buys} | 📉 SELLS: {strong_sells} | 🟢 BULLISH: {bullish} | 🔻 BEARISH: {bearish}"
        
        self.summary_label.config(text=summary)
        self.log_message(f"🎯 GENERAL SUMMARY: {summary}", 'INFO')