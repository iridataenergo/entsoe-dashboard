import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("ENTSOE_TOKEN")

AREAS = {
    "CZ": "10YCZ-CEPS-----N",
    "DE": "10Y1001A1001A83F",
    "AT": "10YAT-APG------L",
    "SK": "10YSK-SEPS-----K",
    "PL": "10YPL-AREA-----S",
}

DISPLAY_TZ = "Europe/Prague"
