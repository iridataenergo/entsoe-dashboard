# Export funkce Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add data and chart export (XLSX, CSV, PNG, PDF) via a centralized sidebar module to all dashboard pages.

**Architecture:** A single `export.py` module provides `render_export_sidebar()` which each page calls at the end of its sidebar block. The module handles all format generation internally. Pages pass their filtered DataFrames, raw data file mappings, and Plotly figures.

**Tech Stack:** pandas + openpyxl (XLSX), fpdf2 (PDF), kaleido (PNG — already installed), Streamlit download_button

---

### Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add fpdf2 and openpyxl to requirements.txt**

Add these two lines at the end of `requirements.txt`:

```
fpdf2
openpyxl
```

- [ ] **Step 2: Install dependencies**

Run: `pip install fpdf2 openpyxl`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add fpdf2 and openpyxl dependencies for export"
```

---

### Task 2: Create export.py — XLSX and CSV generation

**Files:**
- Create: `export.py`

- [ ] **Step 1: Create export.py with XLSX generation function**

```python
import io
import zipfile
from datetime import date

import pandas as pd
import streamlit as st


def _generuj_xlsx(datasety: dict[str, pd.DataFrame]) -> bytes:
    """Generuje XLSX soubor s jedním listem na dataset."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nazev, df in datasety.items():
            # Název listu max 31 znaků (Excel limit)
            sheet_name = nazev[:31]
            df_out = df.copy()
            # Pokud je index datetime, převeď na tz-naive pro Excel kompatibilitu
            if hasattr(df_out.index, "tz") and df_out.index.tz is not None:
                df_out.index = df_out.index.tz_localize(None)
            df_out.to_excel(writer, sheet_name=sheet_name)
            # Tučné záhlaví
            ws = writer.sheets[sheet_name]
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)
    return buffer.getvalue()
```

- [ ] **Step 2: Add CSV generation function**

Append to `export.py`:

```python
def _generuj_csv(datasety: dict[str, pd.DataFrame]) -> tuple[bytes, str]:
    """Generuje CSV. Jeden dataset = CSV, více = ZIP. Vrací (bytes, přípona)."""
    if len(datasety) == 1:
        nazev, df = next(iter(datasety.items()))
        df_out = df.copy()
        if hasattr(df_out.index, "tz") and df_out.index.tz is not None:
            df_out.index = df_out.index.tz_localize(None)
        csv_bytes = df_out.to_csv().encode("utf-8-sig")
        return csv_bytes, "csv"

    # Více datasetů → ZIP
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nazev, df in datasety.items():
            df_out = df.copy()
            if hasattr(df_out.index, "tz") and df_out.index.tz is not None:
                df_out.index = df_out.index.tz_localize(None)
            csv_data = df_out.to_csv().encode("utf-8-sig")
            zf.writestr(f"{nazev}.csv", csv_data)
    return buffer.getvalue(), "zip"
```

- [ ] **Step 3: Verify module imports correctly**

Run: `python -c "from export import _generuj_xlsx, _generuj_csv; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add export.py
git commit -m "feat: add XLSX and CSV generation functions in export module"
```

---

### Task 3: Add PNG and PDF generation to export.py

**Files:**
- Modify: `export.py`

- [ ] **Step 1: Add PNG generation function**

Append to `export.py`:

```python
def _generuj_png(grafy: list, nazvy_grafu: list[str]) -> tuple[bytes, str]:
    """Generuje PNG. Jeden graf = PNG, více = ZIP. Vrací (bytes, přípona)."""
    if len(grafy) == 1:
        png_bytes = grafy[0].to_image(format="png", width=1200, height=600, scale=2)
        return png_bytes, "png"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for fig, nazev in zip(grafy, nazvy_grafu):
            png_bytes = fig.to_image(format="png", width=1200, height=600, scale=2)
            zf.writestr(f"{nazev}.png", png_bytes)
    return buffer.getvalue(), "zip"
```

- [ ] **Step 2: Add PDF generation function**

Append to `export.py`:

```python
from fpdf import FPDF
import tempfile
import os


def _generuj_pdf(
    grafy: list,
    nazvy_grafu: list[str],
    nazev_stranky: str,
    datum_od: date,
    datum_do: date,
) -> bytes:
    """Generuje PDF s titulní stránkou a grafy jako obrázky."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")

    # Titulní stránka
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 40, txt=nazev_stranky, ln=True, align="C")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(
        0, 10,
        txt=f"Obdobi: {datum_od.strftime('%d. %m. %Y')} - {datum_do.strftime('%d. %m. %Y')}",
        ln=True, align="C",
    )
    pdf.cell(
        0, 10,
        txt=f"Exportovano: {date.today().strftime('%d. %m. %Y')}",
        ln=True, align="C",
    )

    # Grafy
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, (fig, nazev) in enumerate(zip(grafy, nazvy_grafu)):
            png_path = os.path.join(tmpdir, f"graf_{i}.png")
            fig.to_image(format="png", width=1200, height=600, scale=2)
            fig.write_image(png_path, width=1200, height=600, scale=2)
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, txt=nazev, ln=True, align="C")
            # A4 landscape: 297x210mm, s okraji
            pdf.image(png_path, x=10, y=25, w=277)

    return bytes(pdf.output())
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from export import _generuj_png, _generuj_pdf; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add export.py
git commit -m "feat: add PNG and PDF generation functions in export module"
```

---

### Task 4: Create the sidebar render function in export.py

**Files:**
- Modify: `export.py`

- [ ] **Step 1: Add render_export_sidebar function**

Append to `export.py`:

```python
def render_export_sidebar(
    nazev_stranky: str,
    filtrovana_data: dict[str, pd.DataFrame],
    surova_data_soubory: dict[str, str],
    grafy: list,
    nazvy_grafu: list[str],
    datum_od: date,
    datum_do: date,
    cache_slozka: str = None,
):
    """Renderuje exportní sekci v sidebaru."""
    if cache_slozka is None:
        cache_slozka = os.path.join(os.path.dirname(__file__), "data", "cache")

    with st.sidebar:
        st.divider()
        st.caption("📥 Export dat")

        # 1. Typ dat
        typ_dat = st.radio(
            "Zdroj dat",
            ["Filtrovaná data (aktuální pohled)", "Surová data (kompletní dataset)"],
            key=f"export_typ_{nazev_stranky}",
        )
        je_surova = typ_dat.startswith("Surová")

        # 2. Výběr datasetů (jen pro surová data)
        if je_surova:
            vybrane_datasety = st.multiselect(
                "Datasety",
                list(surova_data_soubory.keys()),
                default=list(surova_data_soubory.keys()),
                key=f"export_ds_{nazev_stranky}",
            )
        else:
            vybrane_datasety = list(filtrovana_data.keys())

        # 3. Období
        st.caption("Zúžit období exportu:")
        export_od = st.date_input(
            "Export od", value=datum_od,
            min_value=datum_od, max_value=datum_do,
            key=f"export_od_{nazev_stranky}",
        )
        export_do = st.date_input(
            "Export do", value=datum_do,
            min_value=datum_od, max_value=datum_do,
            key=f"export_do_{nazev_stranky}",
        )

        # 4. Formát
        dostupne_formaty = ["XLSX", "CSV"]
        if not je_surova:
            dostupne_formaty.extend(["PDF", "PNG"])
        format_export = st.radio(
            "Formát", dostupne_formaty,
            key=f"export_fmt_{nazev_stranky}",
        )

        # 5. Připrav data
        nazev_souboru_base = f"{nazev_stranky}_{export_od.strftime('%Y%m%d')}_{export_do.strftime('%Y%m%d')}"

        if st.button("📥 Stáhnout", key=f"export_btn_{nazev_stranky}", use_container_width=True):
            with st.spinner("Generuji export..."):
                od_ts = pd.Timestamp(export_od, tz="Europe/Prague")
                do_ts = pd.Timestamp(export_do, tz="Europe/Prague") + pd.Timedelta(days=1)

                # Sestav datasety
                if je_surova:
                    datasety = {}
                    for nazev in vybrane_datasety:
                        soubor = surova_data_soubory[nazev]
                        cesta = os.path.join(cache_slozka, soubor)
                        if os.path.exists(cesta):
                            df = pd.read_parquet(cesta)
                            if hasattr(df.index, "tz") and df.index.tz is None:
                                df.index = pd.to_datetime(df.index).tz_localize("Europe/Prague")
                            datasety[nazev] = df[(df.index >= od_ts) & (df.index < do_ts)]
                else:
                    datasety = {}
                    for nazev, df in filtrovana_data.items():
                        if hasattr(df.index, "tz") and df.index.tz is not None:
                            datasety[nazev] = df[(df.index >= od_ts) & (df.index < do_ts)]
                        else:
                            od_naive = pd.Timestamp(export_od)
                            do_naive = pd.Timestamp(export_do) + pd.Timedelta(days=1)
                            datasety[nazev] = df[(df.index >= od_naive) & (df.index < do_naive)]

                if not datasety and format_export in ("XLSX", "CSV"):
                    st.error("Žádná data k exportu.")
                    return

                # Generuj soubor
                if format_export == "XLSX":
                    data = _generuj_xlsx(datasety)
                    st.download_button(
                        "💾 Uložit XLSX", data,
                        file_name=f"{nazev_souboru_base}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{nazev_stranky}_xlsx",
                    )
                elif format_export == "CSV":
                    data, ext = _generuj_csv(datasety)
                    mime = "text/csv" if ext == "csv" else "application/zip"
                    st.download_button(
                        "💾 Uložit CSV", data,
                        file_name=f"{nazev_souboru_base}.{ext}",
                        mime=mime,
                        key=f"dl_{nazev_stranky}_csv",
                    )
                elif format_export == "PNG":
                    data, ext = _generuj_png(grafy, nazvy_grafu)
                    mime = "image/png" if ext == "png" else "application/zip"
                    st.download_button(
                        "💾 Uložit PNG", data,
                        file_name=f"{nazev_souboru_base}.{ext}",
                        mime=mime,
                        key=f"dl_{nazev_stranky}_png",
                    )
                elif format_export == "PDF":
                    data = _generuj_pdf(grafy, nazvy_grafu, nazev_stranky, export_od, export_do)
                    st.download_button(
                        "💾 Uložit PDF", data,
                        file_name=f"{nazev_souboru_base}.pdf",
                        mime="application/pdf",
                        key=f"dl_{nazev_stranky}_pdf",
                    )
