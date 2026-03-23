import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import timedelta, date

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
        hovertemplate="%{x|%d. %m. %Y}<br>%{y:.1f}<extra></extra>"
    )
    return fig

st.set_page_config(
    page_title="ČR Elektro Dashboard",
    page_icon="⚡",
    layout="wide"
)

cache_slozka = r"C:\Users\IvaRichterová\Desktop\entsoe-dashboard\data\cache"

ZEME_NAZVY = {
    "CZ": "Česká republika",
    "DE": "Německo",
    "AT": "Rakousko",
    "SK": "Slovensko",
    "PL": "Polsko",
    "FR": "Francie",
}

# Načtení dat
ceny = {}
for kod in ZEME_NAZVY:
    soubor = os.path.join(cache_slozka, f"ceny_{kod}.parquet")
    if os.path.exists(soubor):
        ceny[kod] = pd.read_parquet(soubor).iloc[:, 0]
load_actual = pd.read_parquet(os.path.join(cache_slozka, "load_actual.parquet"))
load_forecast = pd.read_parquet(os.path.join(cache_slozka, "load_forecast.parquet"))
vyroba = pd.read_parquet(os.path.join(cache_slozka, "vyroba_cz.parquet"))

# Rozsah dostupných dat
min_datum = ceny["CZ"].index.min().date()
max_datum = ceny["CZ"].index.max().date()
pocet_dni_celkem = (max_datum - min_datum).days + 1

# ── Postranní panel ──────────────────────────────────────────
with st.sidebar:
    st.header("Nastavení")

    st.caption("Země pro srovnání cen:")
    dostupne_zeme = list(ceny.keys())
    vybrane_zeme = []
    for kod in dostupne_zeme:
        if st.checkbox(ZEME_NAZVY[kod], value=(kod == "CZ"), key=f"zeme_{kod}"):
            vybrane_zeme.append(kod)
            
    if not vybrane_zeme:
        st.error("Vyber alespoň jednu zemi.")
        st.stop()

    st.divider()
    st.caption("Vyber rozsah dat:")

    # Posuvník s dvojitým táhlem — vrací (od, do) jako indexy dní
    rozsah = st.slider(
        "Rozsah dní",
        min_value=0,
        max_value=pocet_dni_celkem - 1,
        value=(pocet_dni_celkem - 7, pocet_dni_celkem - 1),
        format="%d",
    )

    # Převod indexů na datumy
    datum_od_slider = min_datum + timedelta(days=rozsah[0])
    datum_do_slider = min_datum + timedelta(days=rozsah[1])

    st.caption("nebo zadej přesné datum:")

    # Datumová pole — výchozí hodnota z posuvníku
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

# ── Filtrování ───────────────────────────────────────────────
od = pd.Timestamp(datum_od, tz="Europe/Prague")
do = pd.Timestamp(datum_do, tz="Europe/Prague") + pd.Timedelta(days=1)

def filtruj(serie):
    return serie[(serie.index >= od) & (serie.index < do)]

ceny_cz = filtruj(ceny["CZ"])
load_actual_filtr = load_actual[(load_actual.index >= od) & (load_actual.index < do)]
load_forecast_filtr = load_forecast[(load_forecast.index >= od) & (load_forecast.index < do)]
vyroba_filtr = vyroba[(vyroba.index >= od) & (vyroba.index < do)]

# ── Nadpis ───────────────────────────────────────────────────
st.title("⚡ ČR Elektro-tržní dashboard")
st.caption(f"Zdroj dat: ENTSO-E | {format_datum(datum_od)} — {format_datum(datum_do)}")

# ── Metriky ──────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Průměrná cena ČR", f"{ceny_cz.mean():.1f} EUR/MWh")
col2.metric("Max cena ČR", f"{ceny_cz.max():.1f} EUR/MWh")
col3.metric("Min cena ČR", f"{ceny_cz.min():.1f} EUR/MWh")
col4.metric("Hodin nad 100 EUR", f"{(ceny_cz > 100).sum()}")

st.divider()

# ── Graf cen ─────────────────────────────────────────────────
st.subheader("Spotové ceny elektřiny — srovnání zemí")
df_ceny = pd.DataFrame({
    ZEME_NAZVY[k]: filtruj(ceny[k]) for k in vybrane_zeme if k in ceny
})
fig_ceny = px.line(df_ceny, labels={"value": "EUR/MWh", "index": "Čas", "variable": "Země"})
fig_ceny.add_hline(y=ceny_cz.mean(), line_dash="dash",
    annotation_text=f"průměr ČR {ceny_cz.mean():.1f}")
fig_ceny = cz_osa_x(fig_ceny)
st.plotly_chart(fig_ceny, use_container_width=True)

st.divider()

# ── Graf zatížení ────────────────────────────────────────────
st.subheader("Zatížení soustavy — ČR")
df_load = pd.DataFrame({
    "Skutečná spotřeba": load_actual_filtr["Actual Load"],
    "Předpověď": load_forecast_filtr["Forecasted Load"],
})
fig_load = px.line(df_load, labels={"value": "MW", "index": "Čas", "variable": ""})
fig_load.update_yaxes(tickformat=",.2f")
fig_load = cz_osa_x(fig_load)
st.plotly_chart(fig_load, use_container_width=True)

st.divider()

# ── Graf výroby ──────────────────────────────────────────────
st.subheader("Výroba podle zdrojů — ČR")
vyroba_clean = vyroba_filtr.xs("Actual Aggregated", axis=1, level=1)
nazvy = {
    "Biomass": "Biomasa", "Fossil Brown coal/Lignite": "Hnědé uhlí",
    "Fossil Coal-derived gas": "Uhelný plyn", "Fossil Gas": "Zemní plyn",
    "Fossil Hard coal": "Černé uhlí", "Fossil Oil": "Ropa",
    "Hydro Pumped Storage": "Přečerpávací voda",
    "Hydro Run-of-river and poundage": "Průtočná voda",
    "Hydro Water Reservoir": "Vodní nádrž", "Nuclear": "Jádro",
    "Other": "Ostatní", "Other renewable": "Ostatní OZE",
    "Solar": "Solár", "Waste": "Odpad", "Wind Onshore": "Vítr",
}
vyroba_clean = vyroba_clean.rename(columns=nazvy)
fig_vyroba = px.area(vyroba_clean,
    labels={"value": "MW", "index": "Čas", "variable": "Zdroj"})
fig_vyroba = cz_osa_x(fig_vyroba)
st.plotly_chart(fig_vyroba, use_container_width=True)