import os
import json
from datetime import datetime
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
        return float(str(val).replace(",", "").replace(" ", ""))
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
# 🏠 HOME DATA  (H53:H56 + indices + OI bars)
# =========================
def get_home_data():
    try:
        trend     = safe(sheet.acell("H53").value)
        sentiment = safe(sheet.acell("H54").value)
        pcr       = safe(sheet.acell("H55").value)
        vix       = safe(sheet.acell("H56").value)
        fetch_time = safe(sheet.acell("E52").value)

        # Indices for home (B53:E55 → Nifty, BankNifty, Sensex)
        idx = get_range("B54:E56")
        def idx_row(r):
            if not r or len(r) < 4:
                return {"name":"—","price":"—","change":0,"pct":0}
            return {
                "name":   safe(r[0]),
                "price":  fmt(r[1]),
                "change": clean_num(r[2]),
                "pct":    clean_num(r[3])
            }

        nifty_row    = idx_row(idx[0]) if len(idx) > 0 else idx_row([])
        banknifty_row= idx_row(idx[1]) if len(idx) > 1 else idx_row([])
        sensex_row   = idx_row(idx[2]) if len(idx) > 2 else idx_row([])

        # OI bars — use Max OI strikes (I109:K114 → 6 rows near ATM)
        oi_raw = get_range("I109:K114")
        oi_bars = []
        for r in oi_raw:
            if len(r) >= 3:
                call_oi = clean_num(r[0])
                strike  = safe(r[1])
                put_oi  = clean_num(r[2])
                total   = call_oi + put_oi if (call_oi + put_oi) > 0 else 1
                oi_bars.append({"strike": f"{strike} CE", "value": round(call_oi/total*100), "type":"CE"})
                oi_bars.append({"strike": f"{strike} PE", "value": round(put_oi/total*100),  "type":"PE"})

        return {
            "date":       datetime.now().strftime("%a, %d %b %Y"),
            "fetch_time": fetch_time,
            "trend":      trend,
            "sentiment":  sentiment,
            "pcr":        pcr,
            "vix":        vix,
            "nifty_price":       nifty_row["price"],
            "nifty_change":      nifty_row["change"],
            "banknifty_price":   banknifty_row["price"],
            "banknifty_change":  banknifty_row["change"],
            "sensex_price":      sensex_row["price"],
            "sensex_change":     sensex_row["change"],
            "oi":         oi_bars[:8],
            "total_oi":   "—",
            "max_pain":   "—",
        }
    except Exception as e:
        print("HOME ERROR:", e)
        return {"date":"—","fetch_time":"—","trend":"—","sentiment":"—","pcr":"—","vix":"—",
                "nifty_price":"—","nifty_change":0,"banknifty_price":"—","banknifty_change":0,
                "sensex_price":"—","sensex_change":0,"oi":[],"total_oi":"—","max_pain":"—"}

# =========================
# 📈 INTRADAY DATA  (pic 2)
# =========================
def get_intraday_data():
    try:
        # Date/Time from H86, J86
        date_val = safe(sheet.acell("J86").value)
        time_val = safe(sheet.acell("M86").value)

        def safe_row(rng):
            d = get_range(rng)
            if d and len(d[0]) >= 5:
                return d[0]
            return ["0","0","0","0","0"]

        nifty  = safe_row("I90:M90")
        bank   = safe_row("I94:M94")
        sensex = safe_row("I98:M98")

        def mk(row, name):
            return {
                "name":  name,
                "ltp":   fmt(row[0]),
                "open":  fmt(row[1]),
                "high":  fmt(row[2]),
                "low":   fmt(row[3]),
                "close": fmt(row[4]),
                "change_pct": 0
            }

        return {
            "date": date_val,
            "time": time_val,
            "nifty":  mk(nifty,  "Nifty 50"),
            "bank":   mk(bank,   "Bank Nifty"),
            "sensex": mk(sensex, "Sensex"),
        }
    except Exception as e:
        print("INTRADAY ERROR:", e)
        empty = {"name":"—","ltp":"—","open":"—","high":"—","low":"—","close":"—","change_pct":0}
        return {"date":"—","time":"—","nifty":empty,"bank":empty,"sensex":empty}

