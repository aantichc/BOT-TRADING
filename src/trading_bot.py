import threading
import time
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd

from config import *
from indicators import HeikinAshiCalculator, TradingIndicator
from capital_manager import CapitalManager

class TradingBot:
    def __init__(self, gui_instance):
        self.gui = gui_instance  # Instancia de la GUI (puede ser None inicialmente)
        self.capital_manager = CapitalManager(gui_instance)  # Nuevo gestor de capital
        self.initialize_variables()
    
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
        self.execution_times = []
        self.last_rebalance_time = None
        self.candle_cache = {}  # Nuevo: cache de velas
        self.cache_timeout = 30  # segundos

    def get_all_prices_bulk(self):
        """Obtiene todos los precios en una sola llamada a API"""
        try:
            if self.client is None:
                return {}
            
            tickers = self.client.get_all_tickers()
            price_dict = {}
            for ticker in tickers:
                if ticker['symbol'] in SYMBOLS:
                    price_dict[ticker['symbol']] = float(ticker['price'])
            return price_dict
        except Exception as e:
            self.log_message(f"❌ Error obteniendo precios bulk: {str(e)}", 'ERROR')
            return {}

    def debug_timing_breakdown(self):
        """Identifica qué parte consume más tiempo"""
        import time
        
        timing_data = {}
        
        # 1. Timing de obtener precios
        start = time.time()
        all_prices = self.get_all_prices_bulk()
        timing_data['precios_bulk'] = time.time() - start
        
        # 2. Timing de análisis por símbolo
        for symbol in SYMBOLS[:2]:  # Probar con 2 símbolos
            start = time.time()
            results, progresses, percentages = self.analyze_symbol(symbol)
            timing_data[f'analisis_{symbol}'] = time.time() - start
        
        # Mostrar resultados
        self.log_message("🔍 DIAGNÓSTICO TIMING:", 'INFO')
        for operation, duration in timing_data.items():
            self.log_message(f"   {operation}: {duration:.3f}s", 'INFO')
        
        return timing_data

    def get_cached_klines(self, symbol, timeframe):
        """Cachea velas para evitar llamadas repetidas a API"""
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self.candle_cache:
            cache_time, data = self.candle_cache[cache_key]
            if (datetime.now() - cache_time).seconds < self.cache_timeout:
                return data
        
        # Si no hay cache o expiró, obtener datos frescos
        fresh_data = self.get_real_time_data(symbol, timeframe)
        self.candle_cache[cache_key] = (datetime.now(), fresh_data)
        return fresh_data

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
        """Método de log que usa la GUI si está disponible"""
        if self.gui:
            self.gui.log_message(message, tag)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def start_bot(self):
        """Inicia el bot en un hilo separado"""
        if not self.running:
            # Configurar Binance client si no está configurado
            if self.client is None:
                self.setup_binance_client()
            
            # 🧪 EJECUTAR DIAGNÓSTICO ANTES DE INICIAR
            self.debug_timing_breakdown()
            
            self.running = True
            if self.gui:
                self.gui.update_bot_status(True)
            
            # Inicializar timing
            self.last_update_time = datetime.now()
            self.next_update_time = (self.last_update_time + timedelta(seconds=UPDATE_INTERVAL)).replace(microsecond=0)
            self.execution_times = []
            
            self.log_message(f"🤖 Bot started - Update interval: {UPDATE_INTERVAL}s", 'INFO')
            self.log_message("💰 Live prices + % movement by timeframe", 'INFO')
            self.log_message("⚖️ Capital management ENABLED - Rebalancing on signal changes", 'SUCCESS')
            
            # Start bot loop in separate thread
            self.bot_thread = threading.Thread(target=self.run_bot_precise_timing, daemon=True)
            self.bot_thread.start()
    
    def stop_bot(self):
        """Detiene el bot"""
        if self.running:
            self.running = False
            if self.gui:
                self.gui.update_bot_status(False, self.counter)
            
            # Mostrar estadísticas finales de timing
            if self.execution_times:
                avg_time = sum(self.execution_times) / len(self.execution_times)
                max_time = max(self.execution_times)
                min_time = min(self.execution_times)
                self.log_message(f"📊 FINAL TIMING STATS: Avg: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s", 'INFO')
            
            self.log_message(f"⏹️ Bot stopped. Total executions: {self.counter}", 'INFO')
    
    def run_bot_precise_timing(self):
        """Bucle principal del bot con timing preciso"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Solo ejecutar si es tiempo de actualizar (sincronizado con reloj)
                if current_time >= self.next_update_time:
                    execution_start = datetime.now()
                    self.counter += 1
                    
                    # Calcular tiempo de la próxima actualización
                    self.next_update_time = (execution_start + timedelta(seconds=UPDATE_INTERVAL)).replace(microsecond=0)
                    
                    # Update interface header inmediatamente
                    if self.gui:
                        self.gui.root.after(0, self.gui.update_display_header)
                    
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
                    
                    # Obtener TODOS los precios de una vez (más rápido)
                    all_prices = self.get_all_prices_bulk()
                    
                    for symbol in SYMBOLS:
                        # Only detailed log every 10 executions
                        if self.counter % 10 == 1:
                            self.log_message(f"\n🔍 Analyzing {symbol}...", symbol.replace('USDC', ''))
                        
                        current_price = all_prices.get(symbol, 0.0)
                        
                        results, progresses, percentages = self.analyze_symbol(symbol)
                        signal = self.generate_trading_signal(results, symbol)
                        
                        all_results[symbol] = results
                        all_progresses[symbol] = progresses
                        all_signals[symbol] = signal
                        all_percentages[symbol] = percentages
                    
                    # Update results in interface (ALWAYS)
                    if self.gui:
                        self.gui.root.after(0, lambda: self.gui.update_all_results(all_results, all_progresses, all_signals, all_prices, all_percentages))
                    
                    # Generate general summary (only log every 10 executions)
                    if self.counter % 10 == 1:
                        self.generate_general_summary(all_signals)
                    
                    # REBALANCE PORTFOLIO - ejecutar en cada ciclo para detectar cambios inmediatos
                    if self.counter % 3 == 0:  # Cada 6 segundos verificar cambios (ajustado por nuevo intervalo)
                        success, message = self.capital_manager.rebalance_portfolio(all_results, all_prices)
                        if success and "Rebalanceados" in message:
                            self.log_message(f"⚖️ {message}", 'TRADE')
                    
                    # Mostrar estado del portfolio cada 30 ejecuciones (ajustado)
                    if self.counter % 30 == 0:
                        portfolio_status = self.capital_manager.get_portfolio_status()
                        self.log_message(f"📊 Estado Portfolio:\n{portfolio_status}", 'INFO')
                    
                    # Calcular tiempo de ejecución y ajustar sleep
                    execution_end = datetime.now()
                    execution_time = (execution_end - execution_start).total_seconds()
                    self.execution_times.append(execution_time)
                    
                    # Calcular drift (cuánto nos pasamos del tiempo ideal)
                    actual_next_time = datetime.now()
                    drift = (actual_next_time - self.next_update_time).total_seconds()
                    
                    # Calcular sleep time dinámicamente
                    sleep_time = max(0.01, UPDATE_INTERVAL - execution_time - drift)
                    
                    # Actualizar display de timing
                    if self.gui:
                        self.gui.root.after(0, lambda: self.gui.update_timing_display(execution_time, sleep_time, drift))
                    
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
                    # Esperar hasta el próximo intervalo con polling eficiente
                    time_until_next = (self.next_update_time - datetime.now()).total_seconds()
                    if time_until_next > 0.1:
                        time.sleep(0.1)  # Poll cada 100ms
                    elif time_until_next > 0.01:
                        time.sleep(0.01)  # Poll cada 10ms cuando está cerca
                    # Si está muy cerca, continuar sin sleep
                        
            except Exception as e:
                self.log_message(f"❌ Error in main loop: {str(e)}", 'ERROR')
                time.sleep(UPDATE_INTERVAL)  # En caso de error, esperar intervalo completo

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
        symbol_short = symbol.replace('USDC', '')
        
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
                
                # Usar cache de velas para optimizar
                df = self.get_cached_klines(symbol, tf)
                
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
        
        symbol_short = symbol.replace('USDC', '')
        
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
        
        if self.gui:
            self.gui.summary_label.config(text=summary)
        self.log_message(f"🎯 GENERAL SUMMARY: {summary}", 'INFO')