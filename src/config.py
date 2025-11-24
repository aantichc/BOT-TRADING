# Archivo: config.py
API_KEY = "F9D9iYQqpiQvZ7FqSuaGugeN1I4QfnBTMnro1SGrga84PZeC7SpXFHiwqkWBkGlo"
API_SECRET = "yAseWTGu6vFlPKyIGkhttip23lcLVsvnybOgflFSt23EE1RjVg0mzdtTE84DBVNY"
TRADING_ENABLED = True  # True para trades reales, False para simular
SYMBOLS = ["BNBUSDC", "FETUSDC", "SOLUSDC", "LINKUSDC", "XLMUSDC"]  # Ej. 4 símbolos → 25% max cada uno
TIMEFRAMES = {"30m": "30m", "1h": "1h", "2h": "2h"}
TIMEFRAME_WEIGHTS = {"30m": 0.30, "1h": 0.30, "2h": 0.40}
UPDATE_INTERVAL = 10  # Segundos para check señales
MIN_TRADE_DIFF = 1.0  # Mínima diferencia USD para trade (evita fees en pequeños)