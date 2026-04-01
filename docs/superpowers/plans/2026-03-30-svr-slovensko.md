# SVR Slovensko Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new SVR (balancing services) dashboard page for Slovakia with three interactive charts (activated energy, contracted reserves, imbalance) and incremental data fetching.

**Architecture:** Extend `fetch_data.py` with incremental SVR data fetching functions that download data month-by-month with pauses. Add `pages/3_SVR.py` as a new Streamlit page with Plotly charts, checkboxes for filtering products (aFRR+/-, mFRR+/-), and a synchronizable time range selector.

**Tech Stack:** Python, Streamlit, entsoe-py, pandas, Plotly Express, parquet

---

### Task 1: Add SVR data fetching to fetch_data.py

**Files:**
- Modify: `fetch_data.py`

- [ ] **Step 1: Add import for time module**

At the top of `fetch_data.py`, after the existing imports, add:

```python
import time
```

- [ ] **Step 2: Add the SVR fetch section at the end of fetch_data.py**

Before the final `print("\n✓ Hotovo ...")` line, add the SVR data fetching block. This fetches three datasets for Slovakia incrementally (month-by-month with 2s pauses, appending to existing parquet files):

```python
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
```

**Note on contracted reserves:** The `query_contracted_reserve_prices()` method requires `process_type` and `type_marketagreement_type` parameters that vary by product type (FCR, aFRR, mFRR) and contract duration (daily, weekly, monthly, yearly). We will add this in a follow-up task after verifying which parameter combinations return data for Slovakia. For now, the three datasets above (activated energy, imbalance prices, imbalance volumes) provide the core SVR view.

- [ ] **Step 3: Commit**

```bash
git add fetch_data.py
git commit -m "feat: add SVR balancing data fetching for Slovakia (incremental, month-by-month)"
```

---

### Task 2: Update GitHub Action to include SVR fetch

**Files:**
- Modify: `.github/workflows/fetch_data.yml`

- [ ] **Step 1: Add SVR parquet files to git add**

In `fetch_data.yml`, change the `git add` line from:

```yaml
          git add data/cache/
```

This already covers all files in `data/cache/`, so no change is needed. The new SVR parquet files will be picked up automatically.

- [ ] **Step 2: Verify the workflow handles the longer fetch time**

The SVR fetch adds ~30s (2s pause × ~15 months of data on first run, but only seconds on daily runs). GitHub Actions default timeout is 6 hours, so no change is needed.

- [ ] **Step 3: Commit** (skip — no changes needed to the workflow file)

---

### Task 3: Create the SVR page — data loading and sidebar

**Files:**
- Create: `pages/3_SVR.py`

- [ ] **Step 1: Create the page file with imports, data loading, and sidebar**

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import timedelta

MESICE = {
    1: "ledna", 2: "února", 3: "března", 4: "dubna",
    5: "května", 6: "června", 7: "července", 8: "srpna",
    9: "září", 10: "října", 11: "listopadu", 12: "prosince"
}


def format_datum(d):
    return f"{d.day}. {MESICE[d.month]} {d.year}"


def cz_osa_x(fig):
    fig.update_xaxes(tickformat="%d. %m. %Y")
    fig.update_traces(
        hovertemplate="%{x|%d. %m. %Y %H:%M}<br>%{y:.2f}<extra></extra>"
    )
    return fig


st.set_page_config(
    page_title="SVR Slovensko",
    page_icon="⚖️",
    layout="wide"
)

cache_slozka = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")

# --- Načtení dat ---
def nacti_svr(nazev_souboru):
    soubor = os.path.join(cache_slozka, nazev_souboru)
    if os.path.exists(soubor):
        df = pd.read_parquet(soubor)
        if df.index.tz is None:
            df.index = pd.to_datetime(df.index).tz_localize("Europe/Prague")
        return df
    return None

df_aktivace = nacti_svr("svr_aktivace_sk.parquet")
df_imbalance_ceny = nacti_svr("svr_imbalance_ceny_sk.parquet")
df_imbalance_objemy = nacti_svr("svr_imbalance_objemy_sk.parquet")

