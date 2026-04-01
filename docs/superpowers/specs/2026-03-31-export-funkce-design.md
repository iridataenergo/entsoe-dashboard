# Export funkce -- Design Spec

**Datum:** 2026-03-31
**Účel:** Přidání exportu dat a grafů z dashboardu ve formátech XLSX, CSV a PDF.

---

## Architektura

Nový soubor `export.py` v kořeni projektu (vedle `config.py`) s hlavní funkcí `render_export_sidebar()`.

Každá stránka zavolá tuto funkci a předá jí:
- **dict s DataFramy** -- pojmenované datasety dané stránky
- **list Plotly figur** -- pro PDF export
- **metadata** -- název stránky, výchozí období

### Sidebar UI

Exportní sekce v sidebaru každé stránky:

1. `st.divider()` + `st.caption("📥 Export dat")`
2. Radio: "Filtrovaná data (aktuální pohled)" / "Surová data (kompletní dataset)"
3. Pokud surová → multiselect dostupných datasetů pro danou stránku
4. Pokud filtrovaná → automaticky se použijí datasety z grafů
5. Date range pro zúžení období (default = období z hlavního filtru)
6. Výběr formátu (radio: XLSX / CSV / PDF / PNG)
   - PDF a PNG dostupné pouze pro filtrovaná data
7. Tlačítko "Stáhnout" → `st.download_button`

---

## Exportní formáty

### XLSX
- Jeden soubor, každý vybraný dataset = samostatný list (sheet)
- Název listu = název datasetu (např. "Ceny elektřiny")
- Záhlaví sloupců tučně, formátování datumů na český formát
- Generuje `openpyxl` přes `pandas.ExcelWriter`

### CSV
- Jeden dataset → jeden CSV soubor
- Více datasetů → ZIP archiv s CSV soubory pojmenovanými podle datasetů
- Encoding UTF-8 s BOM (aby Excel správně zobrazil diakritiku)

### PDF
- Každý graf z aktuální stránky jako PNG obrázek (přes Kaleido)
- Obrázky spojené do jednoho PDF (jedna stránka = jeden graf)
- Titulní stránka s názvem sekce, obdobím a datem exportu
- Knihovna `fpdf2`

### PNG
- Každý graf jako samostatný PNG obrázek (přes Kaleido)
- Jeden graf → jeden PNG soubor
- Více grafů → ZIP archiv s PNG soubory pojmenovanými podle grafů

### Názvy souborů

`{nazev_stranky}_{datum_od}_{datum_do}.{xlsx|csv|zip|pdf|png}`

---

## Surová vs. filtrovaná data

**Filtrovaná data:**
- Přesně to, co stránka aktuálně zobrazuje (po aplikaci všech filtrů)
- Období v export sekci defaultně odpovídá období z hlavního filtru, uživatel ho může zúžit

**Surová data:**
- Načtení přímo z parquet souborů v `data/cache/`
- Mapování per stránka -- `export.py` ví, které cache soubory patří ke které stránce (definováno při volání)
- Období v export sekci filtruje i surová data

**Omezení:** PDF a PNG export je dostupný pouze pro filtrovaná data (exportuje aktuální grafy). U surových dat se nabídne jen XLSX/CSV.

---

## Závislosti

Nové položky v `requirements.txt`:
- `fpdf2` -- generování PDF
- `openpyxl` -- XLSX export

---

## Integrace do stránek

Každá stránka na konci sidebar bloku přidá volání:

```python
from export import render_export_sidebar

render_export_sidebar(
    nazev_stranky="Elektřina",
    filtrovana_data={"Ceny elektřiny": df_ceny, "Zatížení": df_load, "Výroba": df_vyroba},
    surova_data_soubory={"Ceny CZ": "ceny_CZ.parquet", "Zatížení": "load_actual.parquet", ...},
    grafy=[fig_ceny, fig_load, fig_vyroba],
    datum_od=datum_od,
    datum_do=datum_do,
)
```

Žádné změny v `config.py` ani `fetch_data.py` -- export modul je čistě prezentační vrstva.

---

## Testování

Manuální ověření:
- Stáhnout XLSX -- zkontrolovat listy, formátování, diakritiku
- Stáhnout CSV (jeden i více datasetů) -- ověřit encoding, ZIP archiv
- Stáhnout PDF -- ověřit grafy jako obrázky, titulní stránku
- Ověřit přepínání filtrovaná/surová data
- Ověřit zúžení období v exportu
