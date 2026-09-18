import requests, os, json
from dotenv import load_dotenv
load_dotenv()

BASE = "https://stock.arjum.com"
HEADERS = {
    "X-API-Key": os.getenv("ARJUNA_API_KEY"),
    "Accept": "application/json"
}

endpoints = [
    "/api/screener/latest",
    "/api/analysis/BBCA",
    "/api/broker-summary/BBCA",
    "/api/broker-accumulation/BBCA",
    "/api/history/BBCA",
    "/api/market-cap",
    "/api/financial-statements/BBCA",
    "/api/done-details",
]

output = []
for ep in endpoints:
    res = requests.get(BASE + ep, headers=HEADERS)
    block = f"\n=== {ep} === [{res.status_code}]\n"
    try:
        data = res.json()
        if isinstance(data, list):
            block += json.dumps(data[:2], indent=2)
        else:
            block += json.dumps(data, indent=2)
    except:
        block += res.text[:500]
    output.append(block)
    print(f"Done: {ep}")

with open("test_arjum_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("\nHasil disimpan ke test_arjum_result.txt")
