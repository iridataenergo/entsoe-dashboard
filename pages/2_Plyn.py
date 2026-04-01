import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta
from export import render_export_sidebar

MESICE = {
    1: "ledna", 2: "února", 3: "března", 4: "dubna",
    5: "května", 6: "června", 7: "července", 8: "srpna",
    9: "září", 10: "října", 11: "listopadu", 12: "prosince"
}

def format_datum(d):
    return f"{d.day}. {MESICE[d.month]} {d.year}"

def cz_osa_x(fig, fmt="%d. %m. %Y"):
    fig.update_xaxes(tickformat=fmt)
    fig.update_traces(
        hovertemplate="%{x|" + fmt + "}<br>%{y:.2f} EUR/MWh<extra></extra>"
    )
    return fig

st.set_page_config(
    page_title="ČR Plyn Dashboard",
    page_icon="🔥",
    layout="wide"
)

cache_slozka = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")

# Načtení dat
soubor_ttf = os.path.join(cache_slozka, "ttf_plyn.parquet")
if not os.path.exists(soubor_ttf):
    st.error("Data pro plyn nejsou k dispozici. Spusťte fetch_data.py.")
    st.stop()

ttf = pd.read_parquet(soubor_ttf)
ttf.index = pd.to_datetime(ttf.index)
if ttf.index.tz is not None:
    ttf.index = ttf.index.tz_localize(None)
ttf = ttf.sort_index()
ttf_serie = ttf["TTF_EUR_MWh"].dropna()

min_datum = ttf_serie.index.min().date()
max_datum = ttf_serie.index.max().date()
pocet_dni_celkem = (max_datum - min_datum).days + 1

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.header("Nastavení")

    # 1. Aktuální období (max 30 dní zpět)
    st.caption("📅 Aktuální období (max 30 dní):")
    dni_zpet = st.slider(
        "Počet dní zpět",
        min_value=1,
        max_value=30,
        value=7,
        format="%d dní",
    )
    datum_do = max_datum
    datum_od = max_datum - timedelta(days=dni_zpet - 1)
    st.caption(f"Od: {format_datum(datum_od)} — Do: {format_datum(datum_do)}")

    st.divider()

    # 2. Historické období (měsíce)
    st.caption("📆 Historické období:")
    vsechny_mesice = pd.period_range(
        start=ttf_serie.index.min().to_period("M"),
        end=ttf_serie.index.max().to_period("M"),
        freq="M"
    )
    pocet_mesicu = len(vsechny_mesice)

    hist_rozsah = st.slider(
        "Rozsah měsíců",
        min_value=0,
        max_value=pocet_mesicu - 1,
        value=(max(0, pocet_mesicu - 36), pocet_mesicu - 1),
        format="%d",
    )
    hist_od = vsechny_mesice[hist_rozsah[0]].to_timestamp()
    hist_do = vsechny_mesice[hist_rozsah[1]].to_timestamp("M")
    st.caption(f"Od: {hist_od.strftime('%m/%Y')} — Do: {hist_do.strftime('%m/%Y')}")

# ── Filtrace ─────────────────────────────────────────────
od = pd.Timestamp(datum_od)
do = pd.Timestamp(datum_do) + pd.Timedelta(days=1)
ttf_filtr = ttf_serie[(ttf_serie.index >= od) & (ttf_serie.index < do)]
ttf_hist = ttf_serie[(ttf_serie.index >= hist_od) & (ttf_serie.index <= hist_do)]

# ── Hlavička ─────────────────────────────────────────────
st.title("🔥 Evropský trh s plynem — TTF")
st.caption(
    f"Zdroj dat: Yahoo Finance (TTF Natural Gas futures) | "
    f"{format_datum(datum_od)} — {format_datum(datum_do)}"
)
st.info(
    "📌 TTF (Title Transfer Facility) je evropský benchmark pro cenu zemního plynu. "
    "Německo, Francie, ČR i okolní země platí v zásadě TTF ± lokální distribuční poplatky — "
    "na rozdíl od elektřiny zde neexistují výrazné regionální cenové rozdíly. "
    "Zobrazená cena vychází z **TTF futures front-month kontraktu** (nejbližší expirační měsíc) — "
    "jde o denní uzavírací cenu v EUR/MWh, která odráží krátkodobá tržní očekávání "
    "a je standardem používaným energetickými analytiky i médii."
)

st.divider()

# ── Metriky ───────────────────────────────────────────────
posledni = float(ttf_filtr.iloc[-1])
predposledni = float(ttf_filtr.iloc[-2]) if len(ttf_filtr) >= 2 else None
zmena_delta = None
if predposledni and predposledni != 0:
    zmena_pct = (posledni - predposledni) / predposledni * 100
    zmena_delta = f"{zmena_pct:+.2f} %"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Poslední cena TTF", f"{posledni:.2f} EUR/MWh", delta=zmena_delta)