# Kontrola dat
if df_aktivace is None and df_imbalance_ceny is None:
    st.error("SVR data nejsou k dispozici. Spusťte fetch_data.py.")
    st.stop()

# Najdi společný rozsah dat
vsechny_indexy = []
for df in [df_aktivace, df_imbalance_ceny, df_imbalance_objemy]:
    if df is not None and len(df) > 0:
        vsechny_indexy.extend([df.index.min(), df.index.max()])

min_datum = min(vsechny_indexy).date()
max_datum = max(vsechny_indexy).date()
pocet_dni_celkem = (max_datum - min_datum).days + 1

# --- Sidebar ---
with st.sidebar:
    st.header("Nastavení")

    st.caption("📅 Časové období:")
    rozsah = st.slider(
        "Rozsah dní",
        min_value=0,
        max_value=pocet_dni_celkem - 1,
        value=(max(0, pocet_dni_celkem - 30), pocet_dni_celkem - 1),
        format="%d",
        key="svr_rozsah",
    )

    datum_od_slider = min_datum + timedelta(days=rozsah[0])
    datum_do_slider = min_datum + timedelta(days=rozsah[1])

    st.caption("nebo zadej přesné datum:")
    datum_od = st.date_input("Od", value=datum_od_slider, min_value=min_datum, max_value=max_datum, key="svr_od")
    datum_do = st.date_input("Do", value=datum_do_slider, min_value=min_datum, max_value=max_datum, key="svr_do")

    if datum_od > datum_do:
        st.error("Datum Od musí být před datem Do.")
        st.stop()

    st.caption(f"Zobrazeno: {(datum_do - datum_od).days + 1} dní")

    st.divider()

    st.caption("📊 Zobrazení sekcí:")
    zobrazit_metriky = st.checkbox("Souhrnné metriky", value=True, key="svr_metriky")
    zobrazit_aktivace = st.checkbox("Graf aktivací", value=True, key="svr_graf_aktivace")
    zobrazit_imbalance = st.checkbox("Graf nerovnováhy", value=True, key="svr_graf_imbalance")

# Filtrace
od = pd.Timestamp(datum_od, tz="Europe/Prague")
do = pd.Timestamp(datum_do, tz="Europe/Prague") + pd.Timedelta(days=1)


def filtruj(df):
    if df is None:
        return None
    return df[(df.index >= od) & (df.index < do)]


akt_filtr = filtruj(df_aktivace)
imb_ceny_filtr = filtruj(df_imbalance_ceny)
imb_obj_filtr = filtruj(df_imbalance_objemy)
```

- [ ] **Step 2: Commit**

```bash
git add pages/3_SVR.py
git commit -m "feat: add SVR page skeleton with data loading and sidebar"
```

---

### Task 4: Add header, metrics, and activated energy chart

**Files:**
- Modify: `pages/3_SVR.py`

- [ ] **Step 1: Add the page header, metrics, and first chart**

Append to `pages/3_SVR.py`:

```python
# --- Hlavička ---
st.title("⚖️ SVR — Služby výkonovej rovnováhy (Slovensko)")
st.caption(f"Zdroj dat: ENTSO-E Transparency Platform | {format_datum(datum_od)} — {format_datum(datum_do)}")
st.info(
    "📌 **Služby výkonovej rovnováhy (SVR / PpS)** zajišťuje SEPS jako slovenský TSO. "
    "Zahrnují primární (FCR), sekundární (aFRR) a terciární (mFRR) regulaci frekvence. "
    "Od konce 2024 je Slovensko připojeno k evropským platformám PICASSO (aFRR) a MARI (mFRR), "
    "kde se vyvažovací energie obchoduje s marginálním oceňováním."
)

st.divider()

