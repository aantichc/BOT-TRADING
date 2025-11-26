# Archivo: capital_manager.py - VERSIÓN CON REBALANCE AUTOMÁTICO INICIAL
from config import TIMEFRAMES, SYMBOLS, TIMEFRAME_WEIGHTS, MIN_TRADE_DIFF
from datetime import datetime

class CapitalManager:
    def __init__(self, account, indicators, gui=None):
        self.account = account
        self.indicators = indicators
        self.gui = gui
        self.base_allocation = 1.0 / len(SYMBOLS)
        self.last_weights = {s: 0.0 for s in SYMBOLS}
        self.SYMBOLS = SYMBOLS
        self.first_rebalance_done = False  # ✅ NUEVO FLAG PARA PRIMER REBALANCE
    
    def get_signals(self, symbol):
        signals = {}
        for tf_name, tf in TIMEFRAMES.items():
            df = self.indicators.get_klines(symbol, tf)
            if not df.empty:
                color, _ = self.indicators.calculate_oo(df)
                signals[tf_name] = color
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
                        signal_change_msg = self._get_signal_change_message(symbol, signals, old_weight, weight)
                    
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

    def _get_signal_change_message(self, symbol, signals, old_weight, new_weight):
        """Genera mensaje de cambio de señal - MÁS CLARO"""
        # Determinar señal anterior y nueva
        old_signal = self._weight_to_signal(old_weight)
        new_signal = self._weight_to_signal(new_weight)
        
        # Obtener timeframes con cambios
        timeframe_changes = []
        for tf in signals:
            signal_char = "🟢" if signals[tf] == "GREEN" else "🟡" if signals[tf] == "YELLOW" else "🔴"
            timeframe_changes.append(f"{tf}{signal_char}")
        
        timeframes_str = " ".join(timeframe_changes)
        
        # Mensaje más claro
        if new_weight > old_weight:
            direction = "📈"
            color_indicator = "🟢"
        elif new_weight < old_weight:
            direction = "📉" 
            color_indicator = "🔴"
        else:
            return ""  # No loggear si no hay cambio real
        
        return f"{symbol}: {direction} {old_weight:.2f} → {new_weight:.2f}"

    def _weight_to_signal(self, weight):
        """Convierte peso numérico a texto de señal"""
        if weight >= 0.8:
            return "STRONG_BUY"
        elif weight >= 0.5:
            return "BUY"
        elif weight >= 0.3:
            return "SELL"
        else:
            return "STRONG_SELL"