import streamlit as st
import pandas as pd
import plotly.express as px
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
        hovertemplate="%{x|%d. %m. %Y}<br>%{y:.2f} EUR/MWh<extra></extra>"
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

min_datum = ttf.index.min().date()
max_datum = ttf.index.max().date()
pocet_dni_celkem = (max_datum - min_datum).days + 1

# Sidebar
with st.sidebar:
    st.header("Nastavení")
    st.divider()
    st.caption("Vyber rozsah dat:")

    rozsah = st.slider(
        "Rozsah dní",
        min_value=0,
        max_value=pocet_dni_celkem - 1,
        value=(max(0, pocet_dni_celkem - 30), pocet_dni_celkem - 1),
        format="%d",
    )

    datum_od_slider = min_datum + timedelta(days=rozsah[0])
    datum_do_slider = min_datum + timedelta(days=rozsah[1])

    st.caption("nebo zadej přesné datum:")

    datum_od = st.date_input(
        "Od",
        value=datum_od_slider,
        min_value=min_datum,
        max_value=max_datum,
    )
    datum_do = st.date_input(
        "Do",
        value=datum_do_slider,
        min_value=min_datum,
        max_value=max_datum,
    )

    if datum_od > datum_do:
        st.error("Datum Od musí být před datem Do.")
        st.stop()

    st.caption(f"Zobrazeno: {(datum_do - datum_od).days + 1} dní")

# Filtrace
od = pd.Timestamp(datum_od)
do = pd.Timestamp(datum_do) + pd.Timedelta(days=1)
ttf_filtr = ttf[(ttf.index >= od) & (ttf.index < do)]["TTF_EUR_MWh"]

# Změna oproti předchozímu dni
posledni = float(ttf_filtr.iloc[-1])
predposledni = float(ttf_filtr.iloc[-2]) if len(ttf_filtr) >= 2 else None
if predposledni is not None and predposledni != 0:
    zmena_pct = (posledni - predposledni) / predposledni * 100
    zmena_delta = f"{zmena_pct:+.2f} %"
else:
    zmena_delta = None

# Hlavička
st.title("🔥 Evropský trh s plynem — TTF")
st.caption(
    f"Zdroj dat: Yahoo Finance (TTF Natural Gas futures) | "
    f"{format_datum(datum_od)} — {format_datum(datum_do)}"
)
st.info(
    "📌 TTF (Title Transfer Facility) je evropský benchmark pro cenu zemního plynu. "
    "Německo, Francie, ČR i okolní země platí v zásadě TTF ± lokální distribuční poplatky — "
    "na rozdíl od elektřiny zde neexistují výrazné regionální cenové rozdíly.",
    icon=None
)

st.divider()

# Metriky
col1, col2, col3, col4 = st.columns(4)
col1.metric("Poslední cena TTF", f"{posledni:.2f} EUR/MWh", delta=zmena_delta)
col2.metric("Průměr za období", f"{ttf_filtr.mean():.2f} EUR/MWh")
col3.metric("Maximum za období", f"{ttf_filtr.max():.2f} EUR/MWh")
col4.metric("Minimum za období", f"{ttf_filtr.min():.2f} EUR/MWh")

st.divider()

# Graf TTF
st.subheader("Vývoj ceny TTF plynu")
fig_ttf = px.line(
    ttf_filtr,
    labels={"value": "EUR/MWh", "index": "Datum"},
)
fig_ttf.update_traces(name="TTF cena")
fig_ttf.add_hline(
    y=ttf_filtr.mean(),
    line_dash="dash",
    annotation_text=f"průměr {ttf_filtr.mean():.2f} EUR/MWh"
)
fig_ttf = cz_osa_x(fig_ttf)
st.plotly_chart(fig_ttf, use_container_width=True)