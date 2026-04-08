import os
import json
from flask import Flask, render_template
from google.oauth2.service_account import Credentials
import gspread

app = Flask(__name__)
# =========================
# 🔐 GOOGLE SHEETS SETUP
# =========================

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ Read credentials from Render ENV
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

sheet = client.open("Nifty_OI_Data").worksheet("Dashboard")
# =========================
# 🏠 HOME DATA
# =========================
def get_home_data():
    return {
        "trend": sheet.acell("H53").value,
        "sentiment": sheet.acell("H54").value,
        "pcr": sheet.acell("H55").value,
        "vix": sheet.acell("H56").value
    }

# =========================
# 📊 OI DATA
# =========================
def get_oi_data():
    try:
        fetch_time = sheet.acell("Q33").value
        oi_data = sheet.get("B1:I6")

        return {
            "fetch_time": fetch_time,
            "oi_data": oi_data
        }

    except Exception as e:
        print("OI Error:", e)
        return {
            "fetch_time": "Error",
            "oi_data": []
        }

# =========================
# 🔝 TOP 5 DATA
# =========================
def get_top5_data():
    try:
        fetch_time = sheet.acell("I33").value
        nifty_title = sheet.acell("E34").value
        nifty_data = sheet.get("B35:I40")

        bank_title = sheet.acell("E42").value
        bank_data = sheet.get("B43:I48")

        return {
            "fetch_time": fetch_time,
            "nifty_title": nifty_title,
            "nifty_data": nifty_data,
            "bank_title": bank_title,
            "bank_data": bank_data
        }

    except Exception as e:
        print("Top5 Error:", e)
        return {
            "fetch_time": "Error",
            "nifty_title": "NIFTY",
            "nifty_data": [],
            "bank_title": "BANKNIFTY",
            "bank_data": []
        }


# =========================
# 📊 Orderflow DATA
# =========================
def get_orderflow_data():
    try:
        fetch_time = sheet.acell("N67").value
        oi_data = sheet.get("H68:N74")

        return {
            "fetch_time": fetch_time,
            "orderflow_data": orderflow_data
        }

    except Exception as e:
        print("Order Flow Error:", e)
        return {
            "fetch_time": "Error",
            "orderflow_data": []
        }
# =========================
# 📊 Live DATA
# =========================    
    
def get_live_data():
    try:
        return {
            "nifty_live": float(sheet.acell("M36").value.replace(",", "")),
            "bank_live": float(sheet.acell("P36").value.replace(",", ""))
        }
    except:
        return {
            "nifty_live": None,
            "bank_live": None
        }

# =========================
# 📊 DMA DATA
# =========================
def get_dma_data():
    try:
        fetch_time = sheet.acell("Q33").value

        # ✅ Full DMA table
        raw = sheet.get("L35:Q45")

        nifty = []
        bank = []

        for i, row in enumerate(raw):
            if len(row) < 6:
                continue

            # ---------------- NIFTY ----------------
            try:
                level_n = row[0]

                if level_n:
                    value_n = float(row[1].replace(",", ""))
                    status_n = row[2] if len(row) > 2 else ""

                    # ✅ Keep LIVE row also
                    nifty.append({
                        "level": level_n,
                        "value": value_n,
                        "status": status_n
                    })
            except:
                pass

            # ---------------- BANKNIFTY ----------------
            try:
                level_b = row[3]

                if level_b:
                    value_b = float(row[4].replace(",", ""))
                    status_b = row[5] if len(row) > 5 else ""

                    bank.append({
                        "level": level_b,
                        "value": value_b,
                        "status": status_b
                    })
            except:
                pass

        return {
            "fetch_time": fetch_time,
            "nifty": nifty,
            "bank": bank
        }

    except Exception as e:
        print("DMA Error:", e)
        return {
            "fetch_time": "Error",
            "nifty": [],
            "bank": []
        }
# =========================
# 🌐 INDEX DATA
# =========================
def get_index_data():
    try:
        fetch_time = sheet.acell("E52").value
        raw_data = sheet.get("B53:E63")[1:]

        index_data = sorted(
            raw_data,
            key=lambda x: float(x[3]),
            reverse=True
        )

        return {
            "fetch_time": fetch_time,
            "index_data": index_data
        }

    except Exception as e:
        print("Index Error:", e)
        return {
            "fetch_time": "Error",
            "index_data": []
        }

# =========================
# 📈 STOCKS DATA
# =========================
def get_stocks_data():
    try:
        fetch_time = sheet.acell("E66").value
        raw = sheet.get("B67:E117")

        stocks = []

        for row in raw:
            if len(row) < 4:
                continue

            try:
                stocks.append({
                    "name": row[0],
                    "cmp": float(row[1]),
                    "percent": float(row[2]),
                    "change": float(row[3])
                })
            except:
                pass

        stocks = sorted(stocks, key=lambda x: x["percent"], reverse=True)

        return {
            "fetch_time": fetch_time,
            "stocks": stocks
        }

    except Exception as e:
        print("Stock Error:", e)
        return {
            "fetch_time": "Error",
            "stocks": []
        }

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", data=get_home_data())

@app.route("/top5")
def top5():
    return render_template("top5.html", data=get_top5_data())

@app.route("/dma")
def dma():
    dma_data = get_dma_data()
    live_data = get_live_data()

    data = {**dma_data, **live_data}

    return render_template("dma.html", data=data)
@app.route("/oi")
def oi():
    return render_template("oi.html", data=get_oi_data())

@app.route("/signal")
def signal():
    return render_template("signal.html")

@app.route("/indices")
def indices():
    return render_template("indices.html", data=get_index_data())

@app.route("/stocks")
def stocks():
    return render_template("stocks.html", data=get_stocks_data())

# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
