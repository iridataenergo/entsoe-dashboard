import os
import sys
import shutil
import tempfile
import pandas as pd
from entsoe import EntsoePandasClient
from dotenv import load_dotenv
import time

# Workaround: curl SSL fails when certifi path contains non-ASCII characters (e.g. diacritics in username)
try:
    import certifi
    _cert_path = certifi.where()
    if not _cert_path.isascii():
        _tmp_cert = os.path.join(tempfile.gettempdir(), "cacert.pem")
        shutil.copy2(_cert_path, _tmp_cert)
        os.environ["CURL_CA_BUNDLE"] = _tmp_cert
        os.environ["SSL_CERT_FILE"] = _tmp_cert
except Exception:
    pass

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

# 4. TTF ceny plynu — maximální dostupná historie
print("Stahuji TTF ceny plynu (celá historie)...")
try:
    import yfinance as yf
    ttf = yf.download("TTF=F", period="max", interval="1d", auto_adjust=True, progress=False)
    if isinstance(ttf.columns, pd.MultiIndex):
        ttf.columns = ttf.columns.get_level_values(0)
    ttf = ttf[["Close"]].rename(columns={"Close": "TTF_EUR_MWh"})
    ttf.to_parquet("data/cache/ttf_plyn.parquet")
    print(f"  ✓ TTF: {len(ttf)} hodnot ({ttf.index.min().date()} — {ttf.index.max().date()})")
except Exception as e:
    print(f"  ✗ TTF: {e}")

# 5. Naplněnost zásobníků plynu — GIE AGSI API (EU agregát)
print("Stahuji naplněnost zásobníků plynu...")
try:
    import requests
    # Volné API bez tokenu pro agregovaná EU data
    url = "https://agsi.gie.eu/api"
    params = {
        "country": "eu",
        "size": 300,  # posledních 300 dní
    }
    headers = {"x-key": os.getenv("GIE_API_KEY", "")}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    df_agsi = pd.DataFrame(data["data"])
    df_agsi["gasDayStart"] = pd.to_datetime(df_agsi["gasDayStart"])
    df_agsi = df_agsi.set_index("gasDayStart").sort_index()
    # Ponecháme klíčové sloupce
    sloupce = [c for c in ["full", "trend", "injection", "withdrawal", "workingGasVolume"] if c in df_agsi.columns]
    df_agsi = df_agsi[sloupce].apply(pd.to_numeric, errors="coerce")
    df_agsi.to_parquet("data/cache/zasobniky_eu.parquet")
    print(f"  ✓ Zásobníky EU: {len(df_agsi)} hodnot")
except Exception as e:
    print(f"  ✗ Zásobníky EU: {e}")

# 6. SVR — Služby výkonovej rovnováhy (Slovensko)
print("Stahuji SVR data pro Slovensko...")

SK = ZEME["SK"]
SVR_SOUBORY = {
    "aktivace": "data/cache/svr_aktivace_sk.parquet",
    "imbalance_ceny": "data/cache/svr_imbalance_ceny_sk.parquet",
    "imbalance_objemy": "data/cache/svr_imbalance_objemy_sk.parquet",
}

# Výchozí start — 1.1.2025, nebo poslední datum v existujícím souboru
SVR_VYCHOZI_START = pd.Timestamp("2025-01-01", tz="UTC")


def svr_posledni_datum(soubor):
    """Vrátí poslední datum v parquet souboru, nebo None pokud neexistuje."""
    if os.path.exists(soubor):
        df = pd.read_parquet(soubor)
        if len(df) > 0:
            idx = df.index.max()
            if idx.tzinfo is None:
                idx = idx.tz_localize("UTC")
            return idx
    return None