```

- [ ] **Step 2: Verify full module loads**

Run: `python -c "from export import render_export_sidebar; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add export.py
git commit -m "feat: add render_export_sidebar function for sidebar export UI"
```

---

### Task 5: Integrate export into 1_Elektrina.py

**Files:**
- Modify: `pages/1_Elektrina.py`

- [ ] **Step 1: Add import at top of file**

After the existing imports (line 4), add:

```python
from export import render_export_sidebar
```

- [ ] **Step 2: Store figures and call render_export_sidebar**

The page already creates `fig_ceny`, `fig_load`, `fig_vyroba`. After the last `st.plotly_chart` call (end of file, line 164), append:

```python
# --- Export ---
render_export_sidebar(
    nazev_stranky="Elektrina",
    filtrovana_data={
        "Ceny elektřiny": df_ceny,
        "Zatížení soustavy": df_load,
        "Výroba podle zdrojů": vyroba_clean,
    },
    surova_data_soubory={
        "Ceny CZ": "ceny_CZ.parquet",
        "Ceny DE": "ceny_DE.parquet",
        "Ceny AT": "ceny_AT.parquet",
        "Ceny SK": "ceny_SK.parquet",
        "Ceny PL": "ceny_PL.parquet",
        "Zatížení skutečné": "load_actual.parquet",
        "Zatížení předpověď": "load_forecast.parquet",
        "Výroba CZ": "vyroba_cz.parquet",
    },
    grafy=[fig_ceny, fig_load, fig_vyroba],
    nazvy_grafu=["Ceny elektřiny", "Zatížení soustavy", "Výroba podle zdrojů"],
    datum_od=datum_od,
    datum_do=datum_do,
)
```

- [ ] **Step 3: Run the page to verify**

Run: `streamlit run dashboard.py` and navigate to Elektřina page. Verify export section appears in sidebar.

- [ ] **Step 4: Commit**

```bash
git add pages/1_Elektrina.py
git commit -m "feat: integrate export sidebar into Elektřina page"
```

---

### Task 6: Integrate export into 2_Plyn.py

**Files:**
- Modify: `pages/2_Plyn.py`

- [ ] **Step 1: Add import at top of file**

After the existing imports (line 4), add:

```python
from export import render_export_sidebar
```

- [ ] **Step 2: Call render_export_sidebar at end of file**

After the last `st.plotly_chart` call (line 196), append:

```python
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
```

- [ ] **Step 3: Run the page to verify**

Run: `streamlit run dashboard.py` and navigate to Plyn page. Verify export section appears in sidebar.

- [ ] **Step 4: Commit**

```bash
git add pages/2_Plyn.py
git commit -m "feat: integrate export sidebar into Plyn page"
```

---

### Task 7: Integrate export into 3_SVR.py

**Files:**
- Modify: `pages/3_SVR.py`

- [ ] **Step 1: Add import at top of file**

After the existing imports (line 5), add:

```python
from export import render_export_sidebar
```

- [ ] **Step 2: Collect figures into a list as they're created**

The SVR page conditionally creates figures (`fig_up`, `fig_down`, `fig_imb`, `fig_obj`). Before the sidebar block (line 134), add:

```python
# Kolekce grafů pro export (naplní se níže)
export_grafy = []
export_nazvy_grafu = []
```

Then after each `st.plotly_chart(fig_up, ...)` call (line 255), add:

```python
                export_grafy.append(fig_up)
                export_nazvy_grafu.append("Aktivace Up")
