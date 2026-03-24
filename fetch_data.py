import os
import pandas as pd
from entsoe import EntsoePandasClient
from dotenv import load_dotenv

# Token — lokálně z .env, v GitHub Actions z proměnné prostředí
load_dotenv()
TOKEN = os.getenv("ENTSOE_TOKEN")

if not TOKEN:
    raise ValueError("ENTSOE_TOKEN není nastaven")

client = EntsoePandasClient(api_key=TOKEN)

# Rozsah dat — posledních 30 dní
konec = pd.Timestamp.now(tz="UTC").floor("h")
zacatek = konec - pd.Timedelta(days=30)

ZEME = {
    "CZ": "10YCZ-CEPS-----N",
    "DE": "10Y1001A1001A82H",
    "AT": "10YAT-APG------L",
    "SK": "10YSK-SEPS-----K",
    "PL": "10YPL-AREA-----S",
    "FR": "10YFR-RTE------C",
}

# Složka pro data
os.makedirs("data/cache", exist_ok=True)

# 1. Spotové ceny pro všechny země
print("Stahuji spotové ceny...")
for kod, eic in ZEME.items():
    try:
        data = client.query_day_ahead_prices(
            country_code=eic,
            start=zacatek,
            end=konec,
        )
        data.tz_convert("Europe/Prague").to_frame().to_parquet(
            f"data/cache/ceny_{kod}.parquet"
        )
        print(f"  ✓ {kod}: {len(data)} hodnot")
    except Exception as e:
        print(f"  ✗ {kod}: {e}")

# 2. Zatížení soustavy
print("Stahuji zatížení soustavy...")
try:
    load_actual = client.query_load(
        country_code=ZEME["CZ"],
        start=zacatek,
        end=konec,
    )
    load_actual.tz_convert("Europe/Prague").to_parquet("data/cache/load_actual.parquet")
    print(f"  ✓ Actual load: {len(load_actual)} hodnot")
except Exception as e:
    print(f"  ✗ Actual load: {e}")

try:
    load_forecast = client.query_load_forecast(
        country_code=ZEME["CZ"],
        start=zacatek,
        end=konec,
    )
    load_forecast.tz_convert("Europe/Prague").to_parquet("data/cache/load_forecast.parquet")
    print(f"  ✓ Forecast load: {len(load_forecast)} hodnot")
except Exception as e:
    print(f"  ✗ Forecast load: {e}")

# 3. Výroba podle zdrojů
print("Stahuji výrobu podle zdrojů...")
try:
    vyroba = client.query_generation(
        country_code=ZEME["CZ"],
        start=zacatek,
        end=konec,
    )
    vyroba.tz_convert("Europe/Prague").to_parquet("data/cache/vyroba_cz.parquet")
    print(f"  ✓ Výroba: {vyroba.shape[0]} řádků, {vyroba.shape[1]} zdrojů")
except Exception as e:
    print(f"  ✗ Výroba: {e}")

# 4. TTF ceny plynu
print("Stahuji TTF ceny plynu...")
try:
    import yfinance as yf
    ttf = yf.download("TTF=F", period="60d", interval="1d", auto_adjust=True, progress=False)
    ttf = ttf[["Close"]].rename(columns={"Close": "TTF_EUR_MWh"})
    ttf.to_parquet("data/cache/ttf_plyn.parquet")
    print(f"  ✓ TTF: {len(ttf)} hodnot")
except Exception as e:
    print(f"  ✗ TTF: {e}")

print("\n✓ Hotovo — všechna data uložena do data/cache/")