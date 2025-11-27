# Archivo: capital_manager.py - VERSIÓN CON COOLDOWN DINÁMICO 3-5-10 (LÓGICA CORREGIDA)
from config import TIMEFRAMES, SYMBOLS, TIMEFRAME_WEIGHTS, MIN_TRADE_DIFF
from datetime import datetime
import time
import pandas as pd

class CapitalManager:
    def __init__(self, account, indicators, gui=None):
        self.account = account
        self.indicators = indicators
        self.gui = gui
        self.base_allocation = 1.0 / len(SYMBOLS)
        self.last_weights = {s: 0.0 for s in SYMBOLS}
        self.SYMBOLS = SYMBOLS
        self.first_rebalance_done = False
        self.signal_cooldowns = {}
        
        # ✅ SISTEMA DE BASELINES DINÁMICO
        self.volatility_baselines = {}
        self.volume_baselines = {}
        self.baseline_period = 30  # días para calcular baseline
        self.initialize_baselines()  # Calcular al iniciar
        
    def initialize_baselines(self):
        """Calcular baselines para todos los símbolos al iniciar"""
        print("📊 Calculando baselines históricas...")
        for symbol in self.SYMBOLS:
            self.calculate_baselines(symbol)
    
    def calculate_baselines(self, symbol):
        """Calcula líneas base históricas de volatilidad y volumen"""
        try:
            # Usar timeframe 1D para baselines históricas
            df = self.indicators.get_klines(symbol, "1d")
            if len(df) < self.baseline_period:
                print(f"⚠️ Datos insuficientes para baseline {symbol}")
                # Valores por defecto basados en tipo de activo
                if "BTC" in symbol or "ETH" in symbol:
                    self.volatility_baselines[symbol] = 2.5  # Bluechips menos volátiles
                else:
                    self.volatility_baselines[symbol] = 4.0  # Altcoins más volátiles
                self.volume_baselines[symbol] = 0.0
                return
            
            # VOLATILIDAD BASELINE (ATR porcentual promedio 30 días)
            high_low = df['high'] - df['low']
            high_close_prev = abs(df['high'] - df['close'].shift())
            low_close_prev = abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean()
            
            # ATR como porcentaje del precio
            atr_percentages = (atr / df['close']) * 100
            volatility_baseline = atr_percentages.tail(30).mean()  # Últimos 30 días
            
            # VOLUME BASELINE (volumen promedio 30 días)
            volume_baseline = df['volume'].tail(30).mean()
            
            self.volatility_baselines[symbol] = volatility_baseline
            self.volume_baselines[symbol] = volume_baseline
            
            print(f"📊 Baseline {symbol}: Vol={volatility_baseline:.2f}%")
            
        except Exception as e:
            print(f"❌ Error calculando baseline {symbol}: {e}")
            # Valores por defecto
            self.volatility_baselines[symbol] = 3.5
            self.volume_baselines[symbol] = 0.0
    
    def calculate_current_volatility(self, symbol, timeframe='30m'):
        """Calcula volatilidad actual usando ATR porcentual"""
        try:
            df = self.indicators.get_klines(symbol, timeframe)
            if len(df) < 14:
                return 0.0
            
            # True Range
            high_low = df['high'] - df['low']
            high_close_prev = abs(df['high'] - df['close'].shift())
            low_close_prev = abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
            
            # ATR (14 periodos)
            atr = true_range.rolling(14).mean().iloc[-1]
            
            # ATR como porcentaje del precio actual
            current_price = self.account.get_current_price(symbol)
            if current_price > 0:
                atr_percentage = (atr / current_price) * 100
                return atr_percentage
            return 0.0
            
        except Exception as e:
            return 0.0

    def get_current_volume_ratio(self, symbol, timeframe='30m'):
        """Ratio volumen actual vs volumen promedio histórico"""
        try:
            df = self.indicators.get_klines(symbol, timeframe)
            if len(df) < 20:
                return 1.0
            
            current_volume = df['volume'].iloc[-1]
            avg_volume_20 = df['volume'].tail(20).mean()
            
            if avg_volume_20 > 0:
                return current_volume / avg_volume_20
            return 1.0
            
        except:
            return 1.0
    
    def get_dynamic_cooldown_3_5_10(self, symbol):
        """🎯 COOLDOWN 3-5-10 BASADO EN CONDICIONES RELATIVAS"""
        current_volatility = self.calculate_current_volatility(symbol)
        volume_ratio = self.get_current_volume_ratio(symbol)
        
        # Obtener baseline de este símbolo
        baseline_vol = self.volatility_baselines.get(symbol, 3.5)
        
        # Calcular ratio vs su histórico
        vol_ratio = current_volatility / baseline_vol if baseline_vol > 0 else 1.0
        
        # 🎯 LÓGICA 3-5-10
        if vol_ratio > 1.3 and volume_ratio > 1.5:
            # 🔴 ALTA VOLATILIDAD + ALTO VOLUMEN = Mercado moviéndose con convicción
            return 3  # minutos - COOLDOWN CORTO (aprovechar tendencias)
        
        elif vol_ratio < 0.7 and volume_ratio < 0.8:
            # 🟢 BAJA VOLATILIDAD + BAJO VOLUMEN = Mercado lateral/aburrido
            return 10 # minutos - COOLDOWN LARGO (evitar overtrading por ruido)
        
        else:
            # 🟡 CONDICIÓN MIXTA/NORMAL
            return 5  # minutos - COOLDOWN BALANCEADO
        
    def should_allow_signal_change(self, symbol, timeframe, new_signal):
        key = (symbol, timeframe)
        current_time = time.time()
        
        if key not in self.signal_cooldowns:
            # ✅ COOLDOWN DINÁMICO INICIAL
            dynamic_cooldown = self.get_dynamic_cooldown_3_5_10(symbol)
            self.signal_cooldowns[key] = {
                'last_signal': new_signal,
                'last_change': current_time,
                'original_signal': new_signal,  # ← ESTADO QUE INICIÓ COOLDOWN
                'cooldown_minutes': dynamic_cooldown,
                'change_count': 1
            }
            return True
        
        cooldown_data = self.signal_cooldowns[key]
        last_signal = cooldown_data['last_signal']
        last_change = cooldown_data['last_change']
        current_cooldown = cooldown_data['cooldown_minutes']
        original_signal = cooldown_data['original_signal']  # ← ESTADO ORIGINAL
        
        # Verificar si pasó cooldown
        time_since_change = current_time - last_change
        cooldown_seconds = current_cooldown * 60
        
        if time_since_change >= cooldown_seconds:
            # ✅ RECALCULAR COOLDOWN DINÁMICO (puede haber cambiado)
            new_cooldown = self.get_dynamic_cooldown_3_5_10(symbol)
            cooldown_data.update({
                'last_signal': new_signal,
                'last_change': current_time,
                'original_signal': new_signal,  # ← NUEVO ESTADO ORIGINAL
                'cooldown_minutes': new_cooldown,
                'change_count': 1
            })
            return True
        
        # 🔄 DURANTE COOLDOWN - LÓGICA CORREGIDA (OPCIÓN B)
        is_returning_to_original = (new_signal == original_signal)
        
        if not is_returning_to_original:
            # ✅ PERMITIR cualquier cambio a estado DIFERENTE del original
            cooldown_data['last_signal'] = new_signal
            cooldown_data['change_count'] += 1
            return True
        else:
            # 🚫 BLOQUEAR volver al estado ORIGINAL del cooldown
            remaining = cooldown_seconds - time_since_change
            print(f"🚫 Cooldown {symbol} {timeframe}: {last_signal}→{new_signal} "
                  f"({current_cooldown}min, restante: {remaining:.0f}s)")
            return False
     
    def get_signals(self, symbol):
        """✅ OBTENER SEÑALES OO CON COOLDOWN INTELIGENTE"""
        signals = {}
        
        for tf_name, tf in TIMEFRAMES.items():
            try:
                # 1. OBTENER DATOS DE PRECIO
                df = self.indicators.get_klines(symbol, tf)
                
                if not df.empty:
                    # 2. CALCULAR SEÑAL OO
                    color, _ = self.indicators.calculate_oo(df)
                    
                    # 3. ✅ APLICAR COOLDOWN INTELIGENTE
                    if not self.should_allow_signal_change(symbol, tf_name, color):
                        signals[tf_name] = "YELLOW"  # Señal neutral durante cooldown
                    else:
                        signals[tf_name] = color
                else:
                    signals[tf_name] = "RED"
                    
            except Exception as e:
                signals[tf_name] = "RED"
        
        return signals
    
    def calculate_weight(self, signals):
        weight = 0.0
        for tf, color in signals.items():
            w = TIMEFRAME_WEIGHTS[tf]
            if color == "GREEN":
                weight += w
            elif color == "YELLOW":
                weight += w * 0.5
        return weight
    
    def has_changed(self, symbol, new_weight):
        old = self.last_weights[symbol]
        changed = abs(new_weight - old) > 0.0
        self.last_weights[symbol] = new_weight
        return changed

    def rebalance(self, manual=False):
        total_usd = self.account.get_balance_usdc()
        if total_usd <= 0:
            return "No capital"
        
        actions = []
        
        # ✅ FORZAR REBALANCE EN PRIMERA EJECUCIÓN AUNQUE NO HAYA CAMBIO DE SEÑAL
        force_initial_rebalance = not self.first_rebalance_done
        
        for symbol in SYMBOLS:
            signals = self.get_signals(symbol)
            weight = self.calculate_weight(signals)
            
            # ✅ EVITAR LOGS DE INICIALIZACIÓN
            old_weight = self.last_weights.get(symbol, 0.0)
            signal_changed = self.has_changed(symbol, weight)
            
            # ✅ EN PRIMERA EJECUCIÓN, EJECUTAR REBALANCE COMPLETO
            if force_initial_rebalance or signal_changed or manual:
                if (signal_changed and not manual) or force_initial_rebalance:
                    if force_initial_rebalance:
                        signal_change_msg = f"🎯 INITIAL REBALANCE {symbol}: Weight {weight:.2f}"
                    else:
                        direction = "📈" if weight > old_weight else "📉"
                        signal_change_msg = f"{symbol}: {direction} {old_weight:.2f} → {weight:.2f}"
                    
                    actions.append(signal_change_msg)
                    if self.gui:
                        self.gui.log_trade(signal_change_msg)
                
                target_usd = total_usd * self.base_allocation * min(1.0, weight)
                current_balance = self.account.get_symbol_balance(symbol)
                price = self.account.get_current_price(symbol)
                current_usd = current_balance * price
                diff_usd = target_usd - current_usd
                
                if abs(diff_usd) > MIN_TRADE_DIFF:
                    if diff_usd > 0:
                        # ✅ COMPRA - VERIFICAR CAPITAL DISPONIBLE ANTES
                        available_usdc = self.account.get_available_usdc()
                        
                        # ✅ SI NO HAY SUFICIENTE CAPITAL, AJUSTAR AL DISPONIBLE
                        if available_usdc < diff_usd:
                            original_diff = diff_usd
                            diff_usd = available_usdc
                            
                            # ✅ SOLO COMPRAR SI EL MONTO AJUSTADO ES SUFICIENTE
                            if diff_usd > MIN_TRADE_DIFF:
                                msg = f"💰 CAPITAL LIMITADO: Comprando {symbol} con ${diff_usd:.2f} (de ${original_diff:.2f} objetivo)"
                                actions.append(msg)
                                if self.gui:
                                    self.gui.log_trade(msg, 'YELLOW')
                            else:
                                msg = f"❌ CAPITAL INSUFICIENTE: Necesita ${original_diff:.2f}, disponible ${available_usdc:.2f}"
                                actions.append(msg)
                                if self.gui:
                                    self.gui.log_trade(msg, 'RED')
                                continue  # Saltar esta compra
                        
                        # ✅ EJECUTAR COMPRA CON MONTO AJUSTADO
                        success, msg = self.account.buy_market(symbol, diff_usd)
                        if success:
                            if self.gui:
                                self.gui.force_token_update(symbol)
                        else:
                            error_msg = f"❌ ERROR COMPRA {symbol}: {msg}"
                            actions.append(error_msg)
                            if self.gui:
                                self.gui.log_trade(error_msg, 'RED')
                    else:
                        # VENTA
                        quantity = abs(diff_usd) / price
                        success, msg = self.account.sell_market(symbol, quantity)
                        if success:
                            if self.gui:
                                self.gui.force_token_update(symbol)
                        else:
                            error_msg = f"❌ ERROR VENTA {symbol}: {msg}"
                            actions.append(error_msg)
                            if self.gui:
                                self.gui.log_trade(error_msg, 'RED')
        
        # ✅ MARCAR QUE EL PRIMER REBALANCE SE HA COMPLETADO
        if not self.first_rebalance_done:
            self.first_rebalance_done = True
            completion_msg = "✅ Initial Rebalance Completed"
            actions.append(completion_msg)
            if self.gui:
                self.gui.log_trade(completion_msg, 'GREEN')
        
        return actions if actions else "No ajustes necesarios"

    def weight_to_signal(self, weight):
        """Convierte peso numérico a texto de señal"""
        if weight >= 0.8:
            return "STRONG_BUY"
        elif weight >= 0.5:
            return "BUY"
        elif weight >= 0.3:
            return "SELL"
        else:
            return "STRONG_SELL"