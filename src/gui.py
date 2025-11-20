import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime

from .config import *

class TradingBotGUI:
    def __init__(self, root, bot_instance):
        self.root = root
        self.bot = bot_instance  # Instancia del bot lógico
        self.setup_ui()
    
    def setup_ui(self):
        """Configura toda la interfaz gráfica"""
        self.root.title("🤖 Trading Bot - Multiple Symbols (BINANCE) - HEIKIN ASHI")
        self.root.geometry("1200x900")
        self.root.configure(bg=DARK_BG)
        
        # Configurar tema oscuro global
        self.setup_dark_theme()
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = tk.Label(main_frame, 
                              text="🤖 TRADING BOT - LIVE PRICE + CANDLE % MOVEMENT - HEIKIN ASHI", 
                              font=('Arial', 16, 'bold'),
                              fg=GOLD,
                              bg=DARK_BG)
        title_label.grid(row=0, column=0, columnspan=len(SYMBOLS), pady=(0, 15))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame,
                                 text="💰 LIVE PRICE | 📊 % CURRENT CANDLE MOVEMENT | 🕯️ HEIKIN ASHI",
                                 font=('Arial', 10),
                                 fg=TEXT_GRAY,
                                 bg=DARK_BG)
        subtitle_label.grid(row=1, column=0, columnspan=len(SYMBOLS), pady=(0, 20))
        
        # Control frame
        control_frame = tk.Frame(main_frame, bg=DARK_BG)
        control_frame.grid(row=2, column=0, columnspan=len(SYMBOLS), pady=(0, 20), sticky=(tk.W, tk.E))
        
        # Control buttons
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
        
        # Frames for symbol results
        self.symbol_frames = {}
        for i, symbol in enumerate(SYMBOLS):
            symbol_frame = tk.Frame(main_frame, 
                                   bg=DARK_FRAME, 
                                   relief='ridge', 
                                   bd=1,
                                   highlightbackground=BORDER_COLOR,
                                   highlightthickness=1)
            symbol_frame.grid(row=3, column=i, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=(0, 10))
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
            main_frame.columnconfigure(i, weight=1)
        
        # General summary
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
        
        # Log console
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
        
        # Scrollable text area
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 height=12, 
                                                 width=100,
                                                 bg=DARKER_BG,
                                                 fg=TEXT_LIGHT,
                                                 font=('Consolas', 9),
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
        self.log_text.tag_config('HEADER', foreground=GOLD, font=('Consolas', 9, 'bold'))
        self.log_text.tag_config('TIMING', foreground=TEXT_GRAY)

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