# =========================
# 📊 MAX OI / CHAIN  (pic 3) — I105:Q126
# =========================
def get_chain_data():
    try:
        fetch_date = safe(sheet.acell("K104").value)
        fetch_time = safe(sheet.acell("Q104").value)

        raw = get_range("I106:Q126")  # 21 rows × 9 cols

        nifty, bank, sensex = [], [], []

        # find ATM for each (max put OI index)
        def find_atm(rows, put_idx):
            max_v, atm_i = 0, 0
            for i, r in enumerate(rows):
                try:
                    v = clean_num(r[put_idx])
                    if v > max_v:
                        max_v, atm_i = v, i
                except:
                    pass
            return atm_i

        def fmt_oi(v):
            v = clean_num(v)
            if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
            if v >= 1_000:     return f"{v/1_000:.1f}K"
            return str(int(v))

        for r in raw:
            if len(r) < 9:
                r = r + ["0"] * (9 - len(r))
            nifty.append({"call": fmt_oi(r[0]), "strike": safe(r[1]), "put": fmt_oi(r[2]),
                          "call_raw": clean_num(r[0]), "put_raw": clean_num(r[2])})
            bank.append( {"call": fmt_oi(r[3]), "strike": safe(r[4]), "put": fmt_oi(r[5]),
                          "call_raw": clean_num(r[3]), "put_raw": clean_num(r[5])})
            sensex.append({"call": fmt_oi(r[6]), "strike": safe(r[7]), "put": fmt_oi(r[8]),
                           "call_raw": clean_num(r[6]), "put_raw": clean_num(r[8])})

        # mark max call / put OI
        def mark_max(rows):
            max_c = max((r["call_raw"] for r in rows), default=0)
            max_p = max((r["put_raw"]  for r in rows), default=0)
            for r in rows:
                r["max_call"] = r["call_raw"] == max_c and max_c > 0
                r["max_put"]  = r["put_raw"]  == max_p and max_p > 0
            return rows

        return {
            "fetch_date": fetch_date,
            "fetch_time": fetch_time,
            "nifty":   mark_max(nifty),
            "bank":    mark_max(bank),
            "sensex":  mark_max(sensex),
        }
    except Exception as e:
        print("CHAIN ERROR:", e)
        return {"fetch_date":"—","fetch_time":"—","nifty":[],"bank":[],"sensex":[]}

# =========================
# 📊 INDICES  (pic 4) — B53:E63 + stocks B67:E75
# =========================
def get_indices_data():
    try:
        fetch_time = safe(sheet.acell("E52").value)
        raw = get_range("B53:E63")  # header + 10 indices

        indices = []
        for r in raw[1:]:  # skip header row
            if not r or len(r) < 4:
                continue
            indices.append({
                "name":   safe(r[0]),
                "cmp":    fmt(r[1]),
                "change": clean_num(r[2]),
                "pct":    clean_num(r[3]),
            })

        # ✅ SORT BY % (HIGH → LOW)
        indices.sort(key=lambda x: x["pct"], reverse=True)

        # stocks
        stocks_raw = get_range("B67:E75")
        fetch_time2 = safe(sheet.acell("E66").value)

        stocks = []
        for r in stocks_raw[1:]:
            if not r or len(r) < 4:
                continue
            stocks.append({
                "name":   safe(r[0]),
                "cmp":    fmt(r[1]),
                "pct":    clean_num(r[2]),
                "change": clean_num(r[3]),
            })

        return {
            "fetch_time": fetch_time,
            "fetch_time2": fetch_time2,
            "indices": indices,
            "stocks": stocks
        }

    except Exception as e:
        print("INDICES ERROR:", e)
        return {
            "fetch_time": "—",
            "fetch_time2": "—",
            "indices": [],
            "stocks": []
        }
