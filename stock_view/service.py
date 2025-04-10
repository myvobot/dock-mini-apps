import random
import arequests as request

_STOCK_API_URL = "" # Server URL, needs to be configured
_USE_SIMULATED_DATA = True # Whether to use simulated stock information

def generate_mock_stock_info(symbols):
    # Generate simulated stock information
    res = {"stocks": []}
    for symbol in symbols:
        item = {
            'previousClose': random.randint(400, 450),
            'currentPrice': random.randint(400, 450),
            'currency': 'USD'
        }
        item["symbol"], item["shortName"] = symbol.split(":")
        res["stocks"].append(item)
    return res

async def fetch_stock_info(symbols="MSFT"):
    # Fetch stock information
    url = f"{_STOCK_API_URL}?symbols={symbols}"

    try:
        response = await request.request("GET", url)
        if response.status_code == 200: return await response.json()
    except Exception as e:
        pass

    return {}

async def get_stock_details(symbols):
    # Fetch stock details information
    details = []
    if not symbols: return details

    if _USE_SIMULATED_DATA:
        res = generate_mock_stock_info(symbols)
    else:
        res = await fetch_stock_info(",".join(symbols))

    for index, item in enumerate(res.get("stocks", [])):
        # No symbol field in data? Get from symbols
        if item.get("symbol", None) is None:
            item["symbol"], item["shortName"] = symbols[index].split(":")
        details.append(item)

    return details
