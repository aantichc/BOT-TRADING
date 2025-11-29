# Archivo: capital_manager.py - VERSIÓN CORREGIDA
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
        self.cooldowns = {s: {tf: 0 for tf in TIMEFRAMES} for s in SYMBOLS}
        self.frozen_weights = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        self.cooldown_directions = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        self.cooldown_initial_signals = {s: {tf: None for tf in TIMEFRAMES} for s in SYMBOLS}
        self.SYMBOLS = SYMBOLS
        self.first_rebalance_done = False
        
        # ✅ Control de logs repetidos
        self._last_block_times = {}
        self._last_frozen_times = {}
    
    def get_signals(self, symbol):
        """✅ OBTENER SEÑALES OO - CORAZÓN DEL SISTEMA DE TRADING"""
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
            return "POSITIVE"
        elif new_val < old_val:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    def timeframe_to_minutes(self, tf):
        """✅ CONVERTIR TIMEFRAME A MINUTOS PARA CALCULAR COOLDOWN"""
        if tf == "30m":
            return 30
        elif tf == "1h":
            return 60
        elif tf == "2h":
            return 120
        return 30
    
    def update_cooldowns(self):
        """✅ ACTUALIZAR Y VERIFICAR COOLDOWNS ACTIVOS - SOLO UNA VEZ CUANDO EXPIRAN"""
        current_time = time.time()
        
        for symbol in self.SYMBOLS:
            for tf in TIMEFRAMES:
                cooldown_end = self.cooldowns[symbol][tf]
                if cooldown_end > 0 and current_time >= cooldown_end:
                    # ✅ LIMPIAR COOLDOWN CUANDO EXPIRA - VOLVER A LA NORMALIDAD
                    self.cooldowns[symbol][tf] = 0
                    self.frozen_weights[symbol][tf] = None
                    self.cooldown_directions[symbol][tf] = None
                    self.cooldown_initial_signals[symbol][tf] = None
                    
                    expired_msg = f"⏰ COOLDOWN ENDED {symbol} {tf} - Weights unfrozen"
                    if self.gui:
                        self.gui.log_trade(expired_msg, 'BLUE')
                    else:
                        print(expired_msg)
    
    def start_cooldown(self, symbol, tf, direction, initial_signal):
        """✅ INICIAR COOLDOWN PARA UN TIMEFRAME ESPECÍFICO"""
        cooldown_minutes = self.timeframe_to_minutes(tf) // 2
        cooldown_seconds = cooldown_minutes * 60
        self.cooldowns[symbol][tf] = time.time() + cooldown_seconds
        self.cooldown_directions[symbol][tf] = direction
        self.cooldown_initial_signals[symbol][tf] = initial_signal
        
        # ✅ CONGELAR PESO ACTUAL AL INICIAR COOLDOWN
        w = TIMEFRAME_WEIGHTS[tf]
        current_signal = self.last_signals[symbol].get(tf, "RED")
        if current_signal == "GREEN":
            frozen_weight = w
        elif current_signal == "YELLOW":
            frozen_weight = w * 0.5
        else:
            frozen_weight = 0.0
        self.frozen_weights[symbol][tf] = frozen_weight
        
        start_msg = f"⏰ COOLDOWN STARTED {symbol} {tf} - {cooldown_minutes} minutes (Direction: {direction}, Initial Signal: {initial_signal})"
        if self.gui:
            self.gui.log_trade(start_msg, 'BLUE')
        else:
            print(start_msg)
    
    def reset_cooldown(self, symbol, tf):
        """✅ RESETEA EL COOLDOWN CUANDO LA SEÑAL VUELVE AL ESTADO INICIAL"""
        # Reiniciar el cooldown a su tiempo máximo completo
        cooldown_minutes = self.timeframe_to_minutes(tf) // 2
        cooldown_seconds = cooldown_minutes * 60
        self.cooldowns[symbol][tf] = time.time() + cooldown_seconds
        
        reset_msg = f"🔄 COOLDOWN RESET {symbol} {tf} - Timer reset to {cooldown_minutes} minutes"
        if self.gui:
            self.gui.log_trade(reset_msg, 'GREEN')
        else:
            print(reset_msg)
    
    def is_cooldown_active(self, symbol, tf):
        """✅ VERIFICAR SI HAY COOLDOWN ACTIVO"""
        return self.cooldowns[symbol][tf] > 0
    
    def should_block_signal_change(self, symbol, tf, new_signal):
        """✅ VERIFICAR SI SE DEBE BLOQUEAR UN CAMBIO DE SEÑAL DURANTE COOLDOWN"""
        if not self.is_cooldown_active(symbol, tf):
            return False
        
        current_direction = self.cooldown_directions[symbol][tf]
        if current_direction is None:
            return False
        
        # ✅ OBTENER DIRECCIÓN DEL CAMBIO ACTUAL
        old_signal = self.last_signals[symbol].get(tf)
        if old_signal is None or old_signal == new_signal:
            return False
        
        change_direction = self.get_change_direction(old_signal, new_signal)
        
        # ✅ SOLO BLOQUEAR SI ES DIRECCIÓN OPUESTA AL COOLDOWN
        return change_direction != current_direction
    
    def check_cooldown_reset(self, symbol, tf, new_signal):
        """✅ VERIFICAR SI SE DEBE REINICIAR EL COOLDOWN POR VOLVER A LA SEÑAL INICIAL"""
        if not self.is_cooldown_active(symbol, tf):
            return False
        
        initial_signal = self.cooldown_initial_signals[symbol][tf]
        if initial_signal is None:
            return False
        
        # ✅ REINICIAR COOLDOWN SI LA NUEVA SEÑAL COINCIDE CON LA SEÑAL QUE INICIÓ EL COOLDOWN
        if new_signal == initial_signal:
            self.reset_cooldown(symbol, tf)
            return True
        
        return False
    
    def calculate_weight_with_cooldown(self, symbol, signals):
        """✅ CALCULAR PESO TENIENDO EN CUENTA COOLDOWNS - CORREGIDO"""
        weight = 0.0
        
        for tf, color in signals.items():
            w = TIMEFRAME_WEIGHTS[tf]
            
            # ✅ VERIFICAR SI ESTE TIMEFRAME ESTÁ EN COOLDOWN
            if self.is_cooldown_active(symbol, tf):
                # ✅ VERIFICAR SI SE DEBE BLOQUEAR EL CAMBIO DE SEÑAL
                if self.should_block_signal_change(symbol, tf, color):
                    # ✅ DIRECCIÓN OPUESTA BLOQUEADA - USAR PESO CONGELADO ACTUAL
                    frozen_weight = self.frozen_weights[symbol][tf]
                    if frozen_weight is not None:
                        weight += frozen_weight
                        
                        # ✅ EVITAR LOGS REPETIDOS - solo registrar una vez por cambio
                        current_time = time.time()
                        last_block_key = f"blocked_{symbol}_{tf}"
                        last_block_time = getattr(self, '_last_block_times', {}).get(last_block_key, 0)
                        
                        if current_time - last_block_time > 60:  # Solo cada 60 segundos
                            if not hasattr(self, '_last_block_times'):
                                self._last_block_times = {}
                            self._last_block_times[last_block_key] = current_time
                            
                            block_msg = f"⏸️ SIGNAL BLOCKED {symbol} {tf}: {color} (Opposite direction)"
                            if self.gui:
                                self.gui.log_trade(block_msg, 'YELLOW')
                            else:
                                print(block_msg)
                    else:
                        weight += 0.0
                else:
                    # ✅ MISMA DIRECCIÓN - USAR FROZEN WEIGHT EXISTENTE
                    frozen_weight = self.frozen_weights[symbol][tf]
                    if frozen_weight is not None:
                        weight += frozen_weight
                    else:
                        weight += 0.0
            else:
                # ✅ SIN COOLDOWN - CALCULAR NORMALMENTE
                if color == "GREEN":
                    weight += w
                elif color == "YELLOW":
                    weight += w * 0.5
        
        return weight
    
    def log_signal_changes(self, symbol, new_signals):
        """✅ REGISTRA CAMBIOS DE SEÑAL - CORREGIDO PARA BLOQUEOS"""
        if not self.first_rebalance_done:
            return
            
        old_signals = self.last_signals.get(symbol, {})
        
        for tf, new_color in new_signals.items():
            old_color = old_signals.get(tf)
            
            if old_color is not None and new_color != old_color:
                # ✅ 1. PRIMERO VERIFICAR RESET DE COOLDOWN
                if self.check_cooldown_reset(symbol, tf, new_color):
                    # ✅ COOLDOWN RESETEADO - CONTINUAR CON EL CAMBIO NORMALMENTE
                    pass
                
                # ✅ 2. VERIFICAR SI ESTE CAMBIO DEBE SER BLOQUEADO
                if self.should_block_signal_change(symbol, tf, new_color):
                    # ❌ CAMBIO BLOQUEADO - NO SE REGISTRA NI ACTUALIZA
                    # ❌ MANTENEMOS LA SEÑAL ANTERIOR EN last_signals
                    continue
                
                # ✅ 3. LOG NORMAL DEL CAMBIO (solo si no está bloqueado)
                change_msg = f"🔄 {symbol} {tf}: {old_color} → {new_color}"
                if self.gui:
                    self.gui.log_trade(change_msg, 'BLUE')
                else:
                    print(change_msg)
                
                # ✅ 4. DETECTAR CAMBIO DE DIRECCIÓN
                current_direction = self.get_change_direction(old_color, new_color)
                last_direction = self.last_changes[symbol].get(tf)
                
                if (last_direction is not None and 
                    current_direction != "NEUTRAL" and 
                    current_direction != last_direction):
                    
                    direction_msg = f"🔄 DIRECTION CHANGE {symbol} {tf}: {last_direction} → {current_direction}"
                    if self.gui:
                        self.gui.log_trade(direction_msg, 'YELLOW')
                    else:
                        print(direction_msg)
                    
                    if not self.is_cooldown_active(symbol, tf):
                        self.start_cooldown(symbol, tf, current_direction, new_color)
                
                self.last_changes[symbol][tf] = current_direction
            
            # ✅ ACTUALIZAR SEÑALES ANTERIORES SOLO SI NO ESTÁN BLOQUEADAS
            if not self.should_block_signal_change(symbol, tf, new_color):
                self.last_signals[symbol][tf] = new_color

    def calculate_weight(self, signals):
        """✅ CALCULO DE PESO SIMPLE (PARA USO INTERNO)"""
        weight = 0.0
        for tf, color in signals.items():
            w = TIMEFRAME_WEIGHTS[tf]
            if color == "GREEN":
                weight += w
            elif color == "YELLOW":
                weight += w * 0.5
        return weight
    
    def has_changed(self, symbol, new_weight):
        """✅ VERIFICAR SI EL PESO CAMBIÓ - RESPETANDO COOLDOWNS"""
        old = self.last_weights[symbol]
        
        # ✅ SI HAY ALGÚN COOLDOWN ACTIVO EN ESTE SYMBOL, NO PERMITIR CAMBIOS HACIA ABAJO
        has_active_cooldown = any(self.is_cooldown_active(symbol, tf) for tf in TIMEFRAMES)
        
        if has_active_cooldown and new_weight < old:
            # ❌ BLOQUEAR CAMBIOS NEGATIVOS DURANTE COOLDOWN
            return False
        
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
            
            # ✅ CALCULAR PESO PRIMERO (para determinar cambios)
            weight = self.calculate_weight_with_cooldown(symbol, signals)
            
            # ✅ REGISTRAR CAMBIOS DE SEÑAL (después de calcular peso)
            self.log_signal_changes(symbol, signals)
            
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