# =========================
# 📐 DMA  (pic 5) — L33:Q45
# =========================
def get_dma_data():
    try:
        fetch_time = safe(sheet.acell("Q33").value)

        # Nifty50: L36:N45 (Live L36, levels L37:N45)
        nifty_live = safe(sheet.acell("M36").value)
        bank_live  = safe(sheet.acell("P36").value)

        nifty_raw = get_range("L37:N45")
        bank_raw  = get_range("O37:Q45")

        def parse_dma(rows):
            out = []
            for r in rows:
                if len(r) >= 3:
                    out.append({"level": safe(r[0]), "value": fmt(r[1]), "status": safe(r[2])})
            return out

        return {
            "fetch_time": fetch_time,
            "nifty_live": fmt(nifty_live),
            "bank_live":  fmt(bank_live),
            "nifty": parse_dma(nifty_raw),
            "bank":  parse_dma(bank_raw),
        }
    except Exception as e:
        print("DMA ERROR:", e)
        return {"fetch_time":"—","nifty_live":"—","bank_live":"—","nifty":[],"bank":[]}

# =========================
# 📉 OI DATA  (pic 6) — Dashboard B1:L11 (niftyoi sheet mirrored)
# =========================
def get_oi_data():
    try:
        fetch_time = safe(sheet.acell("Q33").value)
        raw = get_range("B1:L11")   # header + 10 rows

        headers = raw[0] if raw else []
        rows = []
        for r in raw[1:]:
            if not r: continue
            row = []
            for cell in r:
                row.append(safe(cell))
            rows.append(row)

        # charts use existing iframe URLs
        return {
            "fetch_time": fetch_time,
            "headers": headers,
            "rows": rows,
        }
    except Exception as e:
        print("OI ERROR:", e)
        return {"fetch_time":"—","headers":[],"rows":[]}

# =========================
# 🏆 TOP 5  (pic 7) — B35:I48
# =========================
def get_top5_data():
    try:
        fetch_time = safe(sheet.acell("H33").value)
        raw = get_range("B35:I48")

        # Row 35 = header (Gainers / Losers for Nifty50)
        # Rows 36-40 = Nifty gainers (B:E) + losers (F:I)
        # Row 42 = Banknifty header
        # Rows 43-47 = BN gainers (B:E) + losers (F:I) [some losers may be shorter]

        def parse_block(rows, start, end):
            gainers, losers = [], []
            for r in rows[start:end]:
                if len(r) >= 4 and safe(r[0]) != "—":
                    gainers.append({"name": safe(r[0]), "cmp": fmt(r[1]), "pct": clean_num(r[2]), "change": clean_num(r[3])})
                if len(r) >= 8 and safe(r[4]) != "—":
                    losers.append({"name": safe(r[4]), "cmp": fmt(r[5]), "pct": clean_num(r[6]), "change": clean_num(r[7])})
            return gainers, losers

        nifty_g, nifty_l   = parse_block(raw, 1, 6)   # rows index 1-5
        bank_g,  bank_l    = parse_block(raw, 8, 14)  # rows index 8-13

        return {
            "fetch_time": fetch_time,
            "nifty_gainers": nifty_g,
            "nifty_losers":  nifty_l,
            "bank_gainers":  bank_g,
            "bank_losers":   bank_l,
        }
    except Exception as e:
        print("TOP5 ERROR:", e)
        return {"fetch_time":"—","nifty_gainers":[],"nifty_losers":[],"bank_gainers":[],"bank_losers":[]}