def svr_uloz_inkrementalne(soubor, nova_data):
    """Přidá nová data k existujícímu parquet souboru bez duplikátů."""
    if os.path.exists(soubor):
        existujici = pd.read_parquet(soubor)
        sloupceno = pd.concat([existujici, nova_data])
        sloupceno = sloupceno[~sloupceno.index.duplicated(keep="last")]
        sloupceno.sort_index().to_parquet(soubor)
    else:
        nova_data.sort_index().to_parquet(soubor)


def svr_stahni_po_mesicich(nazev, soubor, fetch_fn):
    """Stáhne data po měsících od posledního data v souboru do teď."""
    posledni = svr_posledni_datum(soubor)
    if posledni is not None:
        start = posledni + pd.Timedelta(hours=1)
    else:
        start = SVR_VYCHOZI_START

    konec_svr = pd.Timestamp.now(tz="UTC").floor("h")

    if start >= konec_svr:
        print(f"  ⏭ {nazev}: data jsou aktuální")
        return

    # Stahuj po měsících
    mesic_start = start
    celkem = 0
    while mesic_start < konec_svr:
        mesic_konec = min(mesic_start + pd.DateOffset(months=1), konec_svr)
        try:
            data = fetch_fn(mesic_start, mesic_konec)
            if data is not None and len(data) > 0:
                if isinstance(data, pd.Series):
                    data = data.to_frame()
                if data.index.tz is not None:
                    data.index = data.index.tz_convert("Europe/Prague")
                else:
                    data.index = data.index.tz_localize("UTC").tz_convert("Europe/Prague")
                svr_uloz_inkrementalne(soubor, data)
                celkem += len(data)
        except Exception as e:
            print(f"  ⚠ {nazev} ({mesic_start.strftime('%Y-%m')}): {e}")
        mesic_start = mesic_konec
        time.sleep(2)

    print(f"  ✓ {nazev}: {celkem} nových hodnot")


# 6a. Ceny aktivované vyvažovací energie
svr_stahni_po_mesicich(
    "Aktivovaná energie",
    SVR_SOUBORY["aktivace"],
    lambda s, e: client.query_activated_balancing_energy_prices(SK, start=s, end=e),
)

# 6b. Ceny nerovnováhy
svr_stahni_po_mesicich(
    "Ceny nerovnováhy",
    SVR_SOUBORY["imbalance_ceny"],
    lambda s, e: client.query_imbalance_prices(SK, start=s, end=e),
)

# 6c. Objemy nerovnováhy
svr_stahni_po_mesicich(
    "Objemy nerovnováhy",
    SVR_SOUBORY["imbalance_objemy"],
    lambda s, e: client.query_imbalance_volumes(SK, start=s, end=e),
)

# 6d. Zakontraktované rezervy — aFRR (A51) a mFRR (A47), denní kontrakty
# Pozor: v ENTSO-E API je A47=mFRR, A51=aFRR, A52=FCR (entsoe-py má špatné komentáře)
REZERVY_KONFIG = [
    ("aFRR", "A51", "data/cache/svr_rezervy_afrr_sk.parquet"),
    ("mFRR", "A47", "data/cache/svr_rezervy_mfrr_sk.parquet"),
]

for rez_nazev, rez_pt, rez_soubor in REZERVY_KONFIG:
    def fetch_rezervy(s, e, pt=rez_pt):
        prices = client.query_contracted_reserve_prices(
            SK, process_type=pt, type_marketagreement_type="A01", start=s, end=e
        )
        amounts = client.query_contracted_reserve_amount(
            SK, process_type=pt, type_marketagreement_type="A01", start=s, end=e
        )
        # Spojíme ceny a objemy do jednoho DataFrame
        result = pd.DataFrame(index=prices.index)
        for col in prices.columns:
            result[f"{col}_Price"] = prices[col]
            result[f"{col}_Volume"] = amounts[col]
        return result

    svr_stahni_po_mesicich(
        f"Rezervy {rez_nazev}",
        rez_soubor,
        fetch_rezervy,
    )

print("\n✓ Hotovo — všechna data uložena do data/cache/")