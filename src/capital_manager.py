
# Archivo: capital_manager.py
from config import TIMEFRAMES, SYMBOLS, TIMEFRAME_WEIGHTS, MIN_TRADE_DIFF
from datetime import datetime

class CapitalManager:
    def __init__(self, account, indicators, gui=None):
        self.account = account
        self.indicators = indicators
        self.gui = gui
        self.base_allocation = 1.0 / len(SYMBOLS)
        self.last_weights = {s: 0.0 for s in SYMBOLS}
        self.SYMBOLS = SYMBOLS      # ← SIN ESTO self.bot.manager.SYMBOLS daba error
        self.initialized = False  # ✅ NUEVO FLAG
    
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
        
        for symbol in SYMBOLS:
            signals = self.get_signals(symbol)
            weight = self.calculate_weight(signals)
            
            # ✅ EVITAR LOGS DE INICIALIZACIÓN
            old_weight = self.last_weights.get(symbol, 0.0)
            signal_changed = self.has_changed(symbol, weight)
            
            # Si es la primera vez, establecer pesos sin log
            if not self.initialized:
                self.last_weights[symbol] = weight
                continue
            
            if signal_changed or manual:
                # ✅ SOLO LOGGEAR CAMBIOS REALES (no inicialización)
                if signal_changed and not manual:
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
                        # COMPRA
                        success, msg = self.account.buy_market(symbol, diff_usd)
                        if success:
                            #log_msg = f"🟢 COMPRA {symbol}: ${diff_usd:.2f} | Target: ${target_usd:.2f} | Peso: {weight:.2f}"
                            actions.append(log_msg)
                            if self.gui:
                                self.gui.log_trade(log_msg, 'GREEN')
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
                            #log_msg = f"🔴 VENTA {symbol}: {quantity:.6f} (${abs(diff_usd):.2f}) | Peso: {weight:.2f}"
                            actions.append(log_msg)
                            if self.gui:
                                self.gui.log_trade(log_msg, 'RED')
                        else:
                            error_msg = f"❌ ERROR VENTA {symbol}: {msg}"
                            actions.append(error_msg)
                            if self.gui:
                                self.gui.log_trade(error_msg, 'RED')
        
        # ✅ MARCAR COMO INICIALIZADO DESPUÉS DEL PRIMER CICLO
        if not self.initialized:
            self.initialized = True
            # ✅ LOG INICIAL ÚTIL - RESUMEN DE SEÑALES ACTUALES
            initial_summary = self._get_initial_summary()
            actions.append(initial_summary)
            if self.gui:
                self.gui.log_trade(initial_summary)
        
        return actions if actions else "No ajustes necesarios"
    
    def _get_initial_summary(self):
        """Genera un resumen limpio de las señales iniciales"""
        summary_lines = ["📊 SEÑALES INICIALES:"]
        
        for symbol in self.SYMBOLS:
            signals = self.get_signals(symbol)
            weight = self.calculate_weight(signals)
            
            # Convertir señales a emojis
            signal_emojis = []
            for tf in ["30m", "1h", "2h"]:
                if tf in signals:
                    signal = signals[tf]
                    emoji = "🟢" if signal == "GREEN" else "🟡" if signal == "YELLOW" else "🔴"
                    signal_emojis.append(f"{tf}{emoji}")
            
            signals_str = " ".join(signal_emojis)
            signal_text = self._weight_to_signal(weight)
            
            summary_lines.append(f" {symbol}: {signal_text} | Peso: {weight:.2f}")
        
        return "\n".join(summary_lines)

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
        
        return f"{symbol}: {direction} {old_weight} → {new_weight}"

    def _weight_to_signal(self, weight):
        """Convierte peso numérico a texto de señal"""
        if weight >= 0.8:
            return "FUERTE_COMPRA"
        elif weight >= 0.5:
            return "COMPRA"
        elif weight >= 0.3:
            return "NEUTRAL"
        else:
            return "VENTA"