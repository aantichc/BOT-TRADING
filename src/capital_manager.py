# Archivo: capital_manager.py - VERSIÓN CON SISTEMA DE COOLDOWN
from config import TIMEFRAMES, SYMBOLS, TIMEFRAME_WEIGHTS, MIN_TRADE_DIFF
from datetime import datetime
import time

class CapitalManager:
    def __init__(self, account, indicators, gui=None):
        self.account = account
        self.indicators = indicators
        self.gui = gui
        self.base_allocation = 1.0 / len(SYMBOLS)
        self.last_weights = {s: 0.0 for s in SYMBOLS}
        self.last_signals = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        self.last_changes = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        self.cooldowns = {s: {tf: 0 for tf in TIMEFRAMES} for s in SYMBOLS}  # ✅ NUEVO: Sistema de cooldown
        self.SYMBOLS = SYMBOLS
        self.first_rebalance_done = False
    
    def get_signals(self, symbol):
        """✅ OBTENER SEÑALES OO - CORAZÓN DEL SISTEMA DE TRADING"""
        signals = {}
        
        for tf_name, tf in TIMEFRAMES.items():
            try:
                # 1. OBTENER DATOS DE PRECIO
                df = self.indicators.get_klines(symbol, tf)
                
                if not df.empty:
                    # 2. CALCULAR SEÑAL OO (Ordenamiento Ondeulante)
                    color, _ = self.indicators.calculate_oo(df)
                    signals[tf_name] = color
                else:
                    signals[tf_name] = "RED"
                    
            except Exception as e:
                signals[tf_name] = "RED"
        
        return signals
    
    def get_signal_value(self, color):
        """✅ ASIGNAR VALOR NUMÉRICO A LAS SEÑALES PARA COMPARAR DIRECCIÓN"""
        if color == "RED":
            return 0
        elif color == "YELLOW":
            return 1
        elif color == "GREEN":
            return 2
        return 0
    
    def get_change_direction(self, old_color, new_color):
        """✅ DETERMINAR DIRECCIÓN DEL CAMBIO (POSITIVA O NEGATIVA)"""
        old_val = self.get_signal_value(old_color)
        new_val = self.get_signal_value(new_color)
        
        if new_val > old_val:
            return "POSITIVE"  # Mejora: RED→YELLOW, RED→GREEN, YELLOW→GREEN
        elif new_val < old_val:
            return "NEGATIVE"  # Empeora: GREEN→YELLOW, GREEN→RED, YELLOW→RED
        else:
            return "NEUTRAL"   # Sin cambio
    
    def timeframe_to_minutes(self, tf):
        """✅ CONVERTIR TIMEFRAME A MINUTOS PARA CALCULAR COOLDOWN"""
        if tf == "30m":
            return 30
        elif tf == "1h":
            return 60
        elif tf == "2h":
            return 120
        return 30  # Por defecto
    
    def update_cooldowns(self):
        """✅ ACTUALIZAR Y VERIFICAR COOLDOWNS ACTIVOS"""
        current_time = time.time()
        
        for symbol in self.SYMBOLS:
            for tf in TIMEFRAMES:
                cooldown_end = self.cooldowns[symbol][tf]
                if cooldown_end > 0:
                    if current_time >= cooldown_end:
                        # ✅ COOLDOWN TERMINADO
                        self.cooldowns[symbol][tf] = 0
                        end_msg = f"⏰ COOLDOWN ENDED {symbol} {tf}"
                        if self.gui:
                            self.gui.log_trade(end_msg, 'BLUE')
                        else:
                            print(end_msg)
    
    def start_cooldown(self, symbol, tf):
        """✅ INICIAR COOLDOWN PARA UN TIMEFRAME ESPECÍFICO"""
        cooldown_minutes = self.timeframe_to_minutes(tf) // 2
        cooldown_seconds = cooldown_minutes * 60
        self.cooldowns[symbol][tf] = time.time() + cooldown_seconds
        
        start_msg = f"⏰ COOLDOWN STARTED {symbol} {tf} - {cooldown_minutes} minutes"
        if self.gui:
            self.gui.log_trade(start_msg, 'BLUE')
        else:
            print(start_msg)
    
    def reset_cooldown(self, symbol, tf):
        """✅ RESETEAR COOLDOWN EXISTENTE"""
        cooldown_minutes = self.timeframe_to_minutes(tf) // 2
        cooldown_seconds = cooldown_minutes * 60
        self.cooldowns[symbol][tf] = time.time() + cooldown_seconds
        
        reset_msg = f"🔄 COOLDOWN RESET {symbol} {tf} - Direction change during active cooldown"
        if self.gui:
            self.gui.log_trade(reset_msg, 'YELLOW')
        else:
            print(reset_msg)
    
    def is_cooldown_active(self, symbol, tf):
        """✅ VERIFICAR SI HAY COOLDOWN ACTIVO"""
        return self.cooldowns[symbol][tf] > 0
    
    def log_signal_changes(self, symbol, new_signals):
        """✅ REGISTRA CAMBIOS DE SEÑAL Y DETECTA CAMBIOS DE DIRECCIÓN"""
        if not self.first_rebalance_done:
            return
            
        old_signals = self.last_signals.get(symbol, {})
        
        for tf, new_color in new_signals.items():
            old_color = old_signals.get(tf)
            
            # ✅ SOLO REGISTRAR SI EL COLOR CAMBIA
            if old_color is not None and new_color != old_color:
                # ✅ 1. LOG NORMAL DEL CAMBIO (AZUL)
                change_msg = f"🔄 {symbol} {tf}: {old_color} → {new_color}"
                if self.gui:
                    self.gui.log_trade(change_msg, 'BLUE')
                else:
                    print(change_msg)
                
                # ✅ 2. DETECTAR CAMBIO DE DIRECCIÓN (AMARILLO)
                current_direction = self.get_change_direction(old_color, new_color)
                last_direction = self.last_changes[symbol].get(tf)
                
                # ✅ VERIFICAR SI HAY CAMBIO DE DIRECCIÓN
                if (last_direction is not None and 
                    current_direction != "NEUTRAL" and 
                    current_direction != last_direction):
                    
                    direction_msg = f"🔄 DIRECTION CHANGE {symbol} {tf}: {last_direction} → {current_direction}"
                    if self.gui:
                        self.gui.log_trade(direction_msg, 'YELLOW')
                    else:
                        print(direction_msg)
                    
                    # ✅ 3. MANEJO DE COOLDOWN
                    if self.is_cooldown_active(symbol, tf):
                        # ✅ COOLDOWN ACTIVO - RESETEAR
                        self.reset_cooldown(symbol, tf)
                    else:
                        # ✅ NO HAY COOLDOWN - INICIAR UNO NUEVO
                        self.start_cooldown(symbol, tf)
                
                # ✅ ACTUALIZAR ÚLTIMA DIRECCIÓN REGISTRADA
                self.last_changes[symbol][tf] = current_direction
        
        # ✅ ACTUALIZAR SEÑALES ANTERIORES
        self.last_signals[symbol] = new_signals

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
        # ✅ ACTUALIZAR COOLDOWNS AL INICIO DE CADA REBALANCE
        self.update_cooldowns()
        
        total_usd = self.account.get_balance_usdc()
        if total_usd <= 0:
            return "No capital"
        
        actions = []
        force_initial_rebalance = not self.first_rebalance_done
        
        for symbol in SYMBOLS:
            signals = self.get_signals(symbol)
            
            # ✅ REGISTRAR CAMBIOS DE SEÑAL Y DETECTAR CAMBIOS DE DIRECCIÓN
            self.log_signal_changes(symbol, signals)
            
            weight = self.calculate_weight(signals)
            
            old_weight = self.last_weights.get(symbol, 0.0)
            signal_changed = self.has_changed(symbol, weight)
            
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
                        available_usdc = self.account.get_available_usdc()
                        
                        if available_usdc < diff_usd:
                            original_diff = diff_usd
                            diff_usd = available_usdc
                            
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
                                continue
                        
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
        
        if not self.first_rebalance_done:
            self.first_rebalance_done = True
            completion_msg = "✅ Initial Rebalance Completed"
            actions.append(completion_msg)
            if self.gui:
                self.gui.log_trade(completion_msg, 'GREEN')
        
        return actions if actions else "No ajustes necesarios"