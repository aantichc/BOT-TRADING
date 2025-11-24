from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN
from config import API_KEY, API_SECRET, TRADING_ENABLED

class BinanceAccount:
    def __init__(self):
        self.client = None
        self.current_min_qty = 0.0
        self.current_max_qty = 0.0
        self.gui = None  # ← NUEVO: referencia al GUI
        self.setup_client()
    
    def setup_client(self):
        """Configura el cliente de Binance para la cuenta"""
        try:
            self.client = Client(API_KEY, API_SECRET)
            print("✅ Cuenta de Binance conectada")
        except Exception as e:
            print(f"❌ Error conectando a cuenta de Binance: {str(e)}")
            self.client = None
    
    def get_step_precision(self, step_size):
        """Calcula la precisión decimal basada en el step size - VERSIÓN FINAL"""
        if step_size == 0:
            return 8
        
        # Convertir step_size a string para analizar los decimales
        step_str = f"{step_size:.10f}".rstrip('0').rstrip('.')
        
        if '.' in step_str:
            # Contar los dígitos después del punto decimal
            decimal_part = step_str.split('.')[1]
            return len(decimal_part)
        else:
            # Para steps enteros, precisión 0
            return 0
    
    def format_quantity(self, quantity, step_size):
        """Formatea la cantidad según el step size de Binance - VERSIÓN DECIMAL PRECISA"""
        # Usar Decimal para evitar errores de punto flotante
        quantity_dec = Decimal(str(quantity))
        step_dec = Decimal(str(step_size))
        
        # Calcular precisión
        precision = self.get_step_precision(step_size)
        
        # Calcular el número de steps (usando floor para asegurar múltiplo exacto)
        steps = (quantity_dec / step_dec).quantize(Decimal('1.'), rounding=ROUND_DOWN)
        formatted_dec = steps * step_dec
        
        # Convertir de vuelta a float
        formatted = float(formatted_dec)
        
        # Asegurar que no sea menor que el mínimo
        if hasattr(self, 'current_min_qty') and self.current_min_qty > 0:
            formatted = max(self.current_min_qty, formatted)
        
        # Asegurar que no exceda el máximo
        if hasattr(self, 'current_max_qty') and self.current_max_qty > 0:
            formatted = min(self.current_max_qty, formatted)
        
        # Formatear con la precisión correcta
        formatted = round(formatted, precision)
        
        return formatted
    
    def get_available_symbols(self):
        """Obtiene los símbolos disponibles para trading en la cuenta"""
        try:
            if self.client is None:
                return []
            
            exchange_info = self.client.get_exchange_info()
            available_symbols = []
            
            for symbol in exchange_info['symbols']:
                if symbol['status'] == 'TRADING' and 'SPOT' in symbol['permissions']:
                    available_symbols.append(symbol['symbol'])
            
            return available_symbols
            
        except Exception as e:
            print(f"Error obteniendo símbolos disponibles: {str(e)}")
            return []
    
    def get_spot_balance_usd(self):
        """Obtiene el capital total en USD de la cuenta spot - USDC"""
        try:
            if self.client is None:
                return 0.0, "Error: Cliente no disponible"
            
            account_info = self.client.get_account()
            prices = self.client.get_all_tickers()
            price_dict = {item['symbol']: float(item['price']) for item in prices}
            
            total_usd = 0.0
            balances_info = []
            
            for balance in account_info['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    # USDC como base
                    if asset == 'USDC':
                        total_usd += total
                        balances_info.append(f"USDC: ${total:,.2f}")
                    
                    # Buscar pares USDC
                    elif f"{asset}USDC" in price_dict:
                        asset_price = price_dict[f"{asset}USDC"]
                        asset_value = total * asset_price
                        total_usd += asset_value
                        balances_info.append(f"{asset}: ${asset_value:,.2f} ({total:.6f})")
                    
                    # Fallback a USDT si no hay USDC
                    elif f"{asset}USDT" in price_dict:
                        asset_price = price_dict[f"{asset}USDT"]
                        asset_value = total * asset_price
                        total_usd += asset_value
                        balances_info.append(f"{asset}: ${asset_value:,.2f} ({total:.6f}) via USDT")
            
            return total_usd, balances_info
            
        except BinanceAPIException as e:
            return 0.0, f"Error API: {e.message}"
        except Exception as e:
            return 0.0, f"Error: {str(e)}"
    
    def get_symbol_balance(self, symbol):
        """Obtiene el balance de un símbolo específico - USDC"""
        try:
            if self.client is None:
                return 0.0
            
            asset = symbol.replace('USDC', '')
            
            account_info = self.client.get_account()
            for balance in account_info['balances']:
                if balance['asset'] == asset:
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    return free + locked
            
            return 0.0
            
        except Exception as e:
            print(f"Error obteniendo balance de {symbol}: {str(e)}")
            return 0.0
    
    def get_usdc_balance(self):
        """Obtiene el balance específico de USDC"""
        try:
            if self.client is None:
                return 0.0
            
            account_info = self.client.get_account()
            for balance in account_info['balances']:
                if balance['asset'] == 'USDC':
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    return free + locked
            
            return 0.0
            
        except Exception as e:
            print(f"Error obteniendo balance USDC: {str(e)}")
            return 0.0
    
    def get_current_price(self, symbol):
        """Obtiene el precio actual de un símbolo"""
        try:
            if self.client is None:
                return 0.0
            
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
            
        except Exception as e:
            print(f"Error obteniendo precio de {symbol}: {str(e)}")
            return 0.0

    def buy_market(self, symbol, usd_amount):
        """Compra una crypto con cantidad en USDC - VERSIÓN FINAL"""
        if not TRADING_ENABLED:
            return True, f"[TEST] Compra simulada: {symbol} - ${usd_amount:.2f}"
        try:
            if self.client is None:
                return False, "Cliente no disponible"
            
            current_price = self.get_current_price(symbol)
            if current_price == 0:
                return False, "No se pudo obtener el precio"
            
            symbol_info = self.client.get_symbol_info(symbol)
            if not symbol_info:
                return False, "No se pudo obtener información del símbolo"
            
            raw_quantity = usd_amount / current_price
            
            lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
            if lot_size_filter:
                min_qty = float(lot_size_filter['minQty'])
                max_qty = float(lot_size_filter['maxQty'])
                step_size = float(lot_size_filter['stepSize'])
                
                # Guardar min_qty y max_qty para usarlos en format_quantity
                self.current_min_qty = min_qty
                self.current_max_qty = max_qty
                
                # Formatear cantidad según step size
                quantity = self.format_quantity(raw_quantity, step_size)
                quantity = max(min_qty, min(max_qty, quantity))
                
                if quantity < min_qty:
                    return False, f"Cantidad muy pequeña. Mínimo: {min_qty}, Calculado: {quantity}"
            else:
                quantity = raw_quantity
            
            # Verificar balance USDC específicamente
            usdc_balance = self.get_usdc_balance()
            # FIX: Si usd_amount > usdc_balance, comprar lo máximo disponible (en lugar de fallar)
            if usd_amount > usdc_balance:
                if usdc_balance > 0:
                    usd_amount = usdc_balance  # Comprar lo que queda
                    raw_quantity = usd_amount / current_price
                    quantity = self.format_quantity(raw_quantity, step_size) if lot_size_filter else raw_quantity
                    quantity = max(min_qty, min(max_qty, quantity)) if lot_size_filter else quantity
                    print(f"[DEBUG] Balance bajo: Comprando máximo disponible ${usd_amount:.2f}")
                else:
                    return False, f"Balance USDC insuficiente. Disponible: ${usdc_balance:.2f}, Necesario: ${usd_amount:.2f}"
            
            # DEBUG mejorado
            precision = self.get_step_precision(step_size) if lot_size_filter else 8
            print(f"🔧 DEBUG {symbol}:")
            print(f"   Precio: ${current_price:.4f}")
            print(f"   Cantidad cruda: {raw_quantity:.10f}")
            print(f"   Cantidad final: {quantity:.{precision}f}")
            print(f"   Step size: {step_size}")
            print(f"   Precisión: {precision}")
            print(f"   Min Qty: {min_qty}")
            print(f"   USDC: ${usd_amount:.2f}")
            
            # Realizar la orden de compra
            order = self.client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            )
            success_msg = f"COMPRA {symbol}: {quantity:.6f} @ ${current_price:,.4f} → ${usd_amount:,.2f}"
            if self.gui:
                self.gui.log_message(success_msg, 'GREEN')
            return True, success_msg
            
        except BinanceAPIException as e:
            return False, f"Error API en compra: {e.message}"
        except Exception as e:
            return False, f"Error en compra: {str(e)}"

    def sell_market(self, symbol, quantity):
        """Vende una crypto a precio de mercado - VERSIÓN USDC"""
        if not TRADING_ENABLED:
            return True, f"[TEST] Venta simulada: {symbol} - {quantity:.8f}"
        try:
            if self.client is None:
                return False, "Cliente no disponible"
            
            symbol_info = self.client.get_symbol_info(symbol)
            if not symbol_info:
                return False, "No se pudo obtener información del símbolo"
            
            lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
            if lot_size_filter:
                min_qty = float(lot_size_filter['minQty'])
                max_qty = float(lot_size_filter['maxQty'])
                step_size = float(lot_size_filter['stepSize'])
                
                # Guardar min_qty y max_qty
                self.current_min_qty = min_qty
                self.current_max_qty = max_qty
                
                quantity = self.format_quantity(quantity, step_size)
                quantity = max(min_qty, min(max_qty, quantity))
            
            current_balance = self.get_symbol_balance(symbol)
            if quantity > current_balance:
                quantity = current_balance
            
            if quantity < min_qty:
                return False, f"Cantidad insuficiente. Mínimo: {min_qty}, Disponible: {quantity}"
            
            # Realizar la orden de venta
            order = self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            
            current_price = self.get_current_price(symbol)
            usd_amount = quantity * current_price
            
            success_msg = f"VENTA {symbol}: {quantity:.6f} @ ${current_price:,.4f} → ${usd_amount:,.2f}"
            if self.gui:
                self.gui.log_message(success_msg, 'RED')
            return True, success_msg
            
        except BinanceAPIException as e:
            return False, f"Error API en venta: {e.message}"
        except Exception as e:
            return False, f"Error en venta: {str(e)}"
    
    def get_account_snapshot(self):
        """Obtiene un snapshot completo de la cuenta"""
        try:
            if self.client is None:
                return {"error": "Cliente no disponible"}
            
            snapshot = self.client.get_account_snapshot(type='SPOT')
            return snapshot
            
        except Exception as e:
            return {"error": str(e)}