
# Archivo: binance_account.py
from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN
from config import API_KEY, API_SECRET, TRADING_ENABLED, SYMBOLS

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
    
    def buy_market(self, symbol, usd_amount):
        if not TRADING_ENABLED:
            msg = f"[SIM] 🟢 COMPRA {symbol}: ${usd_amount:.1f}"
            if self.gui: 
                self.gui.log_trade(msg, 'GREEN')
            return True, msg
        try:
            price = self.get_current_price(symbol)
            quantity = self.format_quantity(symbol, usd_amount / price)
            order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
            
            # Log detallado
            executed_price = float(order['fills'][0]['price']) if order.get('fills') else price
            executed_total = float(order['cummulativeQuoteQty']) if order.get('cummulativeQuoteQty') else usd_amount
            
            msg = f"COMPRA{symbol}:{quantity:.1f} at ${executed_price:.2f}= ${executed_total:.2f}"
            if self.gui: 
                self.gui.log_trade(msg, 'GREEN')
            return True, msg
        except BinanceAPIException as e:
            msg = f"❌ ERROR COMPRA {symbol}: {e.message}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return False, msg

    def sell_market(self, symbol, quantity):
        if not TRADING_ENABLED:
            msg = f"[SIM] 🔴 VENTA {symbol}: {quantity:.1f}"
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
            
            msg = f"VENTA{symbol}:{quantity:.1f}${executed_price:.2f}->${executed_total:.2f}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return True, msg
        except BinanceAPIException as e:
            msg = f"❌ ERROR VENTA {symbol}: {e.message}"
            if self.gui: 
                self.gui.log_trade(msg, 'RED')
            return False, msg