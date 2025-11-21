import threading
import time
import concurrent.futures
from datetime import datetime, timedelta
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
import numpy as np

from config import *
from indicators import HeikinAshiCalculator, TradingIndicator
from capital_manager import CapitalManager

class TradingBot:
    def __init__(self, gui_instance):
        self.gui = gui_instance  # Instancia de la GUI (puede ser None inicialmente)
        self.capital_manager = CapitalManager(gui_instance)  # Nuevo gestor de capital
        self.initialize_variables()
        # ✅ NUEVO: Cache optimizado
        self.setup_optimized_cache()
    
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
        self.candle_cache = {}  # Cache de velas
        self.current_analysis = {}  # Para almacenar análisis recientes

    def setup_optimized_cache(self):
        """Configura cache más agresivo para modo test"""
        self.cache_timeout = 300 if not TRADING_ENABLED else 30  # 5min test, 30s live
        self.bulk_price_cache = {'data': None, 'timestamp': 0}
        self.symbol_info_cache = {}
        self.analysis_cache = {}

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

    def get_all_prices_bulk_optimized(self):
        """Versión optimizada con cache de precios"""
        try:
            current_time = time.time()
            
            # ✅ Cache de 10 segundos para precios (suficiente para trading)
            if (self.bulk_price_cache['timestamp'] and 
                current_time - self.bulk_price_cache['timestamp'] < 10):
                return self.bulk_price_cache['data']
            
            if self.client is None:
                return {}
            
            tickers = self.client.get_all_tickers()
            price_dict = {}
            for ticker in tickers:
                if ticker['symbol'] in SYMBOLS:
                    price_dict[ticker['symbol']] = float(ticker['price'])
            
            # Actualizar cache
            self.bulk_price_cache = {
                'data': price_dict, 
                'timestamp': current_time
            }
            
            return price_dict
            
        except Exception as e:
            self.log_message(f"❌ Error obteniendo precios bulk: {str(e)}", 'ERROR')
            # Retornar cache viejo si hay error
            return self.bulk_price_cache.get('data', {})

    def debug_timing_breakdown(self):
        """Identifica qué parte consume más tiempo"""
        import time
        
        timing_data = {}
        
        # 1. Timing de obtener precios
        start = time.time()
        all_prices = self.get_all_prices_bulk_optimized()
        timing_data['precios_bulk'] = time.time() - start
        
        # 2. Timing de análisis por símbolo
        for symbol in SYMBOLS[:2]:  # Probar con 2 símbolos
            start = time.time()
            results, progresses, percentages = self.analyze_symbol_optimized(symbol)
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
            if not TRADING_ENABLED:
                self.log_message("🔒 MODO TEST - Operaciones bloqueadas", 'TEST_MODE')
            
            # Start bot loop in separate thread
            self.bot_thread = threading.Thread(target=self.run_bot_precise_timing_optimized, daemon=True)
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

    def analyze_all_symbols_parallel(self):
        """Analiza símbolos en paralelo - OPTIMIZADO"""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {
                    executor.submit(self.analyze_symbol_optimized, symbol): symbol 
                    for symbol in SYMBOLS
                }
                
                all_results, all_progresses, all_percentages = {}, {}, {}
                for future in concurrent.futures.as_completed(futures):
                    symbol = futures[future]
                    try:
                        results, progresses, percentages = future.result(timeout=10)  # Timeout de seguridad
                        all_results[symbol] = results
                        all_progresses[symbol] = progresses
                        all_percentages[symbol] = percentages
                    except concurrent.futures.TimeoutError:
                        self.log_message(f"⏰ Timeout analizando {symbol}", 'WARNING')
                        all_results[symbol] = {tf: "TIMEOUT" for tf in TIMEFRAMES.keys()}
                        all_progresses[symbol] = {tf: "N/A" for tf in TIMEFRAMES.keys()}
                        all_percentages[symbol] = {tf: 0.0 for tf in TIMEFRAMES.keys()}
                    except Exception as e:
                        self.log_message(f"❌ Error analizando {symbol}: {str(e)}", 'ERROR')
                        all_results[symbol] = {tf: "ERROR" for tf in TIMEFRAMES.keys()}
                        all_progresses[symbol] = {tf: "N/A" for tf in TIMEFRAMES.keys()}
                        all_percentages[symbol] = {tf: 0.0 for tf in TIMEFRAMES.keys()}
            
            return all_results, all_progresses, all_percentages
            
        except Exception as e:
            self.log_message(f"❌ Error en análisis paralelo: {str(e)}", 'ERROR')
            return {}, {}, {}

    def analyze_symbol_optimized(self, symbol):
        """Versión optimizada del análisis - CON CACHE"""
        symbol_short = symbol.replace('USDC', '')
        
        # ✅ Cache de análisis por 30 segundos (velas no cambian tan rápido)
        cache_key = f"analysis_{symbol}"
        current_time = time.time()
        
        if (cache_key in self.analysis_cache and 
            current_time - self.analysis_cache[cache_key]['timestamp'] < 30):
            cached = self.analysis_cache[cache_key]
            return cached['results'], cached['progresses'], cached['percentages']
        
        # Análisis normal (código existente)
        results, progresses, percentages = self.analyze_symbol(symbol)
        
        # Guardar en cache
        self.analysis_cache[cache_key] = {
            'results': results,
            'progresses': progresses, 
            'percentages': percentages,
            'timestamp': current_time
        }
        
        return results, progresses, percentages

    def run_bot_precise_timing_optimized(self):
        """Bucle principal OPTIMIZADO - VERSIÓN URGENTE"""
        # ✅ RESETEO INICIAL
        self.next_update_time = datetime.now() + timedelta(seconds=UPDATE_INTERVAL)
        
        while self.running:
            try:
                current_time = datetime.now()
                
                if current_time >= self.next_update_time:
                    execution_start = datetime.now()
                    self.counter += 1
                    
                    # ✅ CALCULAR PRÓXIMO UPDATE ANTES DE EJECUTAR
                    self.next_update_time = execution_start + timedelta(seconds=UPDATE_INTERVAL)
                    
                    # Update interface header inmediatamente
                    if self.gui:
                        self.gui.root.after(0, self.gui.update_display_header)
                    
                    # Log reducido en modo test
                    if self.counter % 20 == 1:  # Cada 20 ejecuciones en test
                        self.log_message(f"\n{'='*80}", 'INFO')
                        self.log_message(f"🔄 EXECUTION #{self.counter} - {execution_start.strftime('%H:%M:%S.%f')[:-3]}", 'INFO')
                        if not TRADING_ENABLED:
                            self.log_message("🔒 MODO TEST - Operaciones bloqueadas", 'TEST_MODE')
                    
                    # ✅ DEBUG EXTREMO - IDENTIFICAR CUELOS DE BOTELLA
                    debug_start = time.time()
                    
                    # 1. Timing de precios
                    price_start = time.time()
                    all_prices = self.get_all_prices_bulk_optimized()
                    price_time = time.time() - price_start
                    
                    # 2. Timing de análisis
                    analysis_start = time.time()
                    all_results, all_progresses, all_signals = {}, {}, {}
                    all_percentages = {}
                    
                    if len(SYMBOLS) > 2:  # Solo paralelizar si hay suficientes símbolos
                        all_results, all_progresses, all_percentages = self.analyze_all_symbols_parallel()
                    else:
                        # Análisis secuencial para pocos símbolos
                        for symbol in SYMBOLS:
                            results, progresses, percentages = self.analyze_symbol_optimized(symbol)
                            signal = self.generate_trading_signal(results, symbol)
                            
                            all_results[symbol] = results
                            all_progresses[symbol] = progresses
                            all_signals[symbol] = signal
                            all_percentages[symbol] = percentages
                    
                    # Generar señales para símbolos analizados en paralelo
                    for symbol in SYMBOLS:
                        if symbol not in all_signals:  # Si no se generó en paralelo
                            all_signals[symbol] = self.generate_trading_signal(all_results.get(symbol, {}), symbol)
                    
                    analysis_time = time.time() - analysis_start
                    
                    # Guardar análisis actual para uso externo
                    self.current_analysis = all_results
                    
                    # 3. Timing de GUI
                    gui_start = time.time()
                    # Update results in interface
                    if self.gui:
                        self.gui.root.after(0, lambda: self.gui.update_all_results(
                            all_results, all_progresses, all_signals, all_prices, all_percentages
                        ))
                    gui_time = time.time() - gui_start
                    
                    # Mostrar breakdown de timing
                    if self.counter % 10 == 1:
                        total_time = time.time() - debug_start
                        self.log_message(f"🔍 DEBUG TIMING: Precios: {price_time:.2f}s, Análisis: {analysis_time:.2f}s, GUI: {gui_time:.2f}s, Total: {total_time:.2f}s", 'TIMING')
                    
                    # ✅ REBALANCEO SELECTIVO (solo si hay cambios significativos)
                    should_rebalance = (
                        self.counter % 5 == 0 or  # Cada 10 segundos
                        any(self.capital_manager.has_signal_changed(symbol, 
                             self.capital_manager.calculate_signal_weight(all_results.get(symbol, {})), 
                             0.15) for symbol in SYMBOLS)
                    )
                    
                    if should_rebalance:
                        rebalance_start = time.time()
                        success, message = self.capital_manager.rebalance_portfolio(all_results, all_prices)
                        rebalance_time = time.time() - rebalance_start
                        if success and "Rebalanceados" in message:
                            self.log_message(f"⚖️ {message} ({rebalance_time:.2f}s)", 'TRADE')
                    
                    # Mostrar estado cada 60 ejecuciones en test (cada ~2min)
                    if self.counter % 60 == 0 and not TRADING_ENABLED:
                        portfolio_status = self.capital_manager.get_portfolio_status()
                        self.log_message(f"📊 Estado Portfolio (TEST):\n{portfolio_status}", 'INFO')
                    
                    # ✅ TIMING URGENTE - ELIMINAR COMPENSACIÓN COMPLEJA
                    execution_end = datetime.now()
                    execution_time = (execution_end - execution_start).total_seconds()
                    self.execution_times.append(execution_time)
                    
                    # ✅ SLEEP SIMPLE Y EFECTIVO
                    sleep_time = max(0.1, UPDATE_INTERVAL - execution_time)
                    
                    # ✅ RESETEO AGRESIVO DE DRIFT
                    if execution_time > UPDATE_INTERVAL:
                        # Si la ejecución fue más larga que el intervalo, resetear
                        self.next_update_time = datetime.now() + timedelta(seconds=UPDATE_INTERVAL)
                        sleep_time = 0.1
                        self.log_message(f"🚨 OVERFLOW: Exec {execution_time:.2f}s > Interval {UPDATE_INTERVAL}s", 'ERROR')
                    
                    # Update timing display
                    if self.gui:
                        self.gui.root.after(0, lambda: self.gui.update_timing_display(
                            execution_time, sleep_time, 0.0  # Drift forzado a 0
                        ))
                    
                    # ✅ LOG CADA 10 EJECUCIONES
                    if self.counter % 10 == 1:
                        avg_time = sum(self.execution_times[-10:]) / min(10, len(self.execution_times))
                        self.log_message(f"⏱️ TIMING URGENTE: Exec: {execution_time:.2f}s, Avg: {avg_time:.2f}s, Sleep: {sleep_time:.2f}s", 'TIMING')
                    
                    # Sleep simple
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                
                else:
                    # Espera eficiente
                    time_until_next = (self.next_update_time - datetime.now()).total_seconds()
                    if time_until_next > 0.5:
                        time.sleep(0.1)
                    elif time_until_next > 0.05:
                        time.sleep(0.01)
                        
            except Exception as e:
                self.log_message(f"❌ Error in main loop: {str(e)}", 'ERROR')
                time.sleep(UPDATE_INTERVAL)

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
