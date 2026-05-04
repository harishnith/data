import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, session, redirect, send_from_directory, request
from google.oauth2.service_account import Credentials
import gspread
from fyers_apiv3 import fyersModel

app = Flask(__name__)

# =========================
# 🔐 SESSION CONFIG (FIXED)
# =========================
app.secret_key = "your_super_secret_key_123"

app.permanent_session_lifetime = timedelta(days=7)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # True only if HTTPS
    SESSION_COOKIE_SAMESITE="Lax"
)

# =========================
# 🔐 GOOGLE SHEETS
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
# 🔐 FYERS
# =========================
APP_ID = "7IAQXYIXWH-100"

ACCESS_TOKEN = os.environ.get("FYERS_TOKEN")
if not ACCESS_TOKEN:
    raise Exception("FYERS_TOKEN missing")

def get_fyers():
    return fyersModel.FyersModel(
        client_id=APP_ID,
        token=ACCESS_TOKEN,
        log_path=""
    )

# =========================
# 🔐 LOGIN CHECK
# =========================
def require_login():
    return not session.get("logged_in", False)

# =========================
# 🔐 GLOBAL PROTECTION
# =========================
@app.before_request
def check_login():
    open_routes = ["/", "/home", "/unlock"]

    if request.path.startswith("/static"):
        return

    if request.path not in open_routes and require_login():
        return redirect("/home")

# =========================
# 🔐 LOGIN ROUTE
# =========================
@app.route("/unlock", methods=["POST"])
def unlock():
    if request.form.get("password") == "1234":
        session.permanent = True
        session["logged_in"] = True
        return jsonify({"status": "success"})
    
    return jsonify({"status": "fail"}), 401

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/home")

# =========================
# 🛠 HELPERS
# =========================
def safe(val, default="—"):
    try:
        v = str(val).strip()
        return v if v else default
    except:
        return default

def clean_num(val):
    try:
        s = str(val).replace(",", "").strip().upper()

        if "B" in s:
            return float(s.replace("B", "")) * 1_000_000_000
        elif "M" in s:
            return float(s.replace("M", "")) * 1_000_000
        elif "K" in s:
            return float(s.replace("K", "")) * 1_000
        else:
            return float(s)

    except:
        return 0.0

def fmt(val, decimals=2):
    try:
        return f"{float(str(val).replace(',','')):.{decimals}f}"
    except:
        return safe(val)

def get_range(r):
    try:
        return sheet.get(r)
    except:
        return []

# =========================
# 🏠 HOME DATA
# =========================
def get_home_data():
    try:
        trend     = safe(sheet.acell("H53").value)
        sentiment = safe(sheet.acell("H54").value)
        pcr       = safe(sheet.acell("H55").value)
        vix       = safe(sheet.acell("H56").value)
        fetch_time = safe(sheet.acell("E52").value)

        idx = get_range("B54:E56")

        def idx_row(r):
            if not r or len(r) < 4:
                return {"name":"—","price":"—","change":0}
            return {
                "name":   safe(r[0]),
                "price":  fmt(r[1]),
                "change": clean_num(r[2])
            }

        nifty_row    = idx_row(idx[0]) if len(idx) > 0 else idx_row([])
        banknifty_row= idx_row(idx[1]) if len(idx) > 1 else idx_row([])

        return {
            "date": datetime.now().strftime("%a, %d %b %Y"),
            "fetch_time": fetch_time,
            "trend": trend,
            "sentiment": sentiment,
            "pcr": pcr,
            "vix": vix,
            "nifty_price": nifty_row["price"],
            "banknifty_price": banknifty_row["price"]
        }

    except:
        return {}

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", data=get_home_data())

@app.route("/intraday")
def intraday():
    return render_template("intraday.html")

@app.route("/chain")
def chain():
    return render_template("chain.html")

@app.route("/indices")
def indices():
    return render_template("indices.html")

@app.route("/dma")
def dma():
    return render_template("dma.html")

@app.route("/oi")
def oi():
    return render_template("oi.html")

@app.route("/top5")
def top5():
    return render_template("top5.html")

@app.route("/stocks")
def stocks():
    return render_template("stocks.html")

@app.route("/orderflow")
def orderflow():
    return render_template("orderflow.html")

# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
