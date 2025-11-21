import sys
import os
sys.path.append('src')

def test_precision():
    from binance_account import BinanceAccount
    
    account = BinanceAccount()
    
    test_cases = [
        ("BTCUSDC", 0.00001, "5 decimales"),
        ("FETUSDC", 0.1, "1 decimal"),
        ("SOLUSDC", 0.001, "3 decimales"),
        ("XLMUSDC", 1.0, "0 decimales"),
        ("LINKUSDC", 0.01, "2 decimales")
    ]
    
    print("🔧 TEST DE PRECISIÓN")
    print("=" * 40)
    
    for symbol, step, expected in test_cases:
        precision = account.get_step_precision(step)
        print(f"{symbol}:")
        print(f"  Step: {step}")
        print(f"  Precisión calculada: {precision}")
        print(f"  Esperado: {expected}")
        print(f"  {'✅' if precision == int(expected.split()[0]) else '❌'}")
        print()

def test_quantity_format():
    from binance_account import BinanceAccount
    
    account = BinanceAccount()
    
    # Test con BTCUSDC - el problema actual
    raw_quantity = 0.0007003973
    step_size = 0.00001
    min_qty = 0.00001
    
    account.current_min_qty = min_qty
    formatted = account.format_quantity(raw_quantity, step_size)
    precision = account.get_step_precision(step_size)
    
    print("🔧 TEST BTCUSDC - FORMATO FINAL")
    print("=" * 40)
    print(f"Raw: {raw_quantity:.10f}")
    print(f"Step: {step_size}")
    print(f"Precisión: {precision}")
    print(f"Formatted: {formatted:.{precision}f}")
    print(f"Como string: '{formatted:.{precision}f}'")

if __name__ == "__main__":
    test_precision()
    test_quantity_format()