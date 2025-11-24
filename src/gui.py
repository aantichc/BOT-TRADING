# src/gui.py - VERSIÓN DEFINITIVA CON HISTORIAL, SMOOTH Y SELECTOR DE TIMEFRAME
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
import json
import os
from scipy.interpolate import make_interp_spline
import numpy as np

HISTORY_FILE = "capital_history.json"
CHART_FILE = "capital_chart.png"

class TradingGUI:
    def __init__(self, bot):
        self.bot = bot
        self.bot.gui = self
        self.update_job = None

        self.root = tk.Tk()
        self.root.title("TRADING BOT - HISTORIAL + SMOOTH + TIMEFRAMES")
        self.root.geometry("1500x950")
        self.root.configure(bg="#0a0a0a")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Cargar historial
        self.history = self.load_history()

        # === BOTONES + SELECTOR TIMEFRAME ===
        top = tk.Frame(self.root, bg="#0a0a0a")
        top.pack(pady=15)

        tk.Button(top, text="START", bg="#00ff00", fg="black", font=("Arial",14,"bold"), width=12, command=self.bot.start).pack(side=tk.LEFT, padx=10)
        tk.Button(top, text="STOP", bg="#ff3333", fg="white", font=("Arial",14,"bold"), width=12, command=self.bot.stop).pack(side=tk.LEFT, padx=10)
        tk.Button(top, text="REBALANCE", bg="#ffaa00", fg="black", font=("Arial",14,"bold"), width=15, command=self.bot.rebalance_manual).pack(side=tk.LEFT, padx=10)

        tk.Label(top, text="Timeframe:", bg="#0a0a0a", fg="#00ff00", font=("Arial",12,"bold")).pack(side=tk.LEFT, padx=(30,5))
        self.tf_var = tk.StringVar(value="30m")
        tf_options = ["15m", "30m", "1h", "2h", "4h", "1D", "1W"]
        ttk.Combobox(top, textvariable=self.tf_var, values=tf_options, width=8, state="readonly", font=("Consolas",11)).pack(side=tk.LEFT)

        main = tk.Frame(self.root, bg="#0a0a0a")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # === IZQUIERDA: TOKENS ===
        left = tk.Frame(main, bg="#0a0a0a")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.token_frames = {}
        from config import SYMBOLS
        for i, symbol in enumerate(SYMBOLS[:6]):
            r, c = i // 2, i % 2
            frame = self.create_token_box(left, symbol)
            frame.grid(row=r, column=c, padx=20, pady=20, sticky="nsew")
            self.token_frames[symbol] = frame
        for i in range(2): left.grid_columnconfigure(i, weight=1)
        for i in range(3): left.grid_rowconfigure(i, weight=1)

        # === DERECHA: LOGS + GRÁFICO ===
        right = tk.Frame(main, bg="#0a0a0a")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(30,0))

        tk.Label(right, text="TRADES EN VIVO", bg="#0a0a0a", fg="#00ff00", font=("Arial",16,"bold")).pack(anchor="w", pady=(0,10))
        self.log_text = tk.Text(right, height=12, bg="#111111", fg="#ffffff", font=("Consolas",11))
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0,15))

        self.fig, self.ax = plt.subplots(figsize=(11,6), facecolor="#0a0a0a")
        self.ax.set_facecolor("#111111")
        self.ax.tick_params(colors='gray')
        self.ax.spines['bottom'].set_color('gray')
        self.ax.spines['left'].set_color('gray')
        self.canvas = FigureCanvasTkAgg(self.fig, right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.schedule_update()
        self.root.mainloop()

    def create_token_box(self, parent, symbol):
        frame = tk.Frame(parent, bg="#1a1a1a", relief="flat", bd=2, highlightbackground="#333", highlightthickness=2)
        frame.configure(width=340, height=240)
        frame.pack_propagate(False)

        tk.Label(frame, text=symbol.replace("USDC", ""), bg="#1a1a1a", fg="#00ffaa", font=("Arial",22,"bold")).pack(pady=(15,5))
        price_lbl = tk.Label(frame, text="$0.0000", bg="#1a1a1a", fg="white", font=("Arial",15))
        price_lbl.pack(pady=(0,8))
        balance_lbl = tk.Label(frame, text="0.000000 → $0 (0.0%)", bg="#1a1a1a", fg="#bbbbbb", font=("Arial",11))
        balance_lbl.pack(pady=(0,15))

        semaforo_frame = tk.Frame(frame, bg="#1a1a1a")
        semaforo_frame.pack()
        canvas = tk.Canvas(semaforo_frame, width=40, height=110, bg="#1a1a1a", highlightthickness=0)
        canvas.grid(row=0, column=0, rowspan=3)
        c30 = canvas.create_oval(8, 8, 32, 32, fill="gray", outline="#555")
        c1h = canvas.create_oval(8, 45, 32, 69, fill="gray", outline="#555")
        c2h = canvas.create_oval(8, 82, 32, 106, fill="gray", outline="#555")
        tk.Label(semaforo_frame, text="30m", bg="#1a1a1a", fg="#888", font=("Consolas",10)).grid(row=0, column=1, sticky="w", padx=8)
        tk.Label(semaforo_frame, text="1h ", bg="#1a1a1a", fg="#888", font=("Consolas",10)).grid(row=1, column=1, sticky="w", padx=8)
        tk.Label(semaforo_frame, text="2h ", bg="#1a1a1a", fg="#888", font=("Consolas",10)).grid(row=2, column=1, sticky="w", padx=8)

        peso_lbl = tk.Label(frame, text="Peso: 0.00", bg="#1a1a1a", fg="yellow", font=("Arial",14,"bold"))
        peso_lbl.pack(pady=(12,0))

        frame.data = {
            "symbol": symbol, "price_lbl": price_lbl, "balance_lbl": balance_lbl,
            "canvas": canvas, "circles": {"30m": c30, "1h": c1h, "2h": c2h}, "peso_lbl": peso_lbl
        }
        return frame

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                return [(datetime.fromisoformat(d[0]), d[1]) for d in data]
        return []

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump([(dt.isoformat(), val) for dt, val in self.history], f)
        # Guardar gráfico
        self.fig.savefig(CHART_FILE, dpi=150, facecolor="#0a0a0a")

    def log_trade(self, msg, color="white"):
        ts = datetime.now().strftime("%H:%M:%S")
        tag = "green" if color == 'GREEN' else "red" if color == 'RED' else "white"
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n", tag)
        self.log_text.tag_config("green", foreground="#00ff88")
        self.log_text.tag_config("red", foreground="#ff4444")
        self.log_text.see(tk.END)

    def schedule_update(self):
        if self.update_job:
            self.root.after_cancel(self.update_job)
        self.update_job = self.root.after(5000, self.update_ui)
    def update_ui(self):
        try:
            if not self.bot.running:
                self.schedule_update()
                return

            total_usd = self.bot.account.get_balance_usdc()
            now = datetime.now()
            self.history.append((now, total_usd))
            self.save_history()  # Guarda cada 5 segundos

            # IMPORT LOCAL PARA timedelta (FIX DEL ERROR)
            from datetime import timedelta

            # Filtrar por timeframe
            tf = self.tf_var.get()
            cutoff = now
            if tf == "15m": cutoff = now - timedelta(minutes=15)
            elif tf == "30m": cutoff = now - timedelta(minutes=30)
            elif tf == "1h": cutoff = now - timedelta(hours=1)
            elif tf == "2h": cutoff = now - timedelta(hours=2)
            elif tf == "4h": cutoff = now - timedelta(hours=4)
            elif tf == "1D": cutoff = now - timedelta(days=1)
            elif tf == "1W": cutoff = now - timedelta(weeks=1)

            filtered = [(t, v) for t, v in self.history if t >= cutoff]
            if not filtered:
                filtered = self.history[-1:]

            times, values = zip(*filtered)
            self.ax.clear()
            if len(times) > 3:
                x_num = np.array([t.timestamp() for t in times])
                x_smooth = np.linspace(x_num.min(), x_num.max(), 300)
                spl = make_interp_spline(x_num, values, k=3)
                y_smooth = spl(x_smooth)
                smooth_times = [datetime.fromtimestamp(ts) for ts in x_smooth]
                self.ax.plot(smooth_times, y_smooth, color="#00ff88", linewidth=3)
            else:
                self.ax.plot(times, values, color="#00ff88", linewidth=3)

            self.ax.set_title(f"Capital Total: ${total_usd:,.2f}", color="white", fontsize=16)
            self.ax.set_facecolor("#111111")
            self.ax.grid(True, alpha=0.2, color="#333")
            self.canvas.draw()

            # Actualizar tokens
            for frame in self.token_frames.values():
                d = frame.data
                symbol = d["symbol"]
                try:
                    signals = self.bot.manager.get_signals(symbol)
                    weight = self.bot.manager.calculate_weight(signals)
                    price = self.bot.account.get_current_price(symbol)
                    balance = self.bot.account.get_symbol_balance(symbol)
                    usd = balance * price
                    pct = (usd / total_usd * 100) if total_usd > 0 else 0

                    d["price_lbl"].config(text=f"${price:,.4f}")
                    d["balance_lbl"].config(text=f"{balance:.6f} → ${usd:,.0f} ({pct:.1f}%)")

                    for tf_t, cid in d["circles"].items():
                        col = {"GREEN": "#00ff00", "YELLOW": "#ffff00", "RED": "#ff0000"}.get(signals.get(tf_t), "gray")
                        d["canvas"].itemconfig(cid, fill=col)

                    color = "#00ff00" if weight >= 0.8 else "#ffff00" if weight >= 0.5 else "#ff8800" if weight >= 0.3 else "#ff4444"
                    d["peso_lbl"].config(text=f"Peso: {weight:.2f}", fg=color)
                except Exception as e:
                    print(f"Error updating {symbol}: {e}")  # Debug temporal

        except Exception as e:
            print(f"Error in update_ui: {e}")  # Debug temporal

        self.schedule_update()
        
    def on_close(self):
        if self.update_job:
            self.root.after_cancel(self.update_job)
        self.save_history()
        self.bot.stop()
        self.root.destroy()