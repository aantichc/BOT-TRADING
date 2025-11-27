# Archivo: capital_manager.py - VERSIÓN SIN LOGS DE COOLDOWN EN REBALANCE INICIAL
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
        self.SYMBOLS = SYMBOLS
        self.first_rebalance_done = False
        self.signal_cooldowns = {}
        self.COOLDOWN_MINUTES = 5
        
    def should_allow_signal_change(self, symbol, timeframe, new_signal, silent=False):
        """✅ OPCION SILENCIOSA PARA REBALANCE INICIAL"""
        key = (symbol, timeframe)
        current_time = time.time()
        
        if key not in self.signal_cooldowns:
            self.signal_cooldowns[key] = {
                'last_signal': new_signal,
                'last_change': current_time,
                'current_cycle_signal': new_signal,
                'change_count': 1,
                'evolution_path': [new_signal]
            }
            if not silent:
                print(f"✅ Primer registro: {symbol} {timeframe} → {new_signal}")
            return True
        
        cooldown_data = self.signal_cooldowns[key]
        last_signal = cooldown_data['last_signal']
        current_cycle_signal = cooldown_data['current_cycle_signal']
        last_change = cooldown_data['last_change']
        change_count = cooldown_data['change_count']
        evolution_path = cooldown_data.get('evolution_path', [last_signal])
        
        # Verificar si pasó cooldown
        time_since_change = current_time - last_change
        cooldown_remaining = (self.COOLDOWN_MINUTES * 60) - time_since_change
        
        if cooldown_remaining <= 0:
            # Cooldown completado - reiniciar CICLO
            cooldown_data['last_signal'] = new_signal
            cooldown_data['last_change'] = current_time
            cooldown_data['current_cycle_signal'] = new_signal
            cooldown_data['change_count'] = 1
            cooldown_data['evolution_path'] = [new_signal]
            if not silent:  # ✅ SOLO MOSTRAR SI NO ES SILENCIOSO
                print(f"✅ Cooldown completado: {symbol} {timeframe} → {new_signal} (nuevo ciclo)")
            return True
        
        # 🔄 DURANTE COOLDOWN - Lógica inteligente basada en CICLO ACTUAL
        is_same_signal = (new_signal == last_signal)
        is_natural_progression = self.is_natural_progression(symbol, timeframe, last_signal, new_signal, cooldown_data)
        
        if is_same_signal:
            cooldown_data['last_signal'] = new_signal
            # Actualizar el camino de evolución
            if evolution_path and evolution_path[-1] != new_signal:
                evolution_path.append(new_signal)
            return True
        elif is_natural_progression:
            cooldown_data['last_signal'] = new_signal
            cooldown_data['change_count'] += 1
            # Actualizar el camino de evolución
            if evolution_path and evolution_path[-1] != new_signal:
                evolution_path.append(new_signal)
            cooldown_data['evolution_path'] = evolution_path
            
            if not silent:  # ✅ SOLO MOSTRAR SI NO ES SILENCIOSO
                print(f"✅ Progresión natural: {symbol} {timeframe} {last_signal} → {new_signal} "
                    f"(cambios: {cooldown_data['change_count']}, ciclo: {current_cycle_signal}, camino: {'→'.join(evolution_path)})")
            return True
        else:
            # 🚫 BLOQUEADO - Cambio no permitido durante cooldown
            if not silent:  # ✅ SOLO MOSTRAR SI NO ES SILENCIOSO
                print(f"🚫 Cooldown bloqueado: {symbol} {timeframe} {last_signal} → {new_signal} "
                    f"(cooldown restante: {cooldown_remaining:.0f}s, ciclo: {current_cycle_signal}, camino: {'→'.join(evolution_path)})")
            return False
            
    def is_natural_progression(self, symbol, timeframe, current_signal, new_signal, cooldown_data):
        """✅ PROGRESIÓN NATURAL INTELIGENTE - Basada en CICLO ACTUAL"""
        
        # ✅ SIEMPRE permitir cambios directos ROJO↔VERDE
        if (current_signal == 'RED' and new_signal == 'GREEN') or \
           (current_signal == 'GREEN' and new_signal == 'RED'):
            return True
        
        current_cycle_signal = cooldown_data.get('current_cycle_signal', current_signal)
        change_count = cooldown_data.get('change_count', 1)
        evolution_path = cooldown_data.get('evolution_path', [])
        
        # ✅ EVOLUCIÓN ALCISTA NATURAL: RED → YELLOW → GREEN
        if current_cycle_signal == 'RED' and change_count == 1 and current_signal == 'YELLOW' and new_signal == 'GREEN':
            return True
        
        # ✅ EVOLUCIÓN BAJISTA NATURAL: GREEN → YELLOW → RED  
        if current_cycle_signal == 'GREEN' and change_count == 1 and current_signal == 'YELLOW' and new_signal == 'RED':
            return True
        
        # ✅ PRIMER PASO HACIA YELLOW: RED → YELLOW o GREEN → YELLOW
        if change_count == 1 and new_signal == 'YELLOW':
            return True
        
        # ✅ PERMITIR SALIR DE YELLOW SI ES PRIMER CAMBIO DESDE ROJO/VERDE
        if current_signal == 'YELLOW' and change_count == 2:
            # Solo permitir si estamos completando una evolución natural
            if (current_cycle_signal == 'RED' and new_signal == 'GREEN') or \
               (current_cycle_signal == 'GREEN' and new_signal == 'RED'):
                return True
        
        # 🚫 BLOQUEAR OSCILACIONES YELLOW:
        # - RED → YELLOW → RED (oscilación indecisa)
        # - GREEN → YELLOW → GREEN (oscilación indecisa)
        if current_signal == 'YELLOW' and change_count >= 2:
            if (current_cycle_signal == 'RED' and new_signal == 'RED') or \
               (current_cycle_signal == 'GREEN' and new_signal == 'GREEN'):
                return False
            
            # 🚫 Bloquear si ya hemos pasado por YELLOW y volvemos al mismo estado del ciclo
            if len(evolution_path) >= 3:
                if evolution_path[0] == 'RED' and evolution_path[1] == 'YELLOW' and new_signal == 'RED':
                    return False
                if evolution_path[0] == 'GREEN' and evolution_path[1] == 'YELLOW' and new_signal == 'GREEN':
                    return False
        
        # 🚫 Por defecto, bloquear cambios complejos durante cooldown
        return False
     
    def get_signals(self, symbol, skip_cooldown=False):
        """✅ OBTENER SEÑALES OO - OPCIÓN PARA OMITIR COOLDOWN Y LOGS"""
        signals = {}
        
        for tf_name, tf in TIMEFRAMES.items():
            try:
                # 1. OBTENER DATOS DE PRECIO
                df = self.indicators.get_klines(symbol, tf)
                
                if not df.empty:
                    # 2. CALCULAR SEÑAL OO
                    color, _ = self.indicators.calculate_oo(df)
                    
                    # 3. ✅ APLICAR COOLDOWN INTELIGENTE (OMITIR DURANTE REBALANCE INICIAL)
                    if skip_cooldown:
                        # ✅ DURANTE REBALANCE INICIAL: USAR SEÑAL REAL SIN COOLDOWN Y SIN LOGS
                        signals[tf_name] = color
                        # Pero aún así registrar para futuros cooldowns (EN SILENCIO)
                        self.should_allow_signal_change(symbol, tf_name, color, silent=True)
                    else:
                        # ✅ OPERACIÓN NORMAL: APLICAR COOLDOWN CON LOGS
                        if not self.should_allow_signal_change(symbol, tf_name, color, silent=False):
                            signals[tf_name] = "YELLOW"  # Señal neutral durante cooldown
                            print(f"⏳ Cooldown {symbol} {tf_name}: bloqueado revertir a {color}")
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
            # ✅ DURANTE REBALANCE INICIAL: OMITIR COOLDOWN PARA OBTENER SEÑALES REALES
            if force_initial_rebalance:
                signals = self.get_signals(symbol, skip_cooldown=True)  # ← SIN COOLDOWN Y SIN LOGS
            else:
                signals = self.get_signals(symbol)  # ← COOLDOWN NORMAL CON LOGS
                
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
                                continue
                        
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