# --- Metriky ---
if zobrazit_metriky:
    col1, col2, col3, col4 = st.columns(4)

    if akt_filtr is not None and len(akt_filtr) > 0:
        # Hledáme sloupce s cenami — názvy závisí na API odpovědi
        akt_cols = akt_filtr.columns.tolist()
        prumer_aktivace = akt_filtr.mean().mean()
        max_aktivace = akt_filtr.max().max()
        col1.metric("Průměr aktivací", f"{prumer_aktivace:.1f} EUR/MWh")
        col2.metric("Max cena aktivace", f"{max_aktivace:.1f} EUR/MWh")
    else:
        col1.metric("Průměr aktivací", "N/A")
        col2.metric("Max cena aktivace", "N/A")

    if imb_ceny_filtr is not None and len(imb_ceny_filtr) > 0:
        max_imb = imb_ceny_filtr.max().max()
        prumer_imb = imb_ceny_filtr.mean().mean()
        col3.metric("Max cena nerovnováhy", f"{max_imb:.1f} EUR/MWh")
        col4.metric("Průměr nerovnováhy", f"{prumer_imb:.1f} EUR/MWh")
    else:
        col3.metric("Max cena nerovnováhy", "N/A")
        col4.metric("Průměr nerovnováhy", "N/A")

    st.divider()

# --- Graf 1: Aktivovaná vyvažovací energie ---
if zobrazit_aktivace:
    st.subheader("Ceny aktivované vyvažovací energie")

    if akt_filtr is not None and len(akt_filtr) > 0:
        akt_cols = akt_filtr.columns.tolist()

        # Checkboxy pro filtrování produktů
        st.caption("Zobrazit produkty:")
        vybrane_akt = []
        cols_check = st.columns(min(len(akt_cols), 6))
        for i, col_name in enumerate(akt_cols):
            with cols_check[i % len(cols_check)]:
                if st.checkbox(str(col_name), value=True, key=f"akt_{col_name}"):
                    vybrane_akt.append(col_name)

        if vybrane_akt:
            df_plot = akt_filtr[vybrane_akt]
            fig_akt = px.line(
                df_plot,
                labels={"value": "EUR/MWh", "index": "Čas", "variable": "Produkt"},
            )
            fig_akt = cz_osa_x(fig_akt)
            fig_akt.update_layout(height=500, legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig_akt, use_container_width=True)
        else:
            st.warning("Vyber alespoň jeden produkt.")
    else:
        st.warning("Data aktivací nejsou k dispozici pro vybrané období.")

    st.divider()
