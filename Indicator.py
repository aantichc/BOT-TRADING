import pandas as pd
import numpy as np
from datetime import datetime
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from binance.client import Client
from binance.exceptions import BinanceAPIException

# ============= BINANCE CONFIGURATION =============
API_KEY = "F9D9iYQqpiQvZ7FqSuaGugeN1I4QfnBTMnro1SGrga84PZeC7SpXFHiwqkWBkGlo"
API_SECRET = "yAseWTGu6vFlPKyIGkhttip23lcLVsvnybOgflFSt23EE1RjVg0mzdtTE84DBVNY"

symbols = ["BTCUSDT", "FETUSDT", "LINKUSDT", "XLMUSDT", "SOLUSDT"]
length = 8                  
UPDATE_INTERVAL = 1  # ⬅️ 1 SECOND

timeframes = {
    "30m": Client.KLINE_INTERVAL_30MINUTE,
    "1h":  Client.KLINE_INTERVAL_1HOUR, 
    "2h":  Client.KLINE_INTERVAL_2HOUR
}

# Configure dark theme colors
DARK_BG = '#1a1a1a'
DARKER_BG = '#0d0d0d'
DARK_FRAME = '#2d2d2d'
TEXT_LIGHT = '#ffffff'
TEXT_GRAY = '#cccccc'
GREEN = '#00ff00'
RED = '#ff0000'
YELLOW = '#ffff00'
GOLD = '#ffd700'

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Trading Bot - Multiple Symbols (BINANCE) - HEIKIN ASHI")
        self.root.geometry("1200x900")
        self.root.configure(bg=DARK_BG)
        
        # Configure ttk style for dark theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure styles for dark theme
        self.style.configure('TFrame', background=DARK_BG)
        self.style.configure('TLabel', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TLabelframe', background=DARK_BG, foreground=TEXT_LIGHT)
        self.style.configure('TLabelframe.Label', background=DARK_BG, foreground=TEXT_LIGHT)
        
        # Control variables
        self.running = False
        self.counter = 0
        self.current_prices = {}
        
        # Binance client
        try:
            self.client = Client(API_KEY, API_SECRET)
            self.setup_ui()
            self.log_message("✅ Connected to Binance API", 'INFO')
        except Exception as e:
            self.setup_ui()
            self.log_message(f"❌ Error connecting to Binance: {str(e)}", 'ERROR')
            self.log_message("⚠️ Using unauthenticated client for public data", 'WARNING')
            self.client = Client()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.configure(style='TFrame')
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = tk.Label(main_frame, 
                              text="🤖 TRADING BOT - LIVE PRICE + CANDLE % MOVEMENT - HEIKIN ASHI", 
                              font=('Arial', 16, 'bold'),
                              fg=TEXT_LIGHT,
                              bg=DARK_BG)
        title_label.grid(row=0, column=0, columnspan=len(symbols), pady=(0, 20))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame,
                                 text="💰 LIVE PRICE | 📊 % CURRENT CANDLE MOVEMENT | 🕯️ HEIKIN ASHI",
                                 font=('Arial', 10),
                                 fg=TEXT_GRAY,
                                 bg=DARK_BG)
        subtitle_label.grid(row=1, column=0, columnspan=len(symbols), pady=(0, 20))
        
        # Control frame
        control_frame = tk.Frame(main_frame, bg=DARK_BG)
        control_frame.grid(row=2, column=0, columnspan=len(symbols), pady=(0, 20), sticky=(tk.W, tk.E))
        
        # Control buttons
        self.start_button = tk.Button(control_frame, 
                                     text="▶️ START BOT", 
                                     command=self.start_bot,
                                     font=('Arial', 12, 'bold'),
                                     bg='#28a745',
                                     fg=TEXT_LIGHT,
                                     width=15,
                                     height=2,
                                     relief='flat',
                                     bd=0)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = tk.Button(control_frame, 
                                    text="⏸️ STOP BOT", 
                                    command=self.stop_bot,
                                    font=('Arial', 12, 'bold'),
                                    bg='#dc3545',
                                    fg=TEXT_LIGHT,
                                    width=15,
                                    height=2,
                                    state=tk.DISABLED,
                                    relief='flat',
                                    bd=0)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Bot status
        self.status_label = tk.Label(control_frame,
                                    text="🛑 BOT STOPPED",
                                    font=('Arial', 12, 'bold'),
                                    fg='#dc3545',
                                    bg=DARK_BG)
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Frames for symbol results
        self.symbol_frames = {}
        for i, symbol in enumerate(symbols):
            # Create custom frame with dark background
            symbol_frame = tk.Frame(main_frame, bg=DARK_FRAME, relief='ridge', bd=1)
            symbol_frame.grid(row=3, column=i, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=(0, 10))
            symbol_frame.columnconfigure(0, weight=1)
            
            # Symbol title
            title_label = tk.Label(symbol_frame, text=f"📊 {symbol}", 
                                  font=('Arial', 12, 'bold'),
                                  fg=TEXT_LIGHT,
                                  bg=DARK_FRAME)
            title_label.grid(row=0, column=0, sticky=tk.W, pady=(10, 5), padx=10)
            
            # Current price
            price_label = tk.Label(symbol_frame, text="Price: --", 
                                  font=('Arial', 11, 'bold'), 
                                  fg=GOLD,
                                  bg=DARK_FRAME)
            price_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 8), padx=10)
            
            # Symbol information
            time_label = tk.Label(symbol_frame, text="Time: --:--:--", 
                                 font=('Arial', 9),
                                 fg=TEXT_GRAY,
                                 bg=DARK_FRAME)
            time_label.grid(row=2, column=0, sticky=tk.W, pady=2, padx=10)
            
            # Results by timeframe
            result_labels = {}
            row_idx = 3
            
            for tf_name in timeframes.keys():
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
                                   bg=DARK_FRAME)
            signal_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(8, 5), padx=10)
            row_idx += 1
            
            # Candle progress
            progress_labels = {}
            for j, tf_name in enumerate(timeframes.keys()):
                label = tk.Label(symbol_frame, 
                                text=f"{tf_name.upper()}: --", 
                                font=('Arial', 8),
                                fg=TEXT_GRAY,
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
        for i in range(len(symbols)):
            main_frame.columnconfigure(i, weight=1)
        
        # General summary
        summary_frame = tk.Frame(main_frame, bg=DARK_FRAME, relief='ridge', bd=1)
        summary_frame.grid(row=4, column=0, columnspan=len(symbols), sticky=(tk.W, tk.E), pady=(10, 10))
        
        summary_title = tk.Label(summary_frame, text="🎯 GENERAL SUMMARY", 
                                font=('Arial', 11, 'bold'),
                                fg=TEXT_LIGHT,
                                bg=DARK_FRAME)
        summary_title.pack(pady=(5, 0))
        
        self.summary_label = tk.Label(summary_frame, 
                                     text="--", 
                                     font=('Arial', 12, 'bold'),
                                     fg=TEXT_LIGHT,
                                     bg=DARK_FRAME)
        self.summary_label.pack(pady=(0, 5))
        
        # Log console
        log_frame = tk.Frame(main_frame, bg=DARK_FRAME, relief='ridge', bd=1)
        log_frame.grid(row=5, column=0, columnspan=len(symbols), sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        log_title = tk.Label(log_frame, text="📝 DETAILED LOGS", 
                            font=('Arial', 11, 'bold'),
                            fg=TEXT_LIGHT,
                            bg=DARK_FRAME)
        log_title.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 height=12, 
                                                 width=100,
                                                 bg=DARKER_BG,
                                                 fg=TEXT_LIGHT,
                                                 font=('Consolas', 8),
                                                 relief='flat',
                                                 bd=0)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        
        # Configure tags for log colors
        self.log_text.tag_config('GREEN', foreground=GREEN)
        self.log_text.tag_config('RED', foreground=RED)
        self.log_text.tag_config('ERROR', foreground='#ff6b6b')
        self.log_text.tag_config('INFO', foreground='#4ecdc4')
        self.log_text.tag_config('WARNING', foreground=YELLOW)
        self.log_text.tag_config('BTC', foreground='#f7931a')
        self.log_text.tag_config('FET', foreground='#00d1b2')
        self.log_text.tag_config('XLM', foreground='#14b6ff')
        self.log_text.tag_config('LINK', foreground='#2a5caa')
        self.log_text.tag_config('SOL', foreground='#00ffbd')

    def get_current_price(self, symbol):
        """Gets the current price of the symbol"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.log_message(f"❌ Error getting price for {symbol}: {str(e)}", 'ERROR')
            return 0.0

    def calculate_movement_percentage(self, df):
        """Calculates the percentage movement of the current candle"""
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
        """Adds message to log console"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_bot(self):
        """Starts the bot in a separate thread"""
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="🟢 BOT RUNNING", fg='#28a745')
            
            self.log_message("🤖 Bot started - Showing PRICE + % CANDLE MOVEMENT", 'INFO')
            self.log_message("⏰ Updating EVERY SECOND in real time", 'INFO')
            self.log_message("💰 Live prices + % movement by timeframe", 'INFO')
            
            # Start bot loop in separate thread
            self.bot_thread = threading.Thread(target=self.run_bot_second_by_second, daemon=True)
            self.bot_thread.start()
    
    def stop_bot(self):
        """Stops the bot"""
        if self.running:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="🛑 BOT STOPPED", fg='#dc3545')
            self.log_message(f"⏹️ Bot stopped. Total executions: {self.counter}", 'INFO')
    
    def run_bot_second_by_second(self):
        """Main bot loop - update every second"""
        while self.running:
            try:
                self.counter += 1
                
                # Update interface
                self.root.after(0, self.update_display_header)
                
                # Only show every 10 executions to avoid log spam
                if self.counter % 10 == 1:
                    self.log_message(f"\n{'='*80}", 'INFO')
                    self.log_message(f"🔄 EXECUTION #{self.counter}", 'INFO')
                
                # Analyze all symbols
                all_results = {}
                all_progresses = {}
                all_signals = {}
                all_prices = {}
                all_percentages = {}
                
                for symbol in symbols:
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
                
                # Wait EXACTLY 1 second before next update
                time.sleep(UPDATE_INTERVAL)
                        
            except Exception as e:
                self.log_message(f"❌ Error in main loop: {str(e)}", 'ERROR')
                time.sleep(1)
    
    def update_display_header(self):
        """Updates general information in the interface"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for symbol in symbols:
            self.symbol_frames[symbol]['time_label'].config(text=f"Time: {current_time}")
    
    def update_all_results(self, all_results, all_progresses, all_signals, all_prices, all_percentages):
        """Updates results of all symbols in the graphical interface"""
        for symbol in symbols:
            results = all_results[symbol]
            progresses = all_progresses[symbol]
            signal = all_signals[symbol]
            price = all_prices[symbol]
            percentages = all_percentages[symbol]
            
            self.update_symbol_results(symbol, results, progresses, signal, price, percentages)
    
    def update_symbol_results(self, symbol, results, progresses, signal, price, percentages):
        """Updates results of a specific symbol"""
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
            
            # Color based on result AND percentage
            if "GREEN" in color:
                label.config(fg=GREEN)
            elif "RED" in color:
                label.config(fg=RED)
            else:
                label.config(fg='#ff6b6b')
        
        # Update progresses
        for tf_name, progress in progresses.items():
            label = frame_data['progress_labels'][tf_name]
            label.config(text=f"{tf_name.upper()}: {progress}")
        
        # Update trading signal
        frame_data['signal_label'].config(text=f"SIGNAL: {signal}")
        
        # Color the signal
        if "STRONG_BUY" in signal:
            frame_data['signal_label'].config(fg=GREEN, bg='#1e3a1e')
        elif "STRONG_SELL" in signal:
            frame_data['signal_label'].config(fg=RED, bg='#3a1e1e')
        elif "BULLISH" in signal:
            frame_data['signal_label'].config(fg='#90ee90', bg=DARK_FRAME)
        elif "BEARISH" in signal:
            frame_data['signal_label'].config(fg='#ff6b6b', bg=DARK_FRAME)
        else:
            frame_data['signal_label'].config(fg=YELLOW, bg=DARK_FRAME)

    # ============= HEIKIN ASHI FUNCTIONS =============
    
    def convert_to_heikin_ashi(self, df):
        """Converts a normal candle DataFrame to Heikin Ashi"""
        try:
            ha_df = df.copy()
            
            # Calculate Heikin Ashi
            ha_df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
            
            # Initialize HA_Open with first value
            ha_df['HA_Open'] = 0.0
            ha_df.loc[ha_df.index[0], 'HA_Open'] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
            
            # Calculate HA_Open for remaining candles
            for i in range(1, len(ha_df)):
                ha_df.iloc[i, ha_df.columns.get_loc('HA_Open')] = (
                    ha_df['HA_Open'].iloc[i-1] + ha_df['HA_Close'].iloc[i-1]
                ) / 2
            
            # Calculate HA_High and HA_Low
            ha_df['HA_High'] = ha_df[['HA_Open', 'HA_Close', 'High']].max(axis=1)
            ha_df['HA_Low'] = ha_df[['HA_Open', 'HA_Close', 'Low']].min(axis=1)
            
            # Replace original columns with Heikin Ashi
            ha_df['Open'] = ha_df['HA_Open']
            ha_df['High'] = ha_df['HA_High']
            ha_df['Low'] = ha_df['HA_Low']
            ha_df['Close'] = ha_df['HA_Close']
            
            # Remove temporary columns
            ha_df.drop(['HA_Open', 'HA_High', 'HA_Low', 'HA_Close'], axis=1, inplace=True)
            
            return ha_df
            
        except Exception as e:
            raise Exception(f"Error converting to Heikin Ashi: {str(e)}")
    
    def get_real_time_data(self, symbol, timeframe):
        """Gets data from Binance INCLUDING the current forming candle"""
        try:
            # Get candles from Binance
            klines = self.client.get_klines(
                symbol=symbol,
                interval=timeframe,
                limit=100
            )
            
            if not klines:
                raise Exception("No data from Binance")
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
                'Close time', 'Quote asset volume', 'Number of trades',
                'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
            ])
            
            # Convert data types
            df['Open'] = df['Open'].astype(float)
            df['High'] = df['High'].astype(float)
            df['Low'] = df['Low'].astype(float)
            df['Close'] = df['Close'].astype(float)
            df['Volume'] = df['Volume'].astype(float)
            
            # Convert timestamp to datetime
            df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
            df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
            
            # Set index
            df.set_index('Open time', inplace=True)
            
            # Convert to Heikin Ashi
            df = self.convert_to_heikin_ashi(df)
            
            return df
            
        except BinanceAPIException as e:
            raise Exception(f"Binance API Error: {e.message}")
        except Exception as e:
            raise Exception(f"Error getting data: {str(e)}")

    def calculate_indicator_oo(self, df, symbol):
        """Calculates indicator using current INCOMPLETE candle in Heikin Ashi"""
        try:
            if len(df) < length:
                return "ERROR: Not enough data", 0.0
                
            df = df.copy()
            
            # Indicator calculations
            df['ys1'] = (df['High'] + df['Low'] + df['Close'] * 2) / 4
            df['rk3'] = df['ys1'].ewm(span=length, adjust=False).mean()
            df['rk4'] = df['ys1'].rolling(window=length).std().fillna(0.001)
            
            df['rk5'] = np.where(df['rk4'] != 0, 
                                (df['ys1'] - df['rk3']) * 100 / df['rk4'], 
                                0)
            
            df['rk6'] = df['rk5'].ewm(span=length, adjust=False).mean()
            df['up'] = df['rk6'].ewm(span=length, adjust=False).mean()
            df['down'] = df['up'].ewm(span=length, adjust=False).mean()
            
            # Analyze current candle
            last_up = df['up'].iloc[-1]
            last_down = df['down'].iloc[-1]
            
            # Debug info (only every 10 executions)
            if self.counter % 10 == 1:
                diff = last_up - last_down
                symbol_short = symbol.replace('USDT', '')
                self.log_message(f"    {symbol_short} - up: {last_up:.4f}, down: {last_down:.4f}, diff: {diff:.4f}", symbol_short)
            
            if last_up > last_down:
                return "GREEN 🟢", (last_up - last_down)
            else:
                return "RED 🔴", (last_up - last_down)
                
        except Exception as e:
            return f"ERROR: {str(e)}", 0.0

    def get_current_candle_progress(self, timeframe):
        """Calculates progress of current candle"""
        now = datetime.now()
        
        if timeframe == Client.KLINE_INTERVAL_30MINUTE:
            progress = (now.minute % 30) / 30 * 100
            minutes_remaining = 30 - (now.minute % 30)
            return f"{progress:.0f}% ({minutes_remaining}min left)"
        elif timeframe == Client.KLINE_INTERVAL_1HOUR:
            progress = now.minute / 60 * 100
            minutes_remaining = 60 - now.minute
            return f"{progress:.0f}% ({minutes_remaining}min left)"
        elif timeframe == Client.KLINE_INTERVAL_2HOUR:
            hour_in_2h_cycle = now.hour % 2
            progress = (hour_in_2h_cycle * 60 + now.minute) / 120 * 100
            hours_remaining = 1 - hour_in_2h_cycle
            minutes_remaining = 60 - now.minute
            return f"{progress:.0f}% ({hours_remaining}h {minutes_remaining}min left)"

    def analyze_symbol(self, symbol):
        """Analyzes a specific symbol using Heikin Ashi"""
        symbol_short = symbol.replace('USDT', '')
        
        # Only detailed log every 10 executions to avoid spam
        if self.counter % 10 == 1:
            self.log_message(f"📊 ANALYSIS {symbol_short} - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", symbol_short)
            self.log_message("🎯 Using CURRENT HEIKIN ASHI CANDLE + % MOVEMENT", symbol_short)
            self.log_message("-" * 50, symbol_short)
        
        results = {}
        progresses = {}
        percentages = {}
        
        for name, tf in timeframes.items():
            try:
                if self.counter % 10 == 1:
                    self.log_message(f"Analyzing {name}...", symbol_short)
                
                df = self.get_real_time_data(symbol, tf)
                
                if len(df) < length:
                    color = f"ERROR: Only {len(df)} candles"
                    movement_percentage = 0.0
                else:
                    # Calculate current candle movement percentage
                    movement_percentage = self.calculate_movement_percentage(df)
                    
                    # Show last candle timestamp only every 10 executions
                    if self.counter % 10 == 1:
                        last_candle_time = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
                        self.log_message(f"  Current candle: {last_candle_time} | %: {movement_percentage:+.2f}%", symbol_short)
                    
                    color, diff = self.calculate_indicator_oo(df, symbol)
                
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
        """Generates trading signal based on 3 timeframes"""
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
        """Generates a general summary of all signals"""
        strong_buys = sum(1 for s in all_signals.values() if "STRONG_BUY" in s)
        strong_sells = sum(1 for s in all_signals.values() if "STRONG_SELL" in s)
        bullish = sum(1 for s in all_signals.values() if "BULLISH" in s)
        bearish = sum(1 for s in all_signals.values() if "BEARISH" in s)
        
        summary = f"📈 BUYS: {strong_buys} | 📉 SELLS: {strong_sells} | 🟢 BULLISH: {bullish} | 🔻 BEARISH: {bearish}"
        
        self.summary_label.config(text=summary)
        self.log_message(f"🎯 GENERAL SUMMARY: {summary}", 'INFO')

# ============= INITIALIZATION =============
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()