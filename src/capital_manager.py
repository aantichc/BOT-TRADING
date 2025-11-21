import time
from binance_account import BinanceAccount
from config import SYMBOLS, TRADING_ENABLED

class CapitalManager:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.account = BinanceAccount()
        self.current_allocations = {}  # {symbol: allocation_percentage}
        self.target_allocations = {}   # {symbol: target_percentage}
        self.last_signals = {}         # {symbol: signal} para detectar cambios
        self.last_signal_weights = {}  # {symbol: signal_weight} para comparar cambios
        self.symbol_base_allocations = {} # {symbol: base_allocation} - asignación base igual
        self.initial_setup_done = False  # Flag para setup inicial
        self.last_total_capital = 0.0    # Para detectar cambios de capital
        self.initialize_allocations()
    
    def initialize_allocations(self):
        """Inicializa las asignaciones de capital - DISTRIBUCIÓN IGUAL"""
        # Distribución igual entre todas las monedas
        equal_percentage = 1.0 / len(SYMBOLS)
        for symbol in SYMBOLS:
            self.symbol_base_allocations[symbol] = equal_percentage  # Ej: 20% para 5 símbolos
            self.target_allocations[symbol] = equal_percentage       # Inicialmente igual
            self.current_allocations[symbol] = 0.0
            self.last_signals[symbol] = "CONSOLIDATION ⚡"
            self.last_signal_weights[symbol] = 0.0  # Inicialmente neutral
    
    def log_message(self, message, tag=None):
        """Método de log que usa la GUI si está disponible"""
        if self.gui:
            self.gui.log_message(message, tag)
        else:
            print(f"[CapitalManager] {message}")
    
    def calculate_signal_weight(self, timeframe_results):
        """Calcula peso con AMARILLO = 50%"""
        timeframe_weights = {
            "30m": 0.30,
            "1h": 0.30,  
            "2h": 0.40
        }
        
        total_weight = 0.0
        
        for tf_name, signal in timeframe_results.items():
            weight = timeframe_weights.get(tf_name, 0.0)
            
            if "GREEN" in signal:
                total_weight += weight  # 100%
            elif "YELLOW" in signal: 
                total_weight += weight * 0.5  # 50% 🟡
            # RED no suma nada
        
        return total_weight

    def has_signal_changed(self, symbol, current_signal_weight, threshold=0.1):
        """Determina si la señal de un símbolo específico ha cambiado significativamente"""
        last_weight = self.last_signal_weights.get(symbol, 0.0)
        
        # Calcular cambio absoluto
        weight_change = abs(current_signal_weight - last_weight)
        
        # Considerar cambio si la diferencia es mayor al threshold
        signal_changed = weight_change >= threshold
        
        # Actualizar último peso
        self.last_signal_weights[symbol] = current_signal_weight
        
        return signal_changed
    
    def get_signal_from_weight(self, weight):
        """Convierte el peso de señal a string de señal"""
        if weight >= 0.8:
            return "STRONG_BUY 🚀"
        elif weight >= 0.3:
            return "BULLISH_TREND 📈"
        elif weight <= -0.8:
            return "STRONG_SELL 🔻"
        elif weight <= -0.3:
            return "BEARISH_TREND 📉"
        else:
            return "CONSOLIDATION ⚡"
    
    def calculate_investment_percentage(self, signal_weight):
        """Calcula qué porcentaje del capital asignado a este token debe estar invertido - VERSIÓN SIMPLE"""
        # signal_weight YA es la suma directa de los pesos activos
        # Ejemplo: solo 30min GREEN → 0.30 = 30%
        # Ejemplo: todas GREEN → 1.00 = 100%
        
        # Solo limitar entre 0% y 100%
        investment_pct = max(0.0, min(1.0, signal_weight))
        
        return investment_pct
    
    def calculate_target_allocation(self, symbol, signal_weight, total_capital):
        """Calcula la asignación objetivo para un símbolo"""
        # La asignación base es igual para todos los tokens
        base_allocation = self.symbol_base_allocations.get(symbol, 1.0 / len(SYMBOLS))
        
        # Calcular qué porcentaje de esa asignación base debe estar invertido
        investment_percentage = self.calculate_investment_percentage(signal_weight)
        
        # La asignación objetivo es: (capital_total * asignación_base) * porcentaje_inversión
        target_allocation = base_allocation * investment_percentage
        
        return target_allocation
    
    def handle_initial_setup(self, all_signals, all_prices):
        """Maneja la configuración inicial del portfolio"""
        if self.initial_setup_done:
            return False, "Setup inicial ya realizado"
        
        try:
            total_usd, _ = self.account.get_spot_balance_usd()
            if not isinstance(total_usd, (int, float)) or total_usd <= 0:
                return False, "No se pudo obtener el capital total"
            
            self.log_message("🎯 CONFIGURACIÓN INICIAL DEL PORTFOLIO - USDC", 'HEADER')
            rebalance_actions = []
            
            for symbol in SYMBOLS:
                symbol_signals = all_signals.get(symbol, {})
                current_price = all_prices.get(symbol, 0.0)
                
                if not symbol_signals or current_price == 0:
                    continue
                
                # Calcular señal inicial
                current_signal_weight = self.calculate_signal_weight(symbol_signals)
                
                # Establecer estado inicial
                self.last_signal_weights[symbol] = current_signal_weight
                self.last_signals[symbol] = self.get_signal_from_weight(current_signal_weight)
                
                # Calcular asignación objetivo inicial
                target_allocation_pct = self.calculate_target_allocation(symbol, current_signal_weight, total_usd)
                target_usd = total_usd * target_allocation_pct
                
                # Obtener valor actual de la posición
                current_balance = self.account.get_symbol_balance(symbol)
                current_usd = current_balance * current_price
                
                # Calcular diferencia
                difference_usd = target_usd - current_usd
                
                # Ejecutar orden inicial si la diferencia es significativa
                if abs(difference_usd) > 20:  # Mínimo $20 para evitar órdenes muy pequeñas
                    if difference_usd > 0:
                        success, message = self.account.buy_market(symbol, difference_usd)
                        action_type = "COMPRA INICIAL"
                        log_tag = 'GREEN'
                    else:
                        sell_amount_usd = abs(difference_usd)
                        sell_quantity = sell_amount_usd / current_price
                        success, message = self.account.sell_market(symbol, sell_quantity)
                        action_type = "VENTA INICIAL" 
                        log_tag = 'RED'
                    
                    if success:
                        result = f"✅ {action_type} {symbol}: {message}"
                        rebalance_actions.append(result)
                        self.log_message(f"💰 {action_type} {symbol}: {message}", log_tag)
                        self.current_allocations[symbol] = target_allocation_pct
                    else:
                        result = f"❌ {action_type} {symbol} fallida: {message}"
                        rebalance_actions.append(result)
                        self.log_message(f"❌ {action_type} {symbol} fallida: {message}", 'ERROR')
                    
                    time.sleep(0.3)
            
            if rebalance_actions:
                self.initial_setup_done = True
                self.log_message("🎯 CONFIGURACIÓN INICIAL COMPLETADA - USDC", 'SUCCESS')
                return True, " | ".join(rebalance_actions)
            else:
                self.initial_setup_done = True
                self.log_message("⚡ Configuración inicial: No se requirieron ajustes", 'INFO')
                return True, "No se requirieron ajustes en setup inicial"
                
        except Exception as e:
            self.log_message(f"❌ Error en configuración inicial: {str(e)}", 'ERROR')
            return False, f"Error en setup inicial: {str(e)}"

    def rebalance_symbol(self, symbol, symbol_signals, current_price, total_usd, manual_rebalance=False):
        try:
            current_signal_weight = self.calculate_signal_weight(symbol_signals)
            target_allocation_pct = self.calculate_target_allocation(symbol, current_signal_weight, total_usd)
            target_usd = total_usd * target_allocation_pct
            
            current_balance = self.account.get_symbol_balance(symbol)
            current_usd = current_balance * current_price
            difference_usd = target_usd - current_usd
            
            min_amount = 1.0
            
            # ✅ SOLO LOG SI HAY OPERACIÓN O MODO MANUAL
            if abs(difference_usd) > min_amount:
                action = "COMPRA" if difference_usd > 0 else "VENTA"
                
                if not TRADING_ENABLED:
                    self.log_message(f"🔒 [TEST] {action} {symbol}: ${abs(difference_usd):.2f}", 'INFO')
                    return f"🔒 [TEST] {action} {symbol}"
                else:
                    if difference_usd > 0:
                        success, message = self.account.buy_market(symbol, difference_usd)
                        if success:
                            self.log_message(f"💰 {action} {symbol}: ${abs(difference_usd):.2f}", 'GREEN')
                            # Actualizar estado
                            self.current_allocations[symbol] = target_allocation_pct
                            self.last_signals[symbol] = self.get_signal_from_weight(current_signal_weight)
                            self.last_signal_weights[symbol] = current_signal_weight
                        else:
                            self.log_message(f"❌ {action} {symbol}: {message}", 'ERROR')
                    else:
                        sell_amount_usd = abs(difference_usd)
                        sell_quantity = sell_amount_usd / current_price
                        success, message = self.account.sell_market(symbol, sell_quantity)
                        if success:
                            self.log_message(f"💰 {action} {symbol}: ${abs(difference_usd):.2f}", 'RED')
                            # Actualizar estado
                            self.current_allocations[symbol] = target_allocation_pct
                            self.last_signals[symbol] = self.get_signal_from_weight(current_signal_weight)
                            self.last_signal_weights[symbol] = current_signal_weight
                        else:
                            self.log_message(f"❌ {action} {symbol}: {message}", 'ERROR')
                    
                    time.sleep(0.3)
                    return f"✅ {action} {symbol}"
            
            return None
                        
        except Exception as e:
            self.log_message(f"❌ Error en {symbol}: {str(e)}", 'ERROR')
            return f"❌ Error en {symbol}"

    def rebalance_portfolio(self, all_signals, all_prices, manual_rebalance=False):
        """Reequilibra el portfolio - VERSIÓN OPTIMIZADA"""
        try:
            # PRIMERO: Manejar configuración inicial si no se ha hecho
            if not self.initial_setup_done:
                success, message = self.handle_initial_setup(all_signals, all_prices)
                return success, message
            
            # LUEGO: Rebalanceo normal por cambios
            total_usd, _ = self.account.get_spot_balance_usd()
            if not isinstance(total_usd, (int, float)) or total_usd <= 0:
                return False, "No se pudo obtener el capital total"
            
            rebalance_actions = []
            symbols_rebalanced = 0
            
            for symbol in SYMBOLS:
                symbol_signals = all_signals.get(symbol, {})
                current_price = all_prices.get(symbol, 0.0)
                
                if not symbol_signals or current_price == 0:
                    continue
                
                # ✅ SOLO rebalancear si la señal cambió significativamente
                current_signal_weight = self.calculate_signal_weight(symbol_signals)
                signal_changed = self.has_signal_changed(symbol, current_signal_weight, threshold=0.15)
                
                if signal_changed or manual_rebalance:
                    result = self.rebalance_symbol(symbol, symbol_signals, current_price, total_usd, manual_rebalance)
                    if result:
                        rebalance_actions.append(result)
                        symbols_rebalanced += 1
            
            if rebalance_actions:
                mode = "MANUAL" if manual_rebalance else "AUTO"
                summary = f"[{mode}] Rebalanceados {symbols_rebalanced} símbolos"
                return True, summary
            else:
                mode = "MANUAL" if manual_rebalance else "AUTO"
                return True, f"[{mode}] No se requirieron ajustes"
                
        except Exception as e:
            return False, f"Error en rebalanceo: {str(e)}"
        
    def get_portfolio_status(self):
        """Obtiene el estado actual del portfolio"""
        try:
            total_usd, balances_info = self.account.get_spot_balance_usd()
            if not isinstance(total_usd, (int, float)):
                return "Error obteniendo portfolio"
            
            status_lines = [f"💰 Capital Total: ${total_usd:,.2f} USDC"]
            status_lines.append(f"🔢 Tokens monitoreados: {len(SYMBOLS)}")
            status_lines.append(f"📊 Asignación base por token: {(1.0/len(SYMBOLS))*100:.1f}%")
            status_lines.append("─" * 50)
            
            total_invested = 0.0
            symbols_with_changes = 0
            
            for symbol in SYMBOLS:
                current_balance = self.account.get_symbol_balance(symbol)
                current_price = self.account.get_current_price(symbol)
                current_usd = current_balance * current_price
                total_invested += current_usd
                
                # Calcular señal actual para comparar
                current_signal_weight = self.last_signal_weights.get(symbol, 0.0)
                current_signal = self.get_signal_from_weight(current_signal_weight)
                
                if current_usd > 0.1:  # Mostrar posiciones > $0.10
                    current_allocation = (current_usd / total_usd) * 100 if total_usd > 0 else 0
                    base_allocation_pct = self.symbol_base_allocations.get(symbol, 0) * 100
                    
                    # Calcular porcentaje utilizado del capital asignado
                    assigned_capital = total_usd * self.symbol_base_allocations.get(symbol, 0)
                    utilization_pct = (current_usd / assigned_capital) * 100 if assigned_capital > 0 else 0
                    
                    # Indicador de cambio reciente
                    signal_change_indicator = "🔄" if self.has_signal_changed(symbol, current_signal_weight, 0.001) else "⚡"
                    
                    status_lines.append(
                        f"{signal_change_indicator} {symbol}: ${current_usd:,.2f} ({current_allocation:.1f}%)\n"
                        f"   📈 Utilización: {utilization_pct:.1f}% de {base_allocation_pct:.1f}% asignado\n"
                        f"   🎯 Señal: {current_signal} (Peso: {current_signal_weight:.2f})"
                    )
                else:
                    # Mostrar símbolos sin posición pero con señal
                    current_signal = self.last_signals.get(symbol, "N/A")
                    signal_change_indicator = "🔄" if self.has_signal_changed(symbol, current_signal_weight, 0.001) else "⚡"
                    
                    status_lines.append(
                        f"{signal_change_indicator} {symbol}: Sin posición\n"
                        f"   🎯 Señal: {current_signal} (Peso: {current_signal_weight:.2f})"
                    )
            
            # Agregar información del cash (USDC)
            cash_usd = total_usd - total_invested
            cash_percentage = (cash_usd / total_usd) * 100 if total_usd > 0 else 0
            status_lines.append(f"\n💵 Cash disponible (USDC): ${cash_usd:,.2f} ({cash_percentage:.1f}%)")
            
            # Contar símbolos con cambios recientes
            for symbol in SYMBOLS:
                if self.has_signal_changed(symbol, self.last_signal_weights.get(symbol, 0.0), 0.001):
                    symbols_with_changes += 1
            
            status_lines.append(f"🔔 Símbolos con cambios recientes: {symbols_with_changes}/{len(SYMBOLS)}")
            
            return "\n".join(status_lines)
            
        except Exception as e:
            return f"Error: {str(e)}"