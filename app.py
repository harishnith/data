import os
import json
from flask import Flask, render_template, jsonify
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
# 📊 INTRADAY DATA
# =========================
def get_intraday_data():
    try:
        def clean(val):
            try:
                return float(str(val).replace(",", ""))
            except:
                return 0

        def safe_row(range_name):
            data = sheet.get(range_name)
            if not data or len(data[0]) < 5:
                return [0, 0, 0, 0, 0]
            return data[0]

        nifty = safe_row("I90:M90")
        bank = safe_row("I94:M94")
        sensex = safe_row("I98:M98")

        return {
            "nifty": {
                "ltp": clean(nifty[0]),
                "open": clean(nifty[1]),
                "high": clean(nifty[2]),
                "low": clean(nifty[3]),
                "close": clean(nifty[4]),
            },
            "bank": {
                "ltp": clean(bank[0]),
                "open": clean(bank[1]),
                "high": clean(bank[2]),
                "low": clean(bank[3]),
                "close": clean(bank[4]),
            },
            "sensex": {
                "ltp": clean(sensex[0]),
                "open": clean(sensex[1]),
                "high": clean(sensex[2]),
                "low": clean(sensex[3]),
                "close": clean(sensex[4]),
            }
        }

    except Exception as e:
        print("Intraday Error:", e)
        return {
            "nifty": {"ltp":0,"open":0,"high":0,"low":0,"close":0},
            "bank": {"ltp":0,"open":0,"high":0,"low":0,"close":0},
            "sensex": {"ltp":0,"open":0,"high":0,"low":0,"close":0}
        }

# =========================
# 📊 CHAIN DATA (NEW)
# =========================
def get_chain_data():
    try:
        def clean(x):
            try:
                return float(str(x).replace(",", "").replace("M","000000").replace("K","000"))
            except:
                return 0

        def get_block(call_col, strike_col, put_col):
            calls = sheet.get(f"{call_col}106:{call_col}126")
            strikes = sheet.get(f"{strike_col}106:{strike_col}126")
            puts = sheet.get(f"{put_col}106:{put_col}126")

            data = []
            for i in range(len(strikes)):
                try:
                    data.append({
                        "call": clean(calls[i][0]),
                        "strike": clean(strikes[i][0]),
                        "put": clean(puts[i][0])
                    })
                except:
                    pass
            return data

        return {
            "nifty": get_block("I","J","K"),
            "bank": get_block("L","M","N"),
            "sensex": get_block("O","P","Q")
        }

    except Exception as e:
        print("CHAIN ERROR:", e)
        return {
            "nifty": [],
            "bank": [],
            "sensex": []
        }

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", data=get_home_data())

@app.route("/oi")
def oi():
    return render_template("oi.html", data=get_oi_data())

@app.route("/intraday")
def intraday():
    return render_template("intraday.html", data=get_intraday_data())

@app.route("/intraday-data")
def intraday_data():
    return jsonify(get_intraday_data())

# 🔥 NEW CHAIN ROUTES
@app.route("/chain")
def chain():
    return render_template("chain.html", data=get_chain_data())

@app.route("/chain-data")
def chain_data():
    return jsonify(get_chain_data())

# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
