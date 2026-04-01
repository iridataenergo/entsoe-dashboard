import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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


def cz_osa_x(fig, df_data=None):
    xargs = dict(tickformat="%d. %m. %Y")
    if df_data is not None and len(df_data) > 0:
        xargs["range"] = [df_data.index.min(), df_data.index.max()]
    fig.update_xaxes(**xargs)
    fig.update_traces(
        hovertemplate="%{x|%d. %m. %Y %H:%M}<br>%{y:.2f}<extra></extra>"
    )
    return fig


import numpy as np


def oznac_extremy(fig, df, prah_nasobek=3):
    """Nastaví výchozí zoom Y bez extrémů, přidá bubliny. Zoom/dvojklik fungují normálně."""
    vsechny = df.values.flatten()
    nenulove = vsechny[(~np.isnan(vsechny)) & (vsechny != 0)]
    if len(nenulove) < 10:
        return fig

    q1 = np.percentile(nenulove, 25)
    q3 = np.percentile(nenulove, 75)
    iqr = q3 - q1
    if iqr == 0:
        return fig

    horni_prah = q3 + prah_nasobek * iqr
    dolni_prah = q1 - prah_nasobek * iqr

    # Najdi skutečný rozsah dat (bez extrémů)
    bezne = vsechny[(~np.isnan(vsechny)) & (vsechny >= dolni_prah) & (vsechny <= horni_prah)]
    if len(bezne) == 0:
        return fig

    y_data_min = bezne.min()
    y_data_max = bezne.max()
    rozpeti = y_data_max - y_data_min if y_data_max != y_data_min else abs(y_data_max) * 0.5
    y_max = y_data_max + rozpeti * 0.15
    y_min = y_data_min - rozpeti * 0.15
    fig.update_yaxes(range=[y_min, y_max])

    # Anotace pro extrémní hodnoty
    for col in df.columns:
        serie = df[col]
        extremy = serie[(serie > horni_prah) | (serie < dolni_prah)].dropna()
        for cas, hodnota in extremy.items():
            # Bublina na okraji grafu — nahoře pro kladné, dole pro záporné
            if hodnota > horni_prah:
                pozice_y = y_max * 0.95
                ay_offset = -25
            else:
                pozice_y = y_min + abs(y_min) * 0.05
                ay_offset = 25
            barva = "#e74c3c" if hodnota > 0 else "#3498db"
            fig.add_annotation(
                x=cas,
                y=pozice_y,
                text=f"<b>{hodnota:.0f}</b>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowcolor=barva,
                font=dict(size=10, color=barva),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor=barva,
                borderwidth=1,
                borderpad=3,
                ax=0,
                ay=ay_offset,
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
df_rezervy_afrr = nacti_svr("svr_rezervy_afrr_sk.parquet")
df_rezervy_mfrr = nacti_svr("svr_rezervy_mfrr_sk.parquet")

# Kontrola dat
if df_aktivace is None and df_imbalance_ceny is None:
    st.error("SVR data nejsou k dispozici. Spusťte fetch_data.py.")
    st.stop()

# Najdi společný rozsah dat
vsechny_indexy = []
for df in [df_aktivace, df_imbalance_ceny, df_imbalance_objemy, df_rezervy_afrr, df_rezervy_mfrr]:
    if df is not None and len(df) > 0:
        vsechny_indexy.extend([df.index.min(), df.index.max()])

min_datum = min(vsechny_indexy).date()
max_datum = max(vsechny_indexy).date()
pocet_dni_celkem = (max_datum - min_datum).days + 1

# Kolekce grafů pro export
export_grafy = []
export_nazvy_grafu = []

# --- Sidebar ---
with st.sidebar:
    st.header("Nastavení")

    st.caption("📅 Časové období:")
    datum_od = st.date_input("Od", value=max_datum - timedelta(days=30), min_value=min_datum, max_value=max_datum, key="svr_od")
    datum_do = st.date_input("Do", value=max_datum, min_value=min_datum, max_value=max_datum, key="svr_do")

    if datum_od > datum_do:
        st.error("Datum Od musí být před datem Do.")
        st.stop()

    st.caption(f"Zobrazeno: {(datum_do - datum_od).days + 1} dní")

    st.divider()

    st.caption("📊 Zobrazení sekcí:")
    zobrazit_metriky = st.checkbox("Souhrnné metriky", value=True, key="svr_metriky")
    zobrazit_rezervy = st.checkbox("Grafy rezerv", value=True, key="svr_graf_rezervy")
    zobrazit_aktivace = st.checkbox("Graf aktivací", value=True, key="svr_graf_aktivace")
    zobrazit_imbalance = st.checkbox("Graf nerovnováhy", value=True, key="svr_graf_imbalance")

    st.divider()
    st.caption("🔧 Filtr produktů — aktivace:")
    vybrane_akt_sidebar = {}
    for nazev in ["aFRR Up", "aFRR Down", "mFRR Up", "mFRR Down"]:
        vybrane_akt_sidebar[nazev] = st.checkbox(nazev, value=True, key=f"akt_{nazev}")

    st.divider()
    st.caption("🔧 Filtr — nerovnováha:")
    vybrane_imb_sidebar = {}
    for nazev in ["Long", "Short"]:
        vybrane_imb_sidebar[nazev] = st.checkbox(nazev, value=True, key=f"imb_{nazev}")

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
rez_afrr_filtr = filtruj(df_rezervy_afrr)
rez_mfrr_filtr = filtruj(df_rezervy_mfrr)

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

# --- Příprava aktivačních dat ---
# Data jsou v long formátu: každý řádek = jedna aktivace (Direction, Price, ReserveType)
# Resample na hodiny, NaN = žádná aktivace = 0 EUR/MWh (žádné náklady)
akt_pivot = None
if akt_filtr is not None and len(akt_filtr) > 0 and "Price" in akt_filtr.columns:
    akt_filtr = akt_filtr.copy()
    akt_filtr["Produkt"] = akt_filtr["ReserveType"] + " " + akt_filtr["Direction"]
    akt_pivot = akt_filtr.pivot_table(index=akt_filtr.index, columns="Produkt", values="Price", aggfunc="mean")
    akt_pivot = akt_pivot.resample("1h").mean().fillna(0)

# --- Metriky ---
if zobrazit_metriky:
    col1, col2, col3, col4 = st.columns(4)

    if akt_pivot is not None and len(akt_pivot) > 0:
        prumer_aktivace = akt_pivot.mean().mean()
        max_aktivace = akt_pivot.max().max()
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

# --- Grafy rezerv ---
def graf_rezervy(df_rez, direction, nazev_sluzby):
    """Vytvoří graf se dvěma Y osami: objem (MW) + cena (EUR/MW/h) + lineární trend."""
    if df_rez is None or len(df_rez) == 0:
        return None

    price_col = f"{direction}_Price"
    volume_col = f"{direction}_Volume"
    if price_col not in df_rez.columns or volume_col not in df_rez.columns:
        return None

    # Resample na hodiny
    df_h = df_rez[[price_col, volume_col]].resample("1h").mean().dropna()
    if len(df_h) == 0:
        return None

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Objem — sloupcový graf (levá osa)
    fig.add_trace(
        go.Bar(
            x=df_h.index, y=df_h[volume_col],
            name="Objem (MW)",
            marker_color="rgba(54, 162, 235, 0.5)",
            hovertemplate="%{x|%d. %m. %Y %H:%M}<br>Objem: %{y:.1f} MW<extra></extra>",
        ),
        secondary_y=False,
    )

    # Cena — čárový graf (pravá osa)
    fig.add_trace(
        go.Scatter(
            x=df_h.index, y=df_h[price_col],
            name="Cena (EUR/MW/h)",
            mode="lines",
            line=dict(color="#ff6b35", width=2),
            hovertemplate="%{x|%d. %m. %Y %H:%M}<br>Cena: %{y:.2f} EUR/MW/h<extra></extra>",
        ),
        secondary_y=True,
    )

    # Lineární trend ceny
    x_num = np.arange(len(df_h))
    y_price = df_h[price_col].values
    mask = ~np.isnan(y_price)
    if mask.sum() > 2:
        koef = np.polyfit(x_num[mask], y_price[mask], 1)
        trend = np.polyval(koef, x_num)
        r2 = 1 - np.sum((y_price[mask] - trend[mask]) ** 2) / np.sum((y_price[mask] - np.mean(y_price[mask])) ** 2)

        fig.add_trace(
            go.Scatter(
                x=df_h.index, y=trend,
                name=f"Trend ceny (R²={r2:.3f})",
                mode="lines",
                line=dict(color="#ff6b35", width=1, dash="dot"),
                hovertemplate=f"Trend: %{{y:.2f}} EUR/MW/h<br>R²={r2:.3f}<extra></extra>",
            ),
            secondary_y=True,
        )

    dir_label = "Up (+)" if direction == "Up" else "Down (-)"
    fig.update_layout(
        title=f"{nazev_sluzby} {dir_label}",
        height=400,
        legend=dict(orientation="h", y=-0.2),
        bargap=0,
    )
    fig.update_xaxes(
        tickformat="%d. %m. %Y",
        range=[df_h.index.min(), df_h.index.max()],
    )
    fig.update_yaxes(title_text="Objem (MW)", secondary_y=False)
    fig.update_yaxes(title_text="EUR/MW/h", secondary_y=True)

    return fig


if zobrazit_rezervy:
    st.subheader("Zakontraktované rezervy")

    for df_rez, nazev in [(rez_afrr_filtr, "aFRR"), (rez_mfrr_filtr, "mFRR")]:
        if df_rez is not None and len(df_rez) > 0:
            for direction in ["Up", "Down"]:
                fig_r = graf_rezervy(df_rez, direction, nazev)
                if fig_r:
                    st.plotly_chart(fig_r, use_container_width=True)
                    export_grafy.append(fig_r)
                    export_nazvy_grafu.append(f"Rezervy {nazev} {direction}")
        else:
            st.warning(f"Data rezerv {nazev} nejsou k dispozici pro vybrané období.")

    st.divider()

# --- Graf 1: Aktivovaná vyvažovací energie ---
if zobrazit_aktivace:
    st.subheader("Ceny aktivované vyvažovací energie")

    if akt_pivot is not None and len(akt_pivot) > 0:
        vybrane_akt = [k for k, v in vybrane_akt_sidebar.items() if v and k in akt_pivot.columns]

        if vybrane_akt:
            # Rozděl na Up a Down grafy — mají úplně jiné škály
            up_cols = [c for c in vybrane_akt if "Up" in c]
            down_cols = [c for c in vybrane_akt if "Down" in c]

            if up_cols:
                st.caption("Kladná regulace (Up)")
                df_up = akt_pivot[up_cols]
                fig_up = px.line(
                    df_up,
                    labels={"value": "EUR/MWh", "index": "Čas", "variable": "Produkt"},
                    render_mode="svg",
                )
                fig_up = cz_osa_x(fig_up, df_up)
                fig_up.update_traces(
                    mode="markers+lines",
                    marker=dict(size=3),
                    line=dict(shape="spline", smoothing=0.8),
                )
                fig_up = oznac_extremy(fig_up, df_up)
                fig_up.update_layout(height=400, legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(fig_up, use_container_width=True)
                export_grafy.append(fig_up)
                export_nazvy_grafu.append("Aktivace Up")

            if down_cols:
                st.caption("Záporná regulace (Down)")
                df_down = akt_pivot[down_cols]
                fig_down = px.line(
                    df_down,
                    labels={"value": "EUR/MWh", "index": "Čas", "variable": "Produkt"},
                    render_mode="svg",
                )
                fig_down = cz_osa_x(fig_down, df_down)
                fig_down.update_traces(
                    mode="markers+lines",
                    marker=dict(size=3),
                    line=dict(shape="spline", smoothing=0.8),
                )
                fig_down = oznac_extremy(fig_down, df_down)
                fig_down.update_layout(height=400, legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(fig_down, use_container_width=True)
                export_grafy.append(fig_down)
                export_nazvy_grafu.append("Aktivace Down")
        else:
            st.warning("Vyber alespoň jeden produkt.")
    else:
        st.warning("Data aktivací nejsou k dispozici pro vybrané období.")

    st.divider()

# --- Graf 2: Nerovnováha ---
if zobrazit_imbalance:
    st.subheader("Ceny nerovnováhy (imbalance)")

    if imb_ceny_filtr is not None and len(imb_ceny_filtr) > 0:
        # Resample na hodiny — průměr 15min cen za hodinu
        imb_ceny_h = imb_ceny_filtr.resample("1h").mean()
        vybrane_imb = [k for k, v in vybrane_imb_sidebar.items() if v and k in imb_ceny_h.columns]

        if vybrane_imb:
            # Bodový graf s vyhlazenou spojnicí (spline)
            df_imb_plot = imb_ceny_h[vybrane_imb]
            fig_imb = px.line(
                df_imb_plot,
                labels={"value": "EUR/MWh", "index": "Čas", "variable": "Typ"},
                render_mode="svg",
            )
            fig_imb = cz_osa_x(fig_imb, df_imb_plot)
            fig_imb.update_traces(
                mode="markers+lines",
                marker=dict(size=3),
                line=dict(shape="spline", smoothing=0.8),
            )
            fig_imb = oznac_extremy(fig_imb, df_imb_plot)
            fig_imb.update_layout(height=500, legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig_imb, use_container_width=True)
            export_grafy.append(fig_imb)
            export_nazvy_grafu.append("Ceny nerovnováhy")

        # Volitelně objemy
        if imb_obj_filtr is not None and len(imb_obj_filtr) > 0:
            # Resample na hodiny — součet objemů za hodinu
            imb_obj_h = imb_obj_filtr.resample("1h").sum()
            with st.expander("📊 Zobrazit objemy nerovnováhy"):
                fig_obj = px.bar(
                    imb_obj_h,
                    labels={"value": "MWh", "index": "Čas", "variable": "Typ"},
                )
                fig_obj = cz_osa_x(fig_obj, imb_obj_h)
                fig_obj.update_layout(height=400, legend=dict(orientation="h", y=-0.15))
                st.plotly_chart(fig_obj, use_container_width=True)
                export_grafy.append(fig_obj)
                export_nazvy_grafu.append("Objemy nerovnováhy")
    else:
        st.warning("Data nerovnováhy nejsou k dispozici pro vybrané období.")

# --- Export ---
filtrovana = {}
if rez_afrr_filtr is not None and len(rez_afrr_filtr) > 0:
    filtrovana["Rezervy aFRR"] = rez_afrr_filtr
if rez_mfrr_filtr is not None and len(rez_mfrr_filtr) > 0:
    filtrovana["Rezervy mFRR"] = rez_mfrr_filtr
if akt_pivot is not None and len(akt_pivot) > 0:
    filtrovana["Aktivace"] = akt_pivot
if imb_ceny_filtr is not None and len(imb_ceny_filtr) > 0:
    filtrovana["Ceny nerovnováhy"] = imb_ceny_filtr
if imb_obj_filtr is not None and len(imb_obj_filtr) > 0:
    filtrovana["Objemy nerovnováhy"] = imb_obj_filtr

render_export_sidebar(
    nazev_stranky="SVR (SK)",
    filtrovana_data=filtrovana,
    surova_data_soubory={
        "Rezervy aFRR SK": "svr_rezervy_afrr_sk.parquet",
        "Rezervy mFRR SK": "svr_rezervy_mfrr_sk.parquet",
        "Aktivace SK": "svr_aktivace_sk.parquet",
        "Imbalance ceny SK": "svr_imbalance_ceny_sk.parquet",
        "Imbalance objemy SK": "svr_imbalance_objemy_sk.parquet",
    },
    grafy=export_grafy,
    nazvy_grafu=export_nazvy_grafu,
    datum_od=datum_od,
    datum_do=datum_do,
)
