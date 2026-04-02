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
        "trend": sheet.acell("H52").value,
        "sentiment": sheet.acell("H53").value,
        "pcr": sheet.acell("H54").value,
        "vix": sheet.acell("H55").value
    }

# =========================
# 📊 OI DATA
# =========================
def get_oi_data():
    try:
        fetch_time = sheet.acell("Q33").value
        oi_data = sheet.get("C1:I6")

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
# 📊 DMA DATA
# =========================
def get_dma_data():
    try:
        fetch_time = sheet.acell("Q33").value
        raw = sheet.get("L35:Q45")

        nifty = []
        bank = []

        for row in raw:
            if "Nifty" in row or "Banknifty" in row:
                continue

            if len(row) < 6:
                continue

            # NIFTY
            try:
                nifty.append({
                    "level": row[0],
                    "value": float(row[1]),
                    "status": row[2]
                })
            except:
                pass

            # BANKNIFTY
            try:
                bank.append({
                    "level": row[3],
                    "value": float(row[4]),
                    "status": row[5]
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
    return render_template("dma.html", data=get_dma_data())

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
