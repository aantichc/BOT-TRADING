
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
            
            # ✅ DETECTAR CAMBIO DE SEÑAL
            old_weight = self.last_weights.get(symbol, 0.0)
            signal_changed = self.has_changed(symbol, weight)
            
            if signal_changed or manual:
                # ✅ NOTIFICAR CAMBIO DE SEÑAL EN LOGS
                if signal_changed and not manual:
                    signal_change_msg = self._get_signal_change_message(symbol, signals, old_weight, weight)
                    actions.append(signal_change_msg)
                    if self.gui:
                        self.gui.log_trade(signal_change_msg, 'BLUE')
                
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
                            log_msg = f"🟢 COMPRA {symbol}: ${diff_usd:.2f} | Target: ${target_usd:.2f} | Peso: {weight:.2f}"
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
                            log_msg = f"🔴 VENTA {symbol}: {quantity:.6f} (${abs(diff_usd):.2f}) | Peso: {weight:.2f}"
                            actions.append(log_msg)
                            if self.gui:
                                self.gui.log_trade(log_msg, 'RED')
                        else:
                            error_msg = f"❌ ERROR VENTA {symbol}: {msg}"
                            actions.append(error_msg)
                            if self.gui:
                                self.gui.log_trade(error_msg, 'RED')
        
        return actions if actions else "No ajustes necesarios"

    def _get_signal_change_message(self, symbol, signals, old_weight, new_weight):
        """Genera mensaje de cambio de señal"""
        # Determinar señal anterior
        old_signal = self._weight_to_signal(old_weight)
        new_signal = self._weight_to_signal(new_weight)
        
        # Obtener timeframes con cambios
        timeframe_changes = []
        for tf in signals:
            signal_char = "🟢" if signals[tf] == "GREEN" else "🟡" if signals[tf] == "YELLOW" else "🔴"
            timeframe_changes.append(f"{tf}{signal_char}")
        
        timeframes_str = " ".join(timeframe_changes)
        
        if new_weight > old_weight:
            direction = "📈 MEJORÓ"
            color_indicator = "🟢"
        elif new_weight < old_weight:
            direction = "📉 EMPEORÓ" 
            color_indicator = "🔴"
        else:
            direction = "🔄 CAMBIÓ"
            color_indicator = "🟡"
        
        return f"{color_indicator} SEÑAL {symbol}: {direction} | {old_signal} → {new_signal} | Peso: {old_weight:.2f} → {new_weight:.2f} | {timeframes_str}"

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