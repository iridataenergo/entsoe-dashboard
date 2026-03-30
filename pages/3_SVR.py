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
