# SVR (Sluzby Vykonove Rovnovahy) — Slovensko

## Prehled

Nova stranka dashboardu zobrazujici data o vyvazovacich sluzbach na Slovensku (SEPS). Stranka obsahuje tri interaktivni grafy s moznosti filtrovani a skryvani, souhrnne metriky a flexibilni vyber casoveho obdobi.

## Datove zdroje

Vsechna data pochazi z ENTSO-E Transparency Platform pres knihovnu `entsoe-py`.
Oblast: `10YSK-SEPS-----K` (Slovensko / SEPS).

### Soubory v data/cache/

| Soubor | Zdroj (entsoe-py metoda) | Obsah |
|--------|--------------------------|-------|
| `svr_aktivace_sk.parquet` | `query_activated_balancing_energy_prices()` | Ceny aktivovane vyvazovaci energie (aFRR+, aFRR-, mFRR+, mFRR-) |
| `svr_rezervy_sk.parquet` | `query_contracted_reserve_prices()` + `query_contracted_reserve_amount()` | Ceny a objemy zakontraktovanych rezerv (FCR, aFRR+/-, mFRR+/-) |
| `svr_imbalance_sk.parquet` | `query_imbalance_prices()` | Ceny a objemy nerovnovahy |

### Inkrementalni stahovani

- **Prvni run:** Stahne data od 1.1.2025 po mesicich, pauza 2s mezi requesty (ochrana pred API limitem).
- **Denni run (GitHub Action):** Zkontroluje posledni datum v parquetu, stahne jen chybejici dny. Existujici data se neprepisuji.
- **Budouci rozsireni:** Postupne rozsirit na 3 roky historie (2022-2025).

## Stranka pages/3_SVR.py

### Sidebar — Casovy vyber

- Range slider + date picker (stejny vzor jako stranka Elektrina)
- Checkbox "Synchronizovat obdobi":
  - Zaskrtnuto (vychozi): jeden sdileny slider pro vsechny grafy
  - Odskrtnuto: kazdy graf ma vlastni nezavisly slider

### Metriky (skrytitelne pres checkbox)

Souhrnne karty na vrchu stranky:
- Prumerna cena aFRR+
- Prumerna cena mFRR+
- Max cena nerovnovahy
- Celkovy objem aktivaci

### Graf 1 — Aktivovana vyvazovaci energie (skrytitelny)

- **Typ:** Carovy graf (Plotly Express)
- **Data:** Ceny aktivovane energie v case
- **Filtrovani:** Checkboxy pro aFRR+, aFRR-, mFRR+, mFRR-
- **Barvy:** Zelena pro kladnou regulaci (+), cervena pro zapornou (-)
- **Interakce:** Zoom, hover s detaily

### Graf 2 — Zakontraktovane rezervy (skrytitelny)

- **Typ:** Carovy/sloupcovy graf (Plotly Express)
- **Data:** Objemy a ceny zakontraktovanych rezerv
- **Filtrovani:** Checkboxy pro FCR, aFRR+, aFRR-, mFRR+, mFRR-
- **Interakce:** Zoom, hover s detaily

### Graf 3 — Nerovnovaha (skrytitelny)

- **Typ:** Carovy graf cen nerovnovahy
- **Data:** Ceny nerovnovahy + volitelne objemy (sloupcovy prekryv)
- **Interakce:** Zoom, hover s detaily

## Vizualni styl

- Konzistentni s existujicimi strankami (Elektrina, Plyn)
- Plotly Express grafy
- Ceske popisky, format dat `%d. %m. %Y`
- Casova zona: Europe/Prague (shodna s existujicim dashboardem)
- Barevne schema: zelena (+) / cervena (-) pro regulacni smery

## Technicke poznamky

- Zadne nove Python zavislosti (entsoe-py, pandas, plotly uz jsou v requirements.txt)
- GitHub Action fetch_data.yml — rozsirit o volani SVR fetch funkci
- ENTSO-E API limit: 400 requestu/min — pauza 2s mezi requesty zajistuje bezpecnost