```

- [ ] **Step 2: Commit**

```bash
git add pages/3_SVR.py
git commit -m "feat: add SVR metrics and activated energy chart"
```

---

### Task 5: Add imbalance chart

**Files:**
- Modify: `pages/3_SVR.py`

- [ ] **Step 1: Add the imbalance chart section**

Append to `pages/3_SVR.py`:

```python
# --- Graf 2: Nerovnováha ---
if zobrazit_imbalance:
    st.subheader("Ceny nerovnováhy (imbalance)")

    if imb_ceny_filtr is not None and len(imb_ceny_filtr) > 0:
        imb_cols = imb_ceny_filtr.columns.tolist()

        st.caption("Zobrazit sloupce:")
        vybrane_imb = []
        cols_check_imb = st.columns(min(len(imb_cols), 6))
        for i, col_name in enumerate(imb_cols):
            with cols_check_imb[i % len(cols_check_imb)]:
                if st.checkbox(str(col_name), value=True, key=f"imb_{col_name}"):
                    vybrane_imb.append(col_name)

        if vybrane_imb:
            fig_imb = px.line(
                imb_ceny_filtr[vybrane_imb],
                labels={"value": "EUR/MWh", "index": "Čas", "variable": "Typ"},
            )
            fig_imb = cz_osa_x(fig_imb)
            fig_imb.update_layout(height=500, legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig_imb, use_container_width=True)

        # Volitelně objemy
        if imb_obj_filtr is not None and len(imb_obj_filtr) > 0:
            with st.expander("📊 Zobrazit objemy nerovnováhy"):
                fig_obj = px.bar(
                    imb_obj_filtr,
                    labels={"value": "MWh", "index": "Čas", "variable": "Typ"},
                )
                fig_obj = cz_osa_x(fig_obj)
                fig_obj.update_layout(height=400, legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(fig_obj, use_container_width=True)
    else:
        st.warning("Data nerovnováhy nejsou k dispozici pro vybrané období.")
```

- [ ] **Step 2: Commit**

```bash
git add pages/3_SVR.py
git commit -m "feat: add imbalance prices and volumes chart to SVR page"
```

---

### Task 6: Test locally and verify data structure

**Files:**
- No files changed — verification only

- [ ] **Step 1: Run fetch_data.py locally to test SVR fetch**

This requires an ENTSO-E API token. Set it in `.env`:
```
ENTSOE_TOKEN=your_token_here
```

Then run:
```bash
python fetch_data.py
```

Expected: SVR data files created in `data/cache/`:
- `svr_aktivace_sk.parquet`
- `svr_imbalance_ceny_sk.parquet`
- `svr_imbalance_objemy_sk.parquet`

- [ ] **Step 2: Check the column names in downloaded data**

```bash
python -c "
import pandas as pd
for f in ['svr_aktivace_sk', 'svr_imbalance_ceny_sk', 'svr_imbalance_objemy_sk']:
    path = f'data/cache/{f}.parquet'
    try:
        df = pd.read_parquet(path)
        print(f'{f}: columns={list(df.columns)}, shape={df.shape}')
        print(df.head(2))
        print()
    except Exception as e:
        print(f'{f}: {e}')
"
```

If column names are different from expected, update the checkbox labels and metric calculations in `pages/3_SVR.py` accordingly.

- [ ] **Step 3: Run the dashboard locally**

```bash
streamlit run dashboard.py
```

Navigate to the SVR page and verify:
- Metrics display correctly
- Charts render with correct data
- Checkboxes filter products
- Time range slider works
- Sections can be hidden via sidebar checkboxes

- [ ] **Step 4: Commit any fixes from testing**

```bash
git add pages/3_SVR.py fetch_data.py
git commit -m "fix: adjust SVR page based on actual API data structure"
```

---

### Task 7: Add contracted reserves (follow-up)

**Files:**
- Modify: `fetch_data.py`
- Modify: `pages/3_SVR.py`

This task is deferred until Task 6 is complete, because `query_contracted_reserve_prices()` and `query_contracted_reserve_amount()` require specific `process_type` and `type_marketagreement_type` parameters. We need to test which combinations return data for Slovakia.

- [ ] **Step 1: Test which process_type / marketagreement_type combinations work for SK**

```bash
python -c "
from entsoe import EntsoePandasClient
from dotenv import load_dotenv
import os, pandas as pd
load_dotenv()
client = EntsoePandasClient(api_key=os.getenv('ENTSOE_TOKEN'))
SK = '10YSK-SEPS-----K'
start = pd.Timestamp('2025-03-01', tz='UTC')
end = pd.Timestamp('2025-03-08', tz='UTC')

# process_type: A47=daily, A46=weekly, A45=monthly, A44=yearly
# type_marketagreement_type: A01=daily, A02=weekly, A03=monthly, A04=yearly, A13=reserve
for pt in ['A44', 'A45', 'A46', 'A47']:
    for ma in ['A01', 'A02', 'A03', 'A04', 'A13']:
        try:
            df = client.query_contracted_reserve_prices(SK, process_type=pt, type_marketagreement_type=ma, start=start, end=end)
            if len(df) > 0:
                print(f'process_type={pt}, market_agreement={ma}: {df.shape}, cols={list(df.columns)[:3]}')
        except:
            pass
"
```

- [ ] **Step 2: Add working combinations to fetch_data.py**

Based on results from Step 1, add fetch calls similar to the pattern in Task 1.

- [ ] **Step 3: Add reserves chart to SVR page**

Add a new section between the activated energy chart and the imbalance chart:

```python
# --- Graf: Zakontraktované rezervy ---
if zobrazit_rezervy:
    st.subheader("Zakontraktované rezervy")
    # ... similar pattern to activated energy chart
```

- [ ] **Step 4: Commit**

```bash
git add fetch_data.py pages/3_SVR.py
git commit -m "feat: add contracted reserves data and chart to SVR page"
```
