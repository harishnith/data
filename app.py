import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, session, redirect, request
from google.oauth2.service_account import Credentials
import gspread
from fyers_apiv3 import fyersModel

app = Flask(__name__)

# =========================
# 🔐 SESSION CONFIG
# =========================
app.secret_key = "secret123"
app.permanent_session_lifetime = timedelta(days=7)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Lax"
)

# =========================
# 🔐 GOOGLE SHEETS
# =========================
sheet = None

try:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_json = os.environ.get("GOOGLE_CREDENTIALS")

    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Nifty_OI_Data").worksheet("Dashboard")
        print("✅ Google Sheets Connected")
    else:
        print("⚠️ GOOGLE_CREDENTIALS missing")

except Exception as e:
    print("❌ Google Sheets Error:", e)

# =========================
# 🔐 FYERS
# =========================
APP_ID = "7IAQXYIXWH-100"
ACCESS_TOKEN = os.environ.get("FYERS_TOKEN")

if ACCESS_TOKEN:
    print("✅ FYERS TOKEN LOADED")
else:
    print("⚠️ FYERS_TOKEN missing")

def get_fyers():
    if not ACCESS_TOKEN:
        return None

    try:
        return fyersModel.FyersModel(
            client_id=APP_ID,
            token=ACCESS_TOKEN,
            log_path=""
        )
    except Exception as e:
        print("❌ Fyers Init Error:", e)
        return None

# =========================
# 🔐 LOGIN
# =========================
def require_login():
    return not session.get("logged_in", False)

@app.before_request
def check_login():
    open_routes = ["/", "/home", "/unlock"]

    if request.path.startswith("/static"):
        return

    if request.path not in open_routes and require_login():
        return redirect("/home")

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

def fmt(val):
    try:
        return f"{float(val):,.2f}"
    except:
        return safe(val)

def get_cell(cell):
    try:
        if sheet:
            return safe(sheet.acell(cell).value)
    except:
        pass
    return "—"

# =========================
# 📊 HOME DATA
# =========================
def get_home_data():
    try:
        return {
            "date": datetime.now().strftime("%d-%m-%Y"),
            "time": datetime.now().strftime("%H:%M:%S"),

            "trend": get_cell("H53"),
            "sentiment": get_cell("H54"),
            "pcr": get_cell("H55"),
            "vix": get_cell("H56"),

            "nifty": fmt(get_cell("E54")),
            "banknifty": fmt(get_cell("E55"))
        }
    except Exception as e:
        print("Home Data Error:", e)
        return {}

# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", data=get_home_data())

@app.route("/indices")
def indices():
    return render_template("indices.html")

@app.route("/intraday")
def intraday():
    return render_template("intraday.html")

@app.route("/chain")
def chain():
    return render_template("chain.html")

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
