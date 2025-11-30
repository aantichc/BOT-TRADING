# Archivo: capital_manager.py - VERSIÓN CON RESET SIMPLE
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
        self.last_directions = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        
        # ✅ SISTEMA DE COOLDOWN
        self.cooldowns = {s: {tf: 0 for tf in TIMEFRAMES} for s in SYMBOLS}
        self.locked_weights = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        
        self.SYMBOLS = SYMBOLS
        self.first_rebalance_done = False
    
    def get_signals(self, symbol):
        """✅ OBTENER SEÑALES REALES (sin bloqueo)"""
        signals = {}
        
        for tf_name, tf in TIMEFRAMES.items():
            try:
                df = self.indicators.get_klines(symbol, tf)
                if not df.empty:
                    color, _ = self.indicators.calculate_oo(df)
                    signals[tf_name] = color
                else:
                    signals[tf_name] = "RED"
            except Exception as e:
                signals[tf_name] = "RED"
        
        return signals
    
    def get_signal_value(self, color):
        return {"RED": 0, "YELLOW": 1, "GREEN": 2}.get(color, 0)
    
    def get_direction(self, old_color, new_color):
        old_val = self.get_signal_value(old_color)
        new_val = self.get_signal_value(new_color)
        
        if new_val > old_val:
            return "POSITIVE"
        elif new_val < old_val:
            return "NEGATIVE"
        return "NEUTRAL"
    
    def timeframe_to_minutes(self, tf):
        return {"30m": 15, "1h": 30, "2h": 60}.get(tf, 15)
    
    def update_cooldowns(self):
        current_time = time.time()
        
        for symbol in self.SYMBOLS:
            for tf in TIMEFRAMES:
                if (self.cooldowns[symbol][tf] > 0 and 
                    current_time >= self.cooldowns[symbol][tf]):
                    # ✅ COOLDOWN TERMINADO
                    self.cooldowns[symbol][tf] = 0
                    self.locked_weights[symbol][tf] = None
                    
                    msg = f"⏰ COOLDOWN ENDED {symbol} {tf}"
                    if self.gui:
                        self.gui.log_trade(msg, 'BLUE')
    
    def start_cooldown(self, symbol, tf, current_signal):
        """✅ INICIAR COOLDOWN - BLOQUEAR PESO ACTUAL"""
        cooldown_minutes = self.timeframe_to_minutes(tf)
        self.cooldowns[symbol][tf] = time.time() + (cooldown_minutes * 60)
        
        # ✅ CALCULAR Y BLOQUEAR PESO ACTUAL
        weight_for_tf = self.calculate_weight_for_timeframe(current_signal, tf)
        self.locked_weights[symbol][tf] = weight_for_tf
        
        msg = f"⏰ COOLDOWN STARTED {symbol} {tf} - {cooldown_minutes} min - Peso bloqueado: {weight_for_tf:.2f}"
        if self.gui:
            self.gui.log_trade(msg, 'BLUE')
    
    def reset_cooldown(self, symbol, tf):
        """✅ RESET COOLDOWN - SOLO REINICIAR TEMPORIZADOR"""
        cooldown_minutes = self.timeframe_to_minutes(tf)
        self.cooldowns[symbol][tf] = time.time() + (cooldown_minutes * 60)
        
        # ✅ MANTENER EL MISMO PESO BLOQUEADO (no cambiar)
        current_locked_weight = self.locked_weights[symbol][tf]
        
        msg = f"🔄 COOLDOWN RESET {symbol} {tf} - {cooldown_minutes} min más - Peso mantiene: {current_locked_weight:.2f}"
        if self.gui:
            self.gui.log_trade(msg, 'YELLOW')
    
    def calculate_weight_for_timeframe(self, signal, tf):
        """✅ CALCULAR PESO PARA UN TIMEFRAME INDIVIDUAL"""
        w = TIMEFRAME_WEIGHTS[tf]
        if signal == "GREEN":
            return w
        elif signal == "YELLOW":
            return w * 0.5
        return 0.0
    
    def calculate_weight(self, signals):
        """✅ CALCULAR PESO TOTAL CON BLOQUEOS"""
        weight = 0.0
        
        for tf, color in signals.items():
            symbol = list(self.SYMBOLS)[0]  # Se ajusta en rebalance
            
            if (self.cooldowns.get(symbol, {}).get(tf, 0) > time.time() and
                self.locked_weights.get(symbol, {}).get(tf) is not None):
                # ✅ USAR PESO BLOQUEADO
                weight += self.locked_weights[symbol][tf]
            else:
                # ✅ USAR PESO NORMAL
                weight += self.calculate_weight_for_timeframe(color, tf)
        
        return weight
    
    def process_signal_changes(self, symbol, new_signals):
        """✅ PROCESAR CAMBIOS CON RESET DE COOLDOWN"""
        if not self.first_rebalance_done:
            return
            
        old_signals = self.last_signals.get(symbol, {})
        
        for tf, new_color in new_signals.items():
            old_color = old_signals.get(tf)
            
            if old_color is not None and new_color != old_color:
                # ✅ LOG DEL CAMBIO DE SEÑAL
                change_msg = f"🔄 {symbol} {tf}: {old_color} → {new_color}"
                if self.gui:
                    self.gui.log_trade(change_msg, 'BLUE')
                
                # ✅ VERIFICAR CAMBIO DE DIRECCIÓN
                current_direction = self.get_direction(old_color, new_color)
                last_direction = self.last_directions[symbol].get(tf)
                
                if (last_direction is not None and 
                    current_direction != "NEUTRAL" and 
                    current_direction != last_direction):
                    
                    # ✅ DETECTAR CAMBIO DE DIRECCIÓN
                    direction_msg = f"🔄 DIRECTION CHANGE {symbol} {tf}: {last_direction} → {current_direction}"
                    if self.gui:
                        self.gui.log_trade(direction_msg, 'YELLOW')
                    
                    # ✅ VERIFICAR SI HAY COOLDOWN ACTIVO
                    if self.cooldowns[symbol][tf] > time.time():
                        # ✅ COOLDOWN ACTIVO - SOLO RESETEAR TEMPORIZADOR
                        self.reset_cooldown(symbol, tf)
                    else:
                        # ✅ NO HAY COOLDOWN - INICIAR NUEVO
                        self.start_cooldown(symbol, tf, new_color)
                
                self.last_directions[symbol][tf] = current_direction
        
        self.last_signals[symbol] = new_signals

    def rebalance(self, manual=False):
        self.update_cooldowns()
        
        total_usd = self.account.get_balance_usdc()
        if total_usd <= 0:
            return "No capital"
        
        actions = []
        force_initial_rebalance = not self.first_rebalance_done
        
        for symbol in SYMBOLS:
            # ✅ OBTENER SEÑALES REALES
            signals = self.get_signals(symbol)
            
            # ✅ PROCESAR CAMBIOS (puede activar/resetear cooldowns)
            self.process_signal_changes(symbol, signals)
            
            # ✅ CALCULAR PESO (con bloqueos aplicados)
            weight = self.calculate_weight(signals)
            
            # ✅ LOG DE BLOQUEOS ACTIVOS
            active_cooldowns = []
            for tf in TIMEFRAMES:
                if self.cooldowns[symbol][tf] > time.time():
                    locked_weight = self.locked_weights[symbol][tf]
                    remaining = int((self.cooldowns[symbol][tf] - time.time()) / 60)
                    active_cooldowns.append(f"{tf}({locked_weight:.2f})[{remaining}m]")
            
            if active_cooldowns:
                lock_msg = f"🔒 {symbol} Cooldowns: {', '.join(active_cooldowns)}"
                if self.gui:
                    self.gui.log_trade(lock_msg, 'BLUE')
            
            old_weight = self.last_weights.get(symbol, 0.0)
            signal_changed = abs(weight - old_weight) > 0.001
            
            if force_initial_rebalance or signal_changed or manual:
                if (signal_changed and not manual) or force_initial_rebalance:
                    change_detail = f" [Cooldowns: {', '.join(active_cooldowns)}]" if active_cooldowns else ""
                    
                    if force_initial_rebalance:
                        signal_change_msg = f"🎯 INITIAL REBALANCE {symbol}: Weight {weight:.2f}{change_detail}"
                    else:
                        direction = "📈" if weight > old_weight else "📉"
                        signal_change_msg = f"{symbol}: {direction} {old_weight:.2f} → {weight:.2f}{change_detail}"
                    
                    actions.append(signal_change_msg)
                    if self.gui:
                        self.gui.log_trade(signal_change_msg)
                
                # ✅ LÓGICA DE TRADING NORMAL...
                target_usd = total_usd * self.base_allocation * min(1.0, weight)
                current_balance = self.account.get_symbol_balance(symbol)
                price = self.account.get_current_price(symbol)
                current_usd = current_balance * price
                diff_usd = target_usd - current_usd
                
                if abs(diff_usd) > MIN_TRADE_DIFF:
                    if diff_usd > 0:
                        available_usdc = self.account.get_available_usdc()
                        if available_usdc < diff_usd:
                            diff_usd = available_usdc
                        if diff_usd > MIN_TRADE_DIFF:
                            success, msg = self.account.buy_market(symbol, diff_usd)
                            if success and self.gui:
                                self.gui.force_token_update(symbol)
                    else:
                        quantity = abs(diff_usd) / price
                        success, msg = self.account.sell_market(symbol, quantity)
                        if success and self.gui:
                            self.gui.force_token_update(symbol)
            
            self.last_weights[symbol] = weight
        
        if not self.first_rebalance_done:
            self.first_rebalance_done = True
            completion_msg = "✅ Initial Rebalance Completed"
            actions.append(completion_msg)
            if self.gui:
                self.gui.log_trade(completion_msg, 'GREEN')
        
        return actions if actions else "No ajustes necesarios"