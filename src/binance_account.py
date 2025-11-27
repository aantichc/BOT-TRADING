
# Archivo: binance_account.py
from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN
from config import API_KEY, API_SECRET, TRADING_ENABLED, SYMBOLS, MIN_TRADE_DIFF

class BinanceAccount:
    def __init__(self, gui=None):
        self.gui = gui
        self.client = Client(API_KEY, API_SECRET)
    
    def get_balance_usdc(self):
        """Balance total en USDC (incluyendo conversión de otros assets)"""
        try:
            account = self.client.get_account()
            total = 0.0
            prices = {t['symbol']: float(t['price']) for t in self.client.get_all_tickers()}
            for b in account['balances']:
                asset = b['asset']
                free = float(b['free'])
                if asset == 'USDC':
                    total += free
                elif f"{asset}USDC" in prices:
                    total += free * prices[f"{asset}USDC"]
            return total
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0
    
    def get_symbol_balance(self, symbol):
        asset = symbol.replace('USDC', '')
        account = self.client.get_account()
        for b in account['balances']:
            if b['asset'] == asset:
                return float(b['free']) + float(b['locked'])
        return 0.0
    
    def get_current_price(self, symbol):
        try:
            return float(self.client.get_symbol_ticker(symbol=symbol)['price'])
        except:
            return 0.0
    
    def format_quantity(self, symbol, quantity):
        """Formatea quantity para Binance rules"""
        info = self.client.get_symbol_info(symbol)
        lot_filter = next((f for f in info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        if lot_filter:
            min_qty = float(lot_filter['minQty'])
            step_size = float(lot_filter['stepSize'])
            quantity_dec = Decimal(str(quantity))
            step_dec = Decimal(str(step_size))
            steps = (quantity_dec / step_dec).to_integral_value(rounding=ROUND_DOWN)
            formatted = float(steps * step_dec)
            return max(min_qty, formatted)
        return quantity

    # Archivo: binance_account.py - MODIFICAR MÉTODO buy_market
    def buy_market(self, symbol, usd_amount):
        if not TRADING_ENABLED:
            msg = f"[SIM] 🟢 BUY {symbol}: ${usd_amount:.1f}"
            if self.gui: 
                self.gui.log_trade(msg, 'GREEN')
            return True, msg
        try:
            # ✅ OBTENER BALANCE DISPONIBLE EN USDC
            available_usdc = self.get_available_usdc()
            
            # ✅ SI NO HAY SUFICIENTE CAPITAL, USAR TODO EL DISPONIBLE
            if available_usdc < usd_amount:
                usd_amount = available_usdc
                if usd_amount < MIN_TRADE_DIFF:
                    msg = f"❌ CAPITAL INSUFICIENTE {symbol}: Necesita ${usd_amount:.2f}, disponible ${available_usdc:.2f}"
                    if self.gui: 
                        self.gui.log_trade(msg, 'RED')
                    return False, msg
                
                msg = f"⚠️ CAPITAL LIMITADO {symbol}: Usando ${usd_amount:.2f} de ${available_usdc:.2f} disponible"
                if self.gui: 
                    self.gui.log_trade(msg, 'YELLOW')
            
            price = self.get_current_price(symbol)
            quantity = self.format_quantity(symbol, usd_amount / price)
            
            # ✅ VERIFICAR QUE LA CANTIDAD SEA VÁLIDA
            if quantity <= 0:
                msg = f"❌ CANTIDAD INVÁLIDA {symbol}: {quantity}"
                if self.gui: 
                    self.gui.log_trade(msg, 'RED')
                return False, msg
                
            order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
            
            # Log detallado
            executed_price = float(order['fills'][0]['price']) if order.get('fills') else price
            executed_total = float(order['cummulativeQuoteQty']) if order.get('cummulativeQuoteQty') else usd_amount
            
            msg = f"🟢 BUY {symbol}: {quantity:.2f} a ${executed_price:.4f} = ${executed_total:.4f}"
            if self.gui: 
                self.gui.log_trade(msg, 'GREEN')
            return True, msg
            
        except BinanceAPIException as e:
            msg = f"❌ ERROR BUY {symbol}: {e.message}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return False, msg


    def get_available_usdc(self):
        """Obtiene el balance disponible en USDC"""
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == 'USDC':
                    return float(balance['free'])
            return 0.0
        except Exception as e:
            print(f"Error getting USDC balance: {e}")
            return 0.0

    def sell_market(self, symbol, quantity):
        if not TRADING_ENABLED:
            msg = f"[SIM] 🔴 SELL {symbol}: {quantity:.1f}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return True, msg
        try:
            price = self.get_current_price(symbol)
            quantity = self.format_quantity(symbol, quantity)
            order = self.client.order_market_sell(symbol=symbol, quantity=quantity)
            
            # Log detallado
            executed_price = float(order['fills'][0]['price']) if order.get('fills') else price
            executed_total = float(order['cummulativeQuoteQty']) if order.get('cummulativeQuoteQty') else quantity * price
            
            msg = f"SELL {symbol}:{quantity:.2f} at ${executed_price:.4f}= ${executed_total:.4f}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return True, msg
        except BinanceAPIException as e:
            msg = f"❌ ERROR VENTA {symbol}: {e.message}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return False, msg