# =========================
# 📋 STOCKS  (pic 8) — B66:E117
# =========================
def get_stocks_data():
    try:
        fetch_time = safe(sheet.acell("E66").value)
        raw = get_range("B67:E117")  # header + 50 stocks

        stocks = []
        for r in raw[1:]:
            if not r or len(r) < 4 or not safe(r[0]): continue
            stocks.append({
                "name":   safe(r[0]),
                "cmp":    fmt(r[1]),
                "pct":    clean_num(r[2]),
                "change": clean_num(r[3]),
            })
        return {"fetch_time": fetch_time, "stocks": stocks}
    except Exception as e:
        print("STOCKS ERROR:", e)
        return {"fetch_time":"—","stocks":[]}

# =========================
# 🌊 ORDER FLOW  (pic 9) — G67:N81
# =========================
def get_orderflow_data():
    try:
        raw = get_range("G67:N81")

        def fmt_vol(v):
            v = clean_num(v)
            if v >= 1_000_000_000:
                return f"{v/1_000_000_000:.2f}B"
            if v >= 1_000_000:
                return f"{v/1_000_000:.1f}M"
            if v >= 1_000:
                return f"{v/1_000:.1f}K"
            return str(int(v))

        def parse_rows(rows):
            out = []
            for r in rows:
                # skip invalid / header rows
                if len(r) < 8:
                    continue
                if not r[1] or ":" not in str(r[1]):
                    continue  # skip header rows

                delta = clean_num(r[6])

                out.append({
                    "time":     safe(r[1]),
                    "spot":     fmt(r[2]),
                    "volume":   fmt_vol(r[3]),
                    "buyers":   fmt_vol(r[4]),
                    "sellers":  fmt_vol(r[5]),
                    "delta":    delta,
                    "delta_fmt": fmt_vol(delta),
                    "bias":     "Bull" if delta > 0 else "Bear" if delta < 0 else "Neutral"
                })
            return out

        # 🔥 SPLIT DATA CORRECTLY
        nifty_block = raw[2:8]   # rows with actual nifty data
        bank_block  = raw[10:16] # rows with banknifty data

        return {
            "nifty": parse_rows(nifty_block),
            "bank":  parse_rows(bank_block),
        }

    except Exception as e:
        print("ORDERFLOW ERROR:", e)
        return {"nifty": [], "bank": []}
# =========================
# 🌐 ROUTES
# =========================
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", data=get_home_data())

@app.route("/intraday")
def intraday():
    return render_template("intraday.html", data=get_intraday_data())

@app.route("/chain")
@app.route("/maxoi")
def chain():
    return render_template("chain.html", data=get_chain_data())

@app.route("/indices")
def indices():
    return render_template("indices.html", data=get_indices_data())

@app.route("/dma")
def dma():
    return render_template("dma.html", data=get_dma_data())

@app.route("/oi")
def oi():
    return render_template("oi.html", data=get_oi_data())

@app.route("/top5")
def top5():
    return render_template("top5.html", data=get_top5_data())

@app.route("/stocks")
def stocks():
    return render_template("stocks.html", data=get_stocks_data())

@app.route("/orderflow")
def orderflow():
    return render_template("orderflow.html", data=get_orderflow_data())

# JSON endpoints for auto-refresh
@app.route("/api/home")       
def api_home():       return jsonify(get_home_data())
@app.route("/api/intraday")   
def api_intraday():   return jsonify(get_intraday_data())
@app.route("/api/chain")      
def api_chain():      return jsonify(get_chain_data())
@app.route("/api/indices")    
def api_indices():    return jsonify(get_indices_data())
@app.route("/api/dma")        
def api_dma():        return jsonify(get_dma_data())
@app.route("/api/oi")         
def api_oi():         return jsonify(get_oi_data())
@app.route("/api/top5")       
def api_top5():       return jsonify(get_top5_data())
@app.route("/api/stocks")     
def api_stocks():     return jsonify(get_stocks_data())
@app.route("/api/orderflow")  
def api_orderflow():  return jsonify(get_orderflow_data())

# =========================
# ▶️ RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
