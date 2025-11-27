import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Obtener APIs desde variables de entorno
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# Verificar que las APIs estén cargadas
if not API_KEY or not API_SECRET:
    raise ValueError("❌ No se encontraron las API keys en las variables de entorno")

TRADING_ENABLED = True
SYMBOLS = ["BNBUSDC", "FETUSDC", "SOLUSDC", "LINKUSDC", "XLMUSDC"]
TIMEFRAMES = {"30m": "30m", "1h": "1h", "2h": "2h"}
TIMEFRAME_WEIGHTS = {"30m": 0.30, "1h": 0.30, "2h": 0.40}
UPDATE_INTERVAL = 30
MIN_TRADE_DIFF = 15
DEFAULT_CHART_TIMEFRAME = "1D"