```

After `st.plotly_chart(fig_down, ...)` (line 273), add:

```python
                export_grafy.append(fig_down)
                export_nazvy_grafu.append("Aktivace Down")
```

After `st.plotly_chart(fig_imb, ...)` (line 306), add:

```python
            export_grafy.append(fig_imb)
            export_nazvy_grafu.append("Ceny nerovnováhy")
```

After `st.plotly_chart(fig_obj, ...)` (line 319), add:

```python
                export_grafy.append(fig_obj)
                export_nazvy_grafu.append("Objemy nerovnováhy")
```

- [ ] **Step 3: Call render_export_sidebar at end of file**

At the very end of the file (after line 322), append:

```python
# --- Export ---
filtrovana = {}
if akt_pivot is not None and len(akt_pivot) > 0:
    filtrovana["Aktivace"] = akt_pivot
if imb_ceny_filtr is not None and len(imb_ceny_filtr) > 0:
    filtrovana["Ceny nerovnováhy"] = imb_ceny_filtr
if imb_obj_filtr is not None and len(imb_obj_filtr) > 0:
    filtrovana["Objemy nerovnováhy"] = imb_obj_filtr

render_export_sidebar(
    nazev_stranky="SVR",
    filtrovana_data=filtrovana,
    surova_data_soubory={
        "Aktivace SK": "svr_aktivace_sk.parquet",
        "Imbalance ceny SK": "svr_imbalance_ceny_sk.parquet",
        "Imbalance objemy SK": "svr_imbalance_objemy_sk.parquet",
    },
    grafy=export_grafy,
    nazvy_grafu=export_nazvy_grafu,
    datum_od=datum_od,
    datum_do=datum_do,
)
```

- [ ] **Step 4: Run the page to verify**

Run: `streamlit run dashboard.py` and navigate to SVR page. Verify export section appears in sidebar.

- [ ] **Step 5: Commit**

```bash
git add pages/3_SVR.py
git commit -m "feat: integrate export sidebar into SVR page"
```

---

### Task 8: Manual end-to-end testing

**Files:** None (testing only)

- [ ] **Step 1: Test XLSX export on Elektřina page**

Run `streamlit run dashboard.py`, go to Elektřina, select "Filtrovaná data", choose XLSX, click Stáhnout. Open the downloaded file — verify multiple sheets, bold headers, Czech characters.

- [ ] **Step 2: Test CSV export with multiple datasets**

Same page, select CSV. Verify ZIP file downloads with multiple CSV files. Open one — verify UTF-8 BOM, correct data.

- [ ] **Step 3: Test surová data export**

Switch to "Surová data", select a subset of datasets, choose XLSX. Verify correct sheets.

- [ ] **Step 4: Test PNG export**

Switch back to "Filtrovaná data", choose PNG. Verify ZIP with PNG images of charts.

- [ ] **Step 5: Test PDF export**

Choose PDF. Verify PDF with title page and chart images.

- [ ] **Step 6: Test on Plyn and SVR pages**

Repeat quick smoke test (one format each) on remaining pages.

- [ ] **Step 7: Commit any fixes if needed**

```bash
git add -A
git commit -m "fix: address issues found during export testing"
```
