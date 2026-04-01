import os
import json
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

# ✅ Read from Render Environment
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

# Open your sheet
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
        # Fetch Time
        fetch_time = sheet.acell("Q33").value

        # Table data
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
# 🔝 TOP 5 DATA (MAIN PART)
# =========================
def get_top5_data():
    try:
        # Fetch Time
        fetch_time = sheet.acell("I33").value

        # NIFTY TITLE
        nifty_title = sheet.acell("E34").value

        # NIFTY TABLE
        nifty_data = sheet.get("B35:I40")

        # BANKNIFTY TITLE
        bank_title = sheet.acell("E42").value

        # BANKNIFTY TABLE
        bank_data = sheet.get("B43:I48")

        return {
            "fetch_time": fetch_time,
            "nifty_title": nifty_title,
            "nifty_data": nifty_data,
            "bank_title": bank_title,
            "bank_data": bank_data
        }

    except Exception as e:
        print("Error fetching Top5:", e)
        return {
            "fetch_time": "Error",
            "nifty_title": "NIFTY",
            "nifty_data": [],
            "bank_title": "BANKNIFTY",
            "bank_data": []
        }
 #=========================
# 📊 DMA DATA (NEW)
# =========================
def get_dma_data():
    try:
        # Fetch Time
        fetch_time = sheet.acell("Q33").value

        # Full Table
        raw = sheet.get("L35:Q45")

        nifty = []
        bank = []

        for row in raw:

            # Skip header row
            if "Nifty" in row or "Banknifty" in row:
                continue

            # Skip empty rows
            if len(row) < 6:
                continue

            # ---------------- NIFTY ----------------
            level_n = row[0]

            try:
                value_n = float(row[1])
            except:
                continue

            status_n = row[2] if len(row) > 2 else ""

            nifty.append({
                "level": level_n,
                "value": value_n,
                "status": status_n
            })

            # ---------------- BANKNIFTY ----------------
            level_b = row[3]

            try:
                value_b = float(row[4])
            except:
                continue

            status_b = row[5] if len(row) > 5 else ""

            bank.append({
                "level": level_b,
                "value": value_b,
                "status": status_b
            })

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
# 🌐 Index
# =========================

def get_index_data():
    try:
        fetch_time = sheet.acell("E52").value
        raw_data = sheet.get("B53:E63")[1:]  # skip header

        # Convert + sort by %Change (descending)
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
# 🌐 Stocks

# =========================
        
def get_stocks_data():
    try:
        fetch_time = sheet.acell("E66").value
        raw = sheet.get("B67:E117")

        stocks = []

        for row in raw:
            if len(row) < 4:
                continue

            name = row[0]

            try:
                cmp = float(row[1])
                change = float(row[3])
                percent = float(row[2])
            except:
                continue

            stocks.append({
                "name": name,
                "cmp": cmp,
                "change": change,
                "percent": percent
            })

        # 🔥 SORT HIGH TO LOW (% CHANGE)
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
    data = get_home_data()
    return render_template("home.html", data=data)

@app.route("/top5")
def top5():
    data = get_top5_data()
    return render_template("top5.html", data=data)


@app.route("/dma")
def dma():
    data = get_dma_data()
    return render_template("dma.html", data=data)


@app.route("/oi")
def oi():
    data = get_oi_data()
    return render_template("oi.html", data=data)

@app.route("/signal")
def signal():
    return render_template("signal.html")
    
@app.route("/indices")
def indices():
    data = get_index_data()
    return render_template("indices.html", data=data)
@app.route("/stocks")
def stocks():
    data = get_stocks_data()
    return render_template("stocks.html", data=data)
# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
