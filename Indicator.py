import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import sys

# ============= CONFIGURACIÓN =============
symbols = ["FET-USD", "XLM-USD", "BTC-USD"]
length = 8                  
UPDATE_INTERVAL = 1  # ⬅️ 1 SEGUNDO

timeframes = {
    "30m": "30m",
    "1h":  "1h", 
    "2h":  "2h"
}

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Bot TradingView - Múltiples Símbolos")
        self.root.geometry("1000x800")
        self.root.configure(bg='#2b2b2b')
        
        # Variables de control
        self.running = False
        self.contador = 0
        
        self.setup_ui()
    
    def setup_ui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = tk.Label(main_frame, 
                              text="🤖 BOT TRADINGVIEW - 3 SÍMBOLOS (FET, XLM, BTC)", 
                              font=('Arial', 16, 'bold'),
                              fg='white',
                              bg='#2b2b2b')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Subtítulo
        subtitle_label = tk.Label(main_frame,
                                 text="✅ Analizando VELA ACTUAL (incompleta) | ⏰ Actualizando CADA SEGUNDO",
                                 font=('Arial', 10),
                                 fg='#cccccc',
                                 bg='#2b2b2b')
        subtitle_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))
        
        # Frame de controles
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, pady=(0, 20), sticky=(tk.W, tk.E))
        
        # Botones de control
        self.start_button = tk.Button(control_frame, 
                                     text="▶️ INICIAR BOT", 
                                     command=self.start_bot,
                                     font=('Arial', 12, 'bold'),
                                     bg='#28a745',
                                     fg='white',
                                     width=15,
                                     height=2)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = tk.Button(control_frame, 
                                    text="⏸️ PAUSAR BOT", 
                                    command=self.stop_bot,
                                    font=('Arial', 12, 'bold'),
                                    bg='#dc3545',
                                    fg='white',
                                    width=15,
                                    height=2,
                                    state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Estado del bot
        self.status_label = tk.Label(control_frame,
                                    text="🛑 BOT DETENIDO",
                                    font=('Arial', 12, 'bold'),
                                    fg='#dc3545',
                                    bg='#2b2b2b')
        self.status_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Frame para resultados de los 3 símbolos
        self.symbol_frames = {}
        for i, symbol in enumerate(symbols):
            symbol_frame = ttk.LabelFrame(main_frame, text=f"📊 {symbol}", padding="10")
            symbol_frame.grid(row=3, column=i, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=(0, 10))
            symbol_frame.columnconfigure(0, weight=1)
            
            # Información del símbolo
            time_label = tk.Label(symbol_frame, text="Hora: --:--:--", font=('Arial', 9))
            time_label.grid(row=0, column=0, sticky=tk.W, pady=2)
            
            # Resultados por timeframe
            result_labels = {}
            row_idx = 1
            
            for tf_name in timeframes.keys():
                label = tk.Label(symbol_frame, text=f"{tf_name.upper():>4}: --", font=('Arial', 10, 'bold'))
                label.grid(row=row_idx, column=0, sticky=tk.W, pady=1)
                result_labels[tf_name] = label
                row_idx += 1
            
            # Señal de trading
            signal_label = tk.Label(symbol_frame, text="SEÑAL: --", font=('Arial', 11, 'bold'))
            signal_label.grid(row=row_idx, column=0, sticky=tk.W, pady=(5, 0))
            row_idx += 1
            
            # Progreso de velas
            progress_labels = {}
            for j, tf_name in enumerate(timeframes.keys()):
                label = tk.Label(symbol_frame, text=f"{tf_name.upper()}: --", font=('Arial', 8))
                label.grid(row=row_idx, column=0, sticky=tk.W, pady=1)
                progress_labels[tf_name] = label
                row_idx += 1
            
            self.symbol_frames[symbol] = {
                'time_label': time_label,
                'result_labels': result_labels,
                'signal_label': signal_label,
                'progress_labels': progress_labels
            }
        
        # Configurar igual ancho para las columnas de símbolos
        for i in range(len(symbols)):
            main_frame.columnconfigure(i, weight=1)
        
        # Resumen general
        summary_frame = ttk.LabelFrame(main_frame, text="🎯 RESUMEN GENERAL", padding="10")
        summary_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 10))
        
        self.summary_label = tk.Label(summary_frame, text="--", font=('Arial', 12, 'bold'))
        self.summary_label.pack()
        
        # Consola de logs
        log_frame = ttk.LabelFrame(main_frame, text="📝 LOGS DETALLADOS", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 height=12, 
                                                 width=100,
                                                 bg='#1e1e1e',
                                                 fg='#ffffff',
                                                 font=('Consolas', 8))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar tags para colores en los logs
        self.log_text.tag_config('VERDE', foreground='#00ff00')
        self.log_text.tag_config('ROJO', foreground='#ff0000')
        self.log_text.tag_config('ERROR', foreground='#ff6b6b')
        self.log_text.tag_config('INFO', foreground='#4ecdc4')
        self.log_text.tag_config('WARNING', foreground='#ffe66d')
        self.log_text.tag_config('BTC', foreground='#f7931a')
        self.log_text.tag_config('FET', foreground='#00d1b2')
        self.log_text.tag_config('XLM', foreground='#14b6ff')
        
    def log_message(self, message, tag=None):
        """Añade mensaje a la consola de logs"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_bot(self):
        """Inicia el bot en un hilo separado"""
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="🟢 BOT EJECUTÁNDOSE", fg='#28a745')
            
            self.log_message("🤖 Bot iniciado - Analizando 3 símbolos: FET, XLM, BTC", 'INFO')
            self.log_message("⏰ Actualización CADA SEGUNDO en tiempo real", 'INFO')
            
            # Iniciar el bucle del bot en un hilo separado
            self.bot_thread = threading.Thread(target=self.run_bot_segundo_a_segundo, daemon=True)
            self.bot_thread.start()
    
    def stop_bot(self):
        """Detiene el bot"""
        if self.running:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_label.config(text="🛑 BOT DETENIDO", fg='#dc3545')
            self.log_message(f"⏹️ Bot detenido. Total de ejecuciones: {self.contador}", 'INFO')
    
    def run_bot_segundo_a_segundo(self):
        """Bucle principal del bot - actualización cada segundo"""
        while self.running:
            try:
                self.contador += 1
                
                # Actualizar interfaz
                self.root.after(0, self.update_display_header)
                
                # Solo mostrar cada 10 ejecuciones para no saturar logs
                if self.contador % 10 == 1:
                    self.log_message(f"\n{'='*80}", 'INFO')
                    self.log_message(f"🔄 EJECUCIÓN #{self.contador}", 'INFO')
                
                # Analizar todos los símbolos
                all_results = {}
                all_progresses = {}
                all_signals = {}
                
                for symbol in symbols:
                    # Solo log detallado cada 10 ejecuciones
                    if self.contador % 10 == 1:
                        self.log_message(f"\n🔍 Analizando {symbol}...", symbol.replace('-USD', ''))
                    
                    resultados, progresos = self.analizar_symbol(symbol)
                    señal = self.generar_señal_trading(resultados, symbol)
                    
                    all_results[symbol] = resultados
                    all_progresses[symbol] = progresos
                    all_signals[symbol] = señal
                
                # Actualizar resultados en la interfaz (SIEMPRE)
                self.root.after(0, lambda: self.update_all_results(all_results, all_progresses, all_signals))
                
                # Generar resumen general (solo log cada 10 ejecuciones)
                if self.contador % 10 == 1:
                    self.generar_resumen_general(all_signals)
                
                # Esperar EXACTAMENTE 1 segundo antes de la siguiente actualización
                time.sleep(UPDATE_INTERVAL)
                        
            except Exception as e:
                self.log_message(f"❌ Error en el bucle principal: {str(e)}", 'ERROR')
                time.sleep(1)
    
    def update_display_header(self):
        """Actualiza la información general en la interfaz"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for symbol in symbols:
            self.symbol_frames[symbol]['time_label'].config(text=f"Hora: {current_time}")
    
    def update_all_results(self, all_results, all_progresses, all_signals):
        """Actualiza los resultados de todos los símbolos en la interfaz gráfica"""
        for symbol in symbols:
            resultados = all_results[symbol]
            progresos = all_progresses[symbol]
            señal = all_signals[symbol]
            
            self.update_symbol_results(symbol, resultados, progresos, señal)
    
    def update_symbol_results(self, symbol, resultados, progresos, señal):
        """Actualiza los resultados de un símbolo específico"""
        frame_data = self.symbol_frames[symbol]
        
        # Actualizar resultados por timeframe
        for tf_name, color in resultados.items():
            label = frame_data['result_labels'][tf_name]
            label_text = f"{tf_name.upper():>4}: {color}"
            label.config(text=label_text)
            
            # Colorear según el resultado
            if "VERDE" in color:
                label.config(fg='#00ff00')
            elif "ROJO" in color:
                label.config(fg='#ff0000')
            else:
                label.config(fg='#ff6b6b')
        
        # Actualizar progresos
        for tf_name, progreso in progresos.items():
            label = frame_data['progress_labels'][tf_name]
            label.config(text=f"{tf_name.upper()}: {progreso}")
        
        # Actualizar señal de trading
        frame_data['signal_label'].config(text=f"SEÑAL: {señal}")
        
        # Colorear la señal
        if "COMPRA_FUERTE" in señal:
            frame_data['signal_label'].config(fg='#00ff00', bg='#1e3a1e')
        elif "VENTA_FUERTE" in señal:
            frame_data['signal_label'].config(fg='#ff0000', bg='#3a1e1e')
        elif "ALCISTA" in señal:
            frame_data['signal_label'].config(fg='#90ee90', bg='#2b2b2b')
        elif "BAJISTA" in señal:
            frame_data['signal_label'].config(fg='#ff6b6b', bg='#2b2b2b')
        else:
            frame_data['signal_label'].config(fg='#ffff00', bg='#2b2b2b')
    
    def generar_resumen_general(self, all_signals):
        """Genera un resumen general de todas las señales"""
        compras_fuertes = sum(1 for s in all_signals.values() if "COMPRA_FUERTE" in s)
        ventas_fuertes = sum(1 for s in all_signals.values() if "VENTA_FUERTE" in s)
        alcistas = sum(1 for s in all_signals.values() if "ALCISTA" in s)
        bajistas = sum(1 for s in all_signals.values() if "BAJISTA" in s)
        
        resumen = f"📈 COMPRAS: {compras_fuertes} | 📉 VENTAS: {ventas_fuertes} | 🟢 ALCISTAS: {alcistas} | 🔻 BAJISTAS: {bajistas}"
        
        self.summary_label.config(text=resumen)
        self.log_message(f"🎯 RESUMEN GENERAL: {resumen}", 'INFO')

    # ============= FUNCIONES DEL BOT (MANTENIDAS) =============
    
    def obtener_datos_tiempo_real(self, symbol, timeframe, period="5d"):
        """
        Obtiene datos INCLUYENDO la vela actual en formación
        """
        ticker = yf.Ticker(symbol)
        
        if timeframe == "2h":
            # Para 2h, usamos datos de 1h y resampleamos
            df_1h = ticker.history(period="10d", interval="1h")
            if df_1h.empty:
                raise Exception("No hay datos")
            
            # Resamplear a 2h - INCLUYENDO VELA ACTUAL
            df_2h = df_1h.resample('2H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min', 
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            return df_2h  # ⬅️ INCLUYE vela actual
            
        else:
            # Para 30m y 1h - INCLUYENDO VELA ACTUAL
            df = ticker.history(period=period, interval=timeframe)
            if df.empty:
                raise Exception("No hay datos")
            
            return df  # ⬅️ INCLUYE vela actual

    def calcular_indicador_oo(self, df, symbol):
        """Calcula el indicador usando vela actual INCOMPLETA"""
        try:
            # Verificar que tenemos datos
            if len(df) < length:
                return "ERROR: Pocos datos"
            
            df = df.copy()
            
            # Cálculos del indicador
            df['ys1'] = (df['High'] + df['Low'] + df['Close'] * 2) / 4
            df['rk3'] = df['ys1'].ewm(span=length, adjust=False).mean()
            df['rk4'] = df['ys1'].rolling(window=length).std().fillna(0.001)
            
            df['rk5'] = np.where(df['rk4'] != 0, 
                                (df['ys1'] - df['rk3']) * 100 / df['rk4'], 
                                0)
            
            df['rk6'] = df['rk5'].ewm(span=length, adjust=False).mean()
            df['up'] = df['rk6'].ewm(span=length, adjust=False).mean()
            df['down'] = df['up'].ewm(span=length, adjust=False).mean()
            
            # ⬇️⬇️⬇️ ANALIZAR LA VELA ACTUAL (INCOMPLETA) ⬇️⬇️⬇️
            ultima_up = df['up'].iloc[-1]      # VELA ACTUAL
            ultima_down = df['down'].iloc[-1]  # VELA ACTUAL
            
            # Debug info (solo cada 10 ejecuciones)
            if self.contador % 10 == 1:
                diff = ultima_up - ultima_down
                symbol_short = symbol.replace('-USD', '')
                self.log_message(f"    {symbol_short} - up: {ultima_up:.4f}, down: {ultima_down:.4f}, diff: {diff:.4f}", symbol_short)
            
            if ultima_up > ultima_down:
                return "VERDE 🟢"   
            else:
                return "ROJO 🔴"
                
        except Exception as e:
            return f"ERROR: {str(e)}"

    def obtener_progreso_vela_actual(self, timeframe):
        """Calcula el progreso de la vela actual"""
        ahora = datetime.now()
        
        if timeframe == "30m":
            progreso = (ahora.minute % 30) / 30 * 100
            minutos_restantes = 30 - (ahora.minute % 30)
            return f"{progreso:.0f}% ({minutos_restantes}min rest)"
        elif timeframe == "1h":
            progreso = ahora.minute / 60 * 100
            minutos_restantes = 60 - ahora.minute
            return f"{progreso:.0f}% ({minutos_restantes}min rest)"
        elif timeframe == "2h":
            hora_en_2h_ciclo = ahora.hour % 2
            progreso = (hora_en_2h_ciclo * 60 + ahora.minute) / 120 * 100
            horas_restantes = 1 - hora_en_2h_ciclo
            minutos_restantes = 60 - ahora.minute
            return f"{progreso:.0f}% ({horas_restantes}h {minutos_restantes}min rest)"

    def analizar_symbol(self, symbol):
        """Analiza un símbolo específico"""
        symbol_short = symbol.replace('-USD', '')
        
        # Solo log detallado cada 10 ejecuciones para no saturar
        if self.contador % 10 == 1:
            self.log_message(f"📊 ANÁLISIS {symbol_short} - Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", symbol_short)
            self.log_message("🎯 Usando VELA ACTUAL (señales en tiempo real)", symbol_short)
            self.log_message("-" * 50, symbol_short)
        
        resultados = {}
        progresos = {}
        
        for nombre, tf in timeframes.items():
            try:
                if self.contador % 10 == 1:
                    self.log_message(f"Analizando {nombre}...", symbol_short)
                
                df = self.obtener_datos_tiempo_real(symbol, tf)
                
                if len(df) < length:
                    color = f"ERROR: Solo {len(df)} velas"
                else:
                    # Mostrar timestamp de última vela (actual) solo cada 10 ejecuciones
                    if self.contador % 10 == 1:
                        ultima_vela_time = df.index[-1].strftime('%Y-%m-%d %H:%M:%S')
                        self.log_message(f"  Vela actual: {ultima_vela_time}", symbol_short)
                    
                    color = self.calcular_indicador_oo(df, symbol)
                
                resultados[nombre] = color
                progresos[nombre] = self.obtener_progreso_vela_actual(tf)
                
                # Log con color solo cada 10 ejecuciones
                if self.contador % 10 == 1:
                    if "VERDE" in color:
                        self.log_message(f"{nombre.upper():>4} → {color}", 'VERDE')
                    elif "ROJO" in color:
                        self.log_message(f"{nombre.upper():>4} → {color}", 'ROJO')
                    else:
                        self.log_message(f"{nombre.upper():>4} → {color}", 'ERROR')
                    
            except Exception as e:
                error_msg = f"ERROR: {str(e)}"
                resultados[nombre] = error_msg
                progresos[nombre] = "N/A"
                if self.contador % 10 == 1:
                    self.log_message(f"{nombre.upper():>4} → {error_msg}", 'ERROR')
        
        if self.contador % 10 == 1:
            self.log_message("-" * 50, symbol_short)
            
            # Mostrar progreso de velas actuales
            self.log_message("📈 PROGRESO VELAS ACTUALES:", symbol_short)
            for tf, progreso in progresos.items():
                self.log_message(f"  {tf.upper():>4} → {progreso}", symbol_short)
        
        return resultados, progresos

    def generar_señal_trading(self, resultados, symbol):
        """Genera señal de trading basada en los 3 timeframes"""
        verdes = sum(1 for c in resultados.values() if "VERDE" in c)
        rojos = sum(1 for c in resultados.values() if "ROJO" in c)
        
        symbol_short = symbol.replace('-USD', '')
        
        # Solo log cada 10 ejecuciones para no saturar
        if self.contador % 10 == 1:
            self.log_message(f"🎯 {symbol_short} - SEÑAL: {verdes}/3 VERDE | {rojos}/3 ROJO", symbol_short)
        
        if verdes == 3:
            if self.contador % 10 == 1:
                self.log_message(f"🚀 {symbol_short} - ENTRADA COMPRA - Todos timeframes VERDE", 'VERDE')
            return "COMPRA_FUERTE 🚀"
        elif rojos == 3:
            if self.contador % 10 == 1:
                self.log_message(f"🔻 {symbol_short} - ENTRADA VENTA - Todos timeframes ROJO", 'ROJO') 
            return "VENTA_FUERTE 🔻"
        elif verdes == 2:
            if self.contador % 10 == 1:
                self.log_message(f"📈 {symbol_short} - SESIÓN ALCISTA - Mayoría VERDE", 'VERDE')
            return "TENDENCIA_ALCISTA 📈"
        elif rojos == 2:
            if self.contador % 10 == 1:
                self.log_message(f"📉 {symbol_short} - SESIÓN BAJISTA - Mayoría ROJO", 'ROJO')
            return "TENDENCIA_BAJISTA 📉"
        else:
            if self.contador % 10 == 1:
                self.log_message(f"⚡ {symbol_short} - MERCADO INDECISO - Señales mixtas", 'WARNING')
            return "CONSOLIDACIÓN ⚡"

# ============= INICIALIZACIÓN =============
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()