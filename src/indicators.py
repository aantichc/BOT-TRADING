import pandas as pd
import numpy as np
from datetime import datetime

class HeikinAshiCalculator:
    @staticmethod
    def convert_to_heikin_ashi(df):
        """Convierte un DataFrame de velas normales a Heikin Ashi"""
        try:
            ha_df = df.copy()
            
            # Calcular Heikin Ashi
            ha_df['HA_Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
            
            # Inicializar HA_Open con primer valor
            ha_df['HA_Open'] = 0.0
            ha_df.loc[ha_df.index[0], 'HA_Open'] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
            
            # Calcular HA_Open para las velas restantes
            for i in range(1, len(ha_df)):
                ha_df.iloc[i, ha_df.columns.get_loc('HA_Open')] = (
                    ha_df['HA_Open'].iloc[i-1] + ha_df['HA_Close'].iloc[i-1]
                ) / 2
            
            # Calcular HA_High y HA_Low
            ha_df['HA_High'] = ha_df[['HA_Open', 'HA_Close', 'High']].max(axis=1)
            ha_df['HA_Low'] = ha_df[['HA_Open', 'HA_Close', 'Low']].min(axis=1)
            
            # Reemplazar columnas originales con Heikin Ashi
            ha_df['Open'] = ha_df['HA_Open']
            ha_df['High'] = ha_df['HA_High']
            ha_df['Low'] = ha_df['HA_Low']
            ha_df['Close'] = ha_df['HA_Close']
            
            # Eliminar columnas temporales
            ha_df.drop(['HA_Open', 'HA_High', 'HA_Low', 'HA_Close'], axis=1, inplace=True)
            
            return ha_df
            
        except Exception as e:
            raise Exception(f"Error convirtiendo a Heikin Ashi: {str(e)}")

class TradingIndicator:
    def __init__(self, length=8):
        self.length = length
    
    def calculate_movement_percentage(self, df):
        """Calcula el porcentaje de movimiento de la vela actual"""
        try:
            if len(df) < 1:
                return 0.0
            
            current_candle = df.iloc[-1]
            open_price = current_candle['Open']
            current_price = current_candle['Close']
            
            if open_price == 0:
                return 0.0
            
            percentage = ((current_price - open_price) / open_price) * 100
            return percentage
            
        except Exception as e:
            return 0.0

    def calculate_indicator_oo(self, df, symbol):
        """Calcula indicador con estado AMARILLO"""
        try:
            if len(df) < self.length:
                return "ERROR: No hay suficientes datos", 0.0
                
            df = df.copy()
            
            # Cálculos existentes
            df['ys1'] = (df['High'] + df['Low'] + df['Close'] * 2) / 4
            df['rk3'] = df['ys1'].ewm(span=self.length, adjust=False).mean()
            df['rk4'] = df['ys1'].rolling(window=self.length).std().fillna(0.001)
            df['rk5'] = np.where(df['rk4'] != 0, 
                                (df['ys1'] - df['rk3']) * 100 / df['rk4'], 
                                0)
            df['rk6'] = df['rk5'].ewm(span=self.length, adjust=False).mean()
            df['up'] = df['rk6'].ewm(span=self.length, adjust=False).mean()
            df['down'] = df['up'].ewm(span=self.length, adjust=False).mean()
            
            # Analizar vela actual Y anterior para detectar amarillo
            last_up = df['up'].iloc[-1]
            last_down = df['down'].iloc[-1]
            prev_up = df['up'].iloc[-2] 
            prev_down = df['down'].iloc[-2]
            
            diff = last_up - last_down
            
            # ✅ DETECTAR AMARILLO (transición)
            is_yellow = (prev_up < last_up) and (last_down < prev_down)
            
            if last_up > last_down:
                if is_yellow:
                    return "YELLOW 🟡", diff * 0.5  # 50% del peso
                else:
                    return "GREEN 🟢", diff
            else:
                if is_yellow:
                    return "YELLOW 🟡", diff * 0.5  # 50% del peso  
                else:
                    return "RED 🔴", diff
                    
        except Exception as e:
            return f"ERROR: {str(e)}", 0.0