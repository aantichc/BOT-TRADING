
# Archivo: indicators.py
import pandas as pd
from binance.client import Client

class Indicators:
    def __init__(self, client):
        self.client = client
        self.length = 8  # Para indicador OO
    
    def get_klines(self, symbol, timeframe):
        """Obtiene klines recientes, incluyendo vela actual"""
        try:
            klines = self.client.get_klines(symbol=symbol, interval=timeframe, limit=100)
            df = pd.DataFrame(klines, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
            df = df.astype({'open': float, 'high': float, 'low': float, 'close': float})
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('open_time', inplace=True)
            return self.to_heikin_ashi(df)
        except Exception as e:
            print(f"Error getting klines for {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def to_heikin_ashi(self, df):
        """Convierte a Heikin Ashi"""
        ha_df = df.copy()
        ha_df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_df['ha_open'] = ((df['open'].shift(1) + df['close'].shift(1)) / 2).fillna((df['open'] + df['close']) / 2)
        ha_df['ha_high'] = ha_df[['ha_open', 'ha_close', 'high']].max(axis=1)
        ha_df['ha_low'] = ha_df[['ha_open', 'ha_close', 'low']].min(axis=1)
        ha_df['open'] = ha_df['ha_open']
        ha_df['high'] = ha_df['ha_high']
        ha_df['low'] = ha_df['ha_low']
        ha_df['close'] = ha_df['ha_close']
        return ha_df[['open', 'high', 'low', 'close']]
    
    def calculate_oo(self, df):
        """Indicador OO con detección yellow"""
        if len(df) < self.length:
            return "RED", 0.0
        df['ys1'] = (df['high'] + df['low'] + df['close'] * 2) / 4
        df['rk3'] = df['ys1'].ewm(span=self.length, adjust=False).mean()
        df['rk4'] = df['ys1'].rolling(window=self.length).std().fillna(0.001)
        df['rk5'] = (df['ys1'] - df['rk3']) * 100 / df['rk4']
        df['rk6'] = df['rk5'].ewm(span=self.length, adjust=False).mean()
        df['up'] = df['rk6'].ewm(span=self.length, adjust=False).mean()
        df['down'] = df['up'].ewm(span=self.length, adjust=False).mean()
        
        last_up, last_down = df['up'].iloc[-1], df['down'].iloc[-1]
        prev_up, prev_down = df['up'].iloc[-2], df['down'].iloc[-2]
        diff = last_up - last_down
        
        up_changing = (prev_up > last_up) and (prev_down < last_down)
        down_changing = (prev_up < last_up) and (prev_down > last_down)
        is_yellow = up_changing or down_changing
        
        if last_up > last_down:
            return ("YELLOW" if is_yellow else "GREEN"), diff * (0.5 if is_yellow else 1.0)
        else:
            return ("YELLOW" if is_yellow else "RED"), diff * (0.5 if is_yellow else 1.0)

