import os
import json
from flask import Flask, render_template
from google.oauth2.service_account import Credentials
import gspread
from flask import jsonify

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
# 📊 Intraday DATA
# =========================        }
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

        # SAFE FETCH
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
# 📊 ORDERFLOW DATA
# =========================
def get_orderflow_data():
    try:
        fetch_time = sheet.acell("N67").value

        nifty_data = sheet.get("H68:N74")     # NIFTY
        bank_data = sheet.get("I75:N81")      # BANKNIFTY

        return {
            "fetch_time": fetch_time,
            "nifty_data": nifty_data,
            "bank_data": bank_data
        }

    except Exception as e:
        print("Orderflow Error:", e)
        return {
            "fetch_time": "Error",
            "nifty_data": [],
            "bank_data": []
        }
# =========================
# 📊 Option Chain DATA
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

        nifty = get_block("I", "J", "K")
        bank = get_block("L", "M", "N")
        sensex = get_block("O", "P", "Q")

        return {
            "nifty": nifty,
            "bank": bank,
            "sensex": sensex
        }

    except Exception as e:
        print("CHAIN ERROR:", e)
        return {"nifty": [], "bank": [], "sensex": []}       
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
    
@app.route("/orderflow")
def orderflow():
    return render_template("orderflow.html", data=get_orderflow_data())
    
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
@app.route("/intraday")
def intraday():
    return render_template("intraday.html", data=get_intraday_data())
    
@app.route("/chain")
def chain():
    return render_template("chain.html", data=get_chain_data())

@app.route("/chain-data")
def chain_data():
    return jsonify(get_chain_data())


@app.route("/intraday-data")
def intraday_data():
    return jsonify(get_intraday_data())    

# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
