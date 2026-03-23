# ČR Elektro-tržní dashboard

Dashboard zobrazuje data z ENTSO-E Transparency Platform pro českou elektroenergetiku.

## Co zobrazuje
- Spotové ceny elektřiny — ČR a srovnání se sousedními zeměmi
- Zatížení soustavy — skutečná spotřeba vs předpověď
- Výroba elektřiny podle zdrojů — jádro, uhlí, OZE

## Jak spustit
1. Nainstaluj závislosti: pip install -r requirements.txt
2. Vytvoř soubor .env s ENTSO-E tokenem: ENTSOE_TOKEN=tvuj_token
3. Spusť dashboard: python -m streamlit run dashboard.py

## Zdroj dat
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu)