col2.metric("Průměr za období", f"{float(ttf_filtr.mean()):.2f} EUR/MWh")
col3.metric("Maximum za období", f"{float(ttf_filtr.max()):.2f} EUR/MWh")
col4.metric("Minimum za období", f"{float(ttf_filtr.min()):.2f} EUR/MWh")

st.divider()

# ── Graf aktuálního období ────────────────────────────────
st.subheader(f"Vývoj ceny TTF — {format_datum(datum_od)} až {format_datum(datum_do)}")
prumer = float(ttf_filtr.mean())
fig_akt = px.line(ttf_filtr, labels={"value": "EUR/MWh", "index": "Datum"})
fig_akt.update_traces(name="TTF cena")
fig_akt.add_hline(y=prumer, line_dash="dash",
    annotation_text=f"průměr {prumer:.2f} EUR/MWh")
fig_akt = cz_osa_x(fig_akt)
st.plotly_chart(fig_akt, use_container_width=True)

st.divider()

# ── Historický graf ───────────────────────────────────────
st.subheader(f"Historický vývoj TTF — {hist_od.strftime('%m/%Y')} až {hist_do.strftime('%m/%Y')}")
fig_hist = px.line(ttf_hist, labels={"value": "EUR/MWh", "index": "Datum"})
fig_hist.update_traces(name="TTF cena")

# Zvýraznění energetické krize 2021-2022
krize_od = pd.Timestamp("2021-06-01")
krize_do = pd.Timestamp("2022-12-31")
if hist_od <= krize_do and hist_do >= krize_od:
    fig_hist.add_vrect(
        x0=max(krize_od, hist_od), x1=min(krize_do, hist_do),
        fillcolor="orange", opacity=0.1,
        annotation_text="Energetická krize", annotation_position="top left"
    )

fig_hist = cz_osa_x(fig_hist, fmt="%m/%Y")
st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ── Roční průměry ─────────────────────────────────────────
st.subheader("Roční průměry TTF")
rocni = ttf_hist.resample("YE").mean().reset_index()
rocni.columns = ["Rok", "EUR/MWh"]
rocni["Rok"] = rocni["Rok"].dt.year.astype(str)
rocni["EUR/MWh"] = rocni["EUR/MWh"].round(2)

fig_rocni = px.bar(
    rocni, x="Rok", y="EUR/MWh",
    text="EUR/MWh",
    labels={"EUR/MWh": "EUR/MWh", "Rok": "Rok"},
    color="EUR/MWh",
    color_continuous_scale="RdYlGn_r",
)
fig_rocni.update_traces(texttemplate="%{text:.1f}", textposition="outside")
fig_rocni.update_coloraxes(showscale=False)
st.plotly_chart(fig_rocni, use_container_width=True)

st.divider()

# ── Sezónnost ─────────────────────────────────────────────
st.subheader("Sezónnost — průměrná cena podle měsíce")
mesicni = ttf_serie.groupby(ttf_serie.index.month).mean().reset_index()
mesicni.columns = ["Měsíc", "EUR/MWh"]
mesicni["Název"] = mesicni["Měsíc"].map({
    1: "Led", 2: "Úno", 3: "Bře", 4: "Dub", 5: "Kvě", 6: "Čvn",
    7: "Čvc", 8: "Srp", 9: "Zář", 10: "Říj", 11: "Lis", 12: "Pro"
})
fig_sezon = px.bar(
    mesicni, x="Název", y="EUR/MWh",
    text="EUR/MWh",
    labels={"EUR/MWh": "Průměr EUR/MWh", "Název": "Měsíc"},
    color="EUR/MWh",
    color_continuous_scale="RdYlGn_r",
)
fig_sezon.update_traces(texttemplate="%{text:.1f}", textposition="outside")
fig_sezon.update_coloraxes(showscale=False)
st.caption("Průměr přes celou dostupnou historii dat")
st.plotly_chart(fig_sezon, use_container_width=True)

# --- Export ---
render_export_sidebar(
    nazev_stranky="Plyn",
    filtrovana_data={
        "TTF aktuální": ttf_filtr.to_frame(name="EUR/MWh"),
        "TTF historický": ttf_hist.to_frame(name="EUR/MWh"),
        "Roční průměry": rocni.set_index("Rok"),
        "Sezónnost": mesicni.set_index("Název"),
    },
    surova_data_soubory={
        "TTF plyn": "ttf_plyn.parquet",
    },
    grafy=[fig_akt, fig_hist, fig_rocni, fig_sezon],
    nazvy_grafu=["TTF aktuální", "TTF historický", "Roční průměry", "Sezónnost"],
    datum_od=datum_od,
    datum_do=datum_do,
)