"""
VALVERDE TRADE IA v3.0
22 ativos: Forex Majors · Commodities · Cripto · Índices · Ações
MTF · Score Ponderado · MACD · Bollinger Bands · EMA · Volume · ATR por tipo
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime
import os, json, requests, time

app = FastAPI(title="Valverde Trade IA")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ============================================================
# CATÁLOGO DE ATIVOS
# ============================================================
SYMBOL_CONFIG = {
    # ── Forex Majors ──
    "EURUSD=X": {"nome":"EUR/USD","nome_exibicao":"Euro / Dólar",       "tipo":"Forex",       "emoji":"💶","base_fallback":1.085},
    "USDJPY=X": {"nome":"USD/JPY","nome_exibicao":"Dólar / Iene",       "tipo":"Forex",       "emoji":"💴","base_fallback":149.5},
    "GBPUSD=X": {"nome":"GBP/USD","nome_exibicao":"Libra / Dólar",      "tipo":"Forex",       "emoji":"💷","base_fallback":1.265},
    "USDCHF=X": {"nome":"USD/CHF","nome_exibicao":"Dólar / Franco CH",  "tipo":"Forex",       "emoji":"🇨🇭","base_fallback":0.895},
    "AUDUSD=X": {"nome":"AUD/USD","nome_exibicao":"Dólar Australiano",  "tipo":"Forex",       "emoji":"🦘","base_fallback":0.655},
    "USDCAD=X": {"nome":"USD/CAD","nome_exibicao":"Dólar / CAD",        "tipo":"Forex",       "emoji":"🍁","base_fallback":1.365},
    "NZDUSD=X": {"nome":"NZD/USD","nome_exibicao":"Dólar NZ",           "tipo":"Forex",       "emoji":"🥝","base_fallback":0.605},
    # ── Commodities ──
    "GC=F":     {"nome":"XAUUSD","nome_exibicao":"Ouro",                "tipo":"Commodities", "emoji":"🥇","base_fallback":2350.0},
    "SI=F":     {"nome":"XAGUSD","nome_exibicao":"Prata",               "tipo":"Commodities", "emoji":"🥈","base_fallback":28.5},
    "PL=F":     {"nome":"XPTUSD","nome_exibicao":"Platina",             "tipo":"Commodities", "emoji":"⚗️","base_fallback":960.0},
    "CL=F":     {"nome":"WTI",   "nome_exibicao":"Petróleo WTI",        "tipo":"Commodities", "emoji":"🛢️","base_fallback":78.0},
    "BZ=F":     {"nome":"BRENT", "nome_exibicao":"Petróleo Brent",      "tipo":"Commodities", "emoji":"⛽","base_fallback":82.0},
    "NG=F":     {"nome":"NATGAS","nome_exibicao":"Gás Natural",          "tipo":"Commodities", "emoji":"🔥","base_fallback":2.8},
    # ── Cripto ──
    "BTC-USD":  {"nome":"BTC",   "nome_exibicao":"Bitcoin",             "tipo":"Cripto",      "emoji":"₿","base_fallback":66800,"binance":"BTCUSDT"},
    "ETH-USD":  {"nome":"ETH",   "nome_exibicao":"Ethereum",            "tipo":"Cripto",      "emoji":"⟠","base_fallback":3300, "binance":"ETHUSDT"},
    # ── Índices Globais ──
    "^GDAXI":   {"nome":"DAX",   "nome_exibicao":"DAX Alemanha",        "tipo":"Índices",     "emoji":"🇩🇪","base_fallback":18200},
    "^FTSE":    {"nome":"FTSE100","nome_exibicao":"FTSE 100 UK",        "tipo":"Índices",     "emoji":"🇬🇧","base_fallback":8200},
    "^N225":    {"nome":"NIKKEI","nome_exibicao":"Nikkei 225",          "tipo":"Índices",     "emoji":"🇯🇵","base_fallback":38500},
    "^GSPC":    {"nome":"SP500", "nome_exibicao":"S&P 500",             "tipo":"Índices",     "emoji":"🇺🇸","base_fallback":5200},
    "^IXIC":    {"nome":"NASDAQ","nome_exibicao":"NASDAQ 100",          "tipo":"Índices",     "emoji":"💻","base_fallback":16400},
    "^DJI":     {"nome":"DOW30", "nome_exibicao":"Dow Jones",           "tipo":"Índices",     "emoji":"📈","base_fallback":39000},
    # ── Ações ──
    "AAPL":     {"nome":"AAPL",  "nome_exibicao":"Apple",               "tipo":"Ações",       "emoji":"🍎","base_fallback":220},
    "NVDA":     {"nome":"NVDA",  "nome_exibicao":"NVIDIA",              "tipo":"Ações",       "emoji":"🎮","base_fallback":120},
}

# ATR multipliers por tipo — R:R mínimo 1.5:1
ATR_MULTIPLIER = {
    "Forex":       {"stop": 1.5, "tp": 2.5},
    "Cripto":      {"stop": 2.5, "tp": 4.0},
    "Commodities": {"stop": 2.0, "tp": 3.5},
    "Índices":     {"stop": 1.8, "tp": 3.0},
    "Ações":       {"stop": 1.5, "tp": 2.5},
}

SCORE_MINIMO   = 65
HISTORICO_FILE = "historico_sinais.json"

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_historico(h):
    with open(HISTORICO_FILE, "w") as f:
        json.dump(h, f, indent=2)


# ============================================================
# INDICADORES TÉCNICOS
# ============================================================

def calcular_ema(closes, periodo):
    if len(closes) < periodo:
        return closes[-1]
    k = 2 / (periodo + 1)
    ema = sum(closes[:periodo]) / periodo
    for p in closes[periodo:]:
        ema = p * k + ema * (1 - k)
    return ema

def calcular_rsi(closes, periodo=14):
    if len(closes) < periodo + 1:
        return 50.0
    g = p = 0.0
    for i in range(-periodo, 0):
        d = closes[i] - closes[i-1]
        if d > 0: g += d
        else:     p += abs(d)
    if p == 0: return 100.0
    return round(100 - (100 / (1 + g/p)), 1)

def calcular_macd(closes, fast=12, slow=26, sp=9):
    if len(closes) < slow + sp:
        return 0.0, 0.0, 0.0
    mv = []
    for i in range(slow - 1, len(closes)):
        mv.append(calcular_ema(closes[:i+1], fast) - calcular_ema(closes[:i+1], slow))
    if len(mv) < sp:
        return mv[-1], mv[-1], 0.0
    ml = mv[-1]
    sl = calcular_ema(mv, sp)
    return round(ml, 6), round(sl, 6), round(ml - sl, 6)

def calcular_bollinger(closes, periodo=20, dev=2):
    if len(closes) < periodo:
        p = closes[-1]; return p, p, p
    r   = closes[-periodo:]
    ma  = sum(r) / periodo
    std = (sum((c - ma)**2 for c in r) / periodo) ** 0.5
    return round(ma + dev*std, 6), round(ma, 6), round(ma - dev*std, 6)

def calcular_atr(closes, periodo=14):
    if len(closes) < 2:
        return closes[-1] * 0.005
    v = [abs(closes[i] - closes[i-1]) for i in range(max(-periodo, -(len(closes)-1)), 0)]
    return sum(v)/len(v) if v else closes[-1] * 0.005

def calcular_volume_ratio(volumes, periodo=20):
    if not volumes or len(volumes) < 2:
        return 1.0
    media = sum(volumes[-periodo-1:-1]) / min(periodo, len(volumes)-1)
    return round(volumes[-1] / media, 2) if media else 1.0

def calcular_forca(rsi, macd_hist, sinal):
    """Força direcional 0-100"""
    if sinal == "COMPRA":
        rsi_f = max(0, (50 - rsi) / 50 * 100)
        mac_f = 100 if macd_hist > 0 else 30
    elif sinal == "VENDA":
        rsi_f = max(0, (rsi - 50) / 50 * 100)
        mac_f = 100 if macd_hist < 0 else 30
    else:
        rsi_f = mac_f = 50
    return round(rsi_f * 0.6 + mac_f * 0.4, 1)

def calcular_score(rsi, macd_hist, preco, bb_upper, bb_lower, sinal, volume_ratio, mtf_ok):
    score = 0
    # RSI (30 pts)
    if sinal == "COMPRA":
        if rsi < 30:   score += 30
        elif rsi < 40: score += 22
        elif rsi < 50: score += 12
    elif sinal == "VENDA":
        if rsi > 70:   score += 30
        elif rsi > 60: score += 22
        elif rsi > 50: score += 12
    # MACD (25 pts)
    if   sinal == "COMPRA" and macd_hist > 0: score += 25
    elif sinal == "VENDA"  and macd_hist < 0: score += 25
    elif abs(macd_hist) < preco * 0.0005:      score += 10
    # Bollinger (25 pts)
    bw = bb_upper - bb_lower
    if bw > 0:
        pos = (preco - bb_lower) / bw
        if sinal == "COMPRA":
            if pos <= 0.1:   score += 25
            elif pos <= 0.3: score += 15
            elif pos <= 0.5: score += 8
        elif sinal == "VENDA":
            if pos >= 0.9:   score += 25
            elif pos >= 0.7: score += 15
            elif pos >= 0.5: score += 8
    # Volume (10 pts)
    if   volume_ratio >= 1.5: score += 10
    elif volume_ratio >= 1.2: score += 7
    elif volume_ratio >= 1.0: score += 4
    # MTF (10 pts)
    if mtf_ok: score += 10
    return min(score, 100)


# ============================================================
# FONTES DE DADOS
# ============================================================

def fetch_binance(symbol, interval, limit=100):
    bs = SYMBOL_CONFIG.get(symbol, {}).get("binance")
    if not bs: return None
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={bs}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return {
                "closes":  [float(c[4]) for c in data],
                "volumes": [float(c[5]) for c in data],
                "fonte":   "binance",
            }
    except Exception as e:
        print(f"Binance [{symbol}]: {e}")
    return None

def fetch_yahoo(symbol, interval):
    try:
        yi  = "1h" if interval == "4h" else interval
        rng = {"5m":"5d","15m":"5d","30m":"5d","1h":"30d","4h":"60d","1d":"6mo"}.get(interval, "5d")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={yi}&range={rng}"
        r   = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            res = r.json().get("chart", {}).get("result", [])
            if res:
                q       = res[0].get("indicators", {}).get("quote", [{}])[0]
                closes  = [c for c in q.get("close",  []) if c is not None]
                volumes = [v for v in q.get("volume", []) if v is not None]
                if closes:
                    if not volumes or max(volumes) == 0:
                        volumes = [1_000_000.0] * len(closes)
                    return {"closes": closes, "volumes": volumes, "fonte": "yahoo"}
    except Exception as e:
        print(f"Yahoo [{symbol}]: {e}")
    return None

def fetch_fallback(symbol, interval):
    import random
    base = SYMBOL_CONFIG.get(symbol, {}).get("base_fallback", 100.0)
    random.seed(int(time.time()/300) + hash(symbol + interval) % 9999)
    closes  = [base * (1 + random.uniform(-0.015, 0.015)) for _ in range(100)]
    volumes = [random.uniform(500_000, 2_000_000) for _ in range(100)]
    return {"closes": closes, "volumes": volumes, "fonte": "simulado"}

def fetch_candles(symbol, interval):
    if SYMBOL_CONFIG.get(symbol, {}).get("binance"):
        d = fetch_binance(symbol, interval)
        if d: return d
    d = fetch_yahoo(symbol, interval)
    if d: return d
    return fetch_fallback(symbol, interval)


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analisar_closes(symbol, closes, volumes):
    cfg  = SYMBOL_CONFIG.get(symbol, {})
    tipo = cfg.get("tipo", "Ações")
    p    = closes[-1]

    rsi             = calcular_rsi(closes)
    _, _, macd_hist = calcular_macd(closes)
    bbu, bbm, bbl   = calcular_bollinger(closes)
    atr             = calcular_atr(closes)
    vr              = calcular_volume_ratio(volumes)
    ema9            = calcular_ema(closes, 9)
    ema21           = calcular_ema(closes, 21)
    ema50           = calcular_ema(closes, 50)

    if   ema9 > ema21 > ema50: tendencia = "ALTA"
    elif ema9 < ema21 < ema50: tendencia = "BAIXA"
    else:                       tendencia = "LATERAL"

    if   rsi < 35 and macd_hist > 0 and tendencia != "BAIXA": sinal_bruto = "COMPRA"
    elif rsi > 65 and macd_hist < 0 and tendencia != "ALTA":  sinal_bruto = "VENDA"
    elif rsi < 30:                                             sinal_bruto = "COMPRA"
    elif rsi > 70:                                             sinal_bruto = "VENDA"
    else:                                                      sinal_bruto = "NEUTRO"

    return {
        "preco": round(p, 6), "rsi": rsi, "macd_hist": macd_hist,
        "bb_upper": bbu, "bb_lower": bbl, "atr": atr,
        "volume_ratio": vr, "ema9": round(ema9, 6), "ema21": round(ema21, 6),
        "ema50": round(ema50, 6), "tendencia": tendencia,
        "sinal_bruto": sinal_bruto, "tipo": tipo,
    }

def get_analysis(symbol, interval="15m"):
    dados  = fetch_candles(symbol, interval)
    closes = dados["closes"]
    vols   = dados["volumes"]
    fonte  = dados["fonte"]
    if len(closes) < 35: return None

    a    = analisar_closes(symbol, closes, vols)
    tipo = a["tipo"]
    p    = a["preco"]

    # ── Multi-Timeframe ──
    tf_up  = {"5m":"15m","15m":"1h","30m":"1h","1h":"4h","4h":"1d","1d":"1d"}.get(interval, "1h")
    mtf_ok = True
    tend_s = "LATERAL"
    if tf_up != interval:
        ds = fetch_candles(symbol, tf_up)
        if ds and len(ds["closes"]) >= 35:
            as_ = analisar_closes(symbol, ds["closes"], ds["volumes"])
            tend_s = as_["tendencia"]
            if a["sinal_bruto"] == "COMPRA" and tend_s == "BAIXA": mtf_ok = False
            if a["sinal_bruto"] == "VENDA"  and tend_s == "ALTA":  mtf_ok = False

    score = calcular_score(
        a["rsi"], a["macd_hist"], p, a["bb_upper"], a["bb_lower"],
        a["sinal_bruto"], a["volume_ratio"], mtf_ok
    )
    sinal     = a["sinal_bruto"] if (score >= SCORE_MINIMO and mtf_ok) else "NEUTRO"
    forca     = calcular_forca(a["rsi"], a["macd_hist"], sinal)
    confianca = round(50 + score / 2, 1) if sinal != "NEUTRO" else round(score * 0.6, 1)

    mult = ATR_MULTIPLIER.get(tipo, ATR_MULTIPLIER["Ações"])
    atr  = a["atr"]
    sl   = round(p - mult["stop"] * atr, 6) if sinal == "COMPRA" else round(p + mult["stop"] * atr, 6)
    tp   = round(p + mult["tp"]   * atr, 6) if sinal == "COMPRA" else round(p - mult["tp"]   * atr, 6)

    return {
        "preco": p, "rsi": a["rsi"], "macd_hist": a["macd_hist"],
        "bb_upper": a["bb_upper"], "bb_lower": a["bb_lower"],
        "volume_ratio": a["volume_ratio"],
        "ema9": a["ema9"], "ema21": a["ema21"], "ema50": a["ema50"],
        "tendencia": a["tendencia"], "tendencia_sup": tend_s,
        "sinal": sinal, "score": score, "forca": forca, "confianca": confianca,
        "mtf_ok": mtf_ok, "stop_loss": sl, "take_profit": tp, "fonte": fonte,
    }


# ============================================================
# HTML  — interface completa
# ============================================================

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Valverde Trade IA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#060a17;--bg2:#0c1122;--bg3:#101728;
  --border:rgba(255,255,255,0.06);--bord2:rgba(255,255,255,0.12);
  --text:#dde4f0;--muted:#4e6080;
  --accent:#38bdf8;--buy:#22c55e;--sell:#ef4444;--warn:#f59e0b;--sim:#f97316;
  --mono:'Space Mono',monospace;--sans:'DM Sans',sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);background:var(--bg);color:var(--text);min-height:100vh;padding:20px 16px}
body::before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.025'/%3E%3C/svg%3E");opacity:.6}
.wrap{position:relative;z-index:1;max-width:1380px;margin:0 auto}

/* Header */
.header{display:flex;align-items:center;justify-content:space-between;
  margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid var(--border)}
.logo-block{display:flex;align-items:baseline;gap:10px}
.logo{font-family:var(--mono);font-size:1.1rem;font-weight:700;color:var(--accent);letter-spacing:-.5px}
.logo-tag{font-family:var(--mono);font-size:.58rem;color:var(--muted);
  border:1px solid var(--bord2);padding:2px 7px;border-radius:4px}
.header-right{display:flex;align-items:center;gap:10px}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--buy);
  box-shadow:0 0 6px var(--buy);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.live-text{font-size:.65rem;color:var(--muted);font-family:var(--mono)}
.refresh-btn{background:transparent;border:1px solid var(--bord2);color:var(--text);
  cursor:pointer;font-family:var(--mono);font-size:.65rem;padding:5px 12px;border-radius:6px;
  transition:border-color .2s,color .2s}
.refresh-btn:hover{border-color:var(--accent);color:var(--accent)}

/* Tabs */
.tabs{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:14px}
.tab{font-family:var(--mono);font-size:.6rem;padding:5px 11px;border-radius:20px;cursor:pointer;
  border:1px solid var(--border);color:var(--muted);background:transparent;
  transition:all .15s;white-space:nowrap}
.tab:hover{border-color:var(--bord2);color:var(--text)}
.tab.active       {background:rgba(56,189,248,.12);border-color:var(--accent);color:var(--accent)}
.tab.t-fx.active  {background:rgba(139,92,246,.12);border-color:#8b5cf6;color:#8b5cf6}
.tab.t-co.active  {background:rgba(251,191,36,.1); border-color:#fbbf24;color:#fbbf24}
.tab.t-cr.active  {background:rgba(249,115,22,.1); border-color:#f97316;color:#f97316}
.tab.t-id.active  {background:rgba(20,184,166,.1); border-color:#14b8a6;color:#14b8a6}
.tab.t-ac.active  {background:rgba(34,197,94,.1);  border-color:#22c55e;color:#22c55e}

/* Grid */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}

/* Panel */
.panel{background:var(--bg2);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.panel-head{display:flex;align-items:center;justify-content:space-between;
  padding:12px 16px;border-bottom:1px solid var(--border);background:var(--bg3)}
.panel-title{font-family:var(--mono);font-size:.65rem;letter-spacing:.08em;
  color:var(--muted);text-transform:uppercase}
.panel-count{font-family:var(--mono);font-size:.58rem;
  background:rgba(56,189,248,.1);color:var(--accent);padding:2px 8px;border-radius:20px}
.panel-body{padding:12px;max-height:82vh;overflow-y:auto}
.panel-body::-webkit-scrollbar{width:3px}
.panel-body::-webkit-scrollbar-thumb{background:var(--bord2);border-radius:3px}

/* Signal Card */
.sig-card{background:var(--bg3);border:1px solid var(--border);border-radius:11px;
  padding:12px 14px;margin-bottom:9px;cursor:pointer;transition:border-color .18s,transform .12s}
.sig-card:hover{border-color:var(--bord2);transform:translateY(-1px)}
.sig-card.buy    {border-left:3px solid var(--buy)}
.sig-card.sell   {border-left:3px solid var(--sell)}
.sig-card.neutral{border-left:3px solid var(--warn)}

.sig-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.sig-asset{display:flex;align-items:center;gap:8px}
.sig-emoji{font-size:.95rem}
.sig-name{font-weight:600;font-size:.88rem}
.sig-sub{font-size:.58rem;color:var(--muted);font-family:var(--mono);margin-top:1px}

.badge{font-family:var(--mono);font-size:.62rem;font-weight:700;
  padding:3px 9px;border-radius:5px;letter-spacing:.05em}
.badge.buy    {background:rgba(34,197,94,.14); color:var(--buy); border:1px solid rgba(34,197,94,.28)}
.badge.sell   {background:rgba(239,68,68,.14); color:var(--sell);border:1px solid rgba(239,68,68,.28)}
.badge.neutral{background:rgba(245,158,11,.14);color:var(--warn);border:1px solid rgba(245,158,11,.28)}
.badge.sim    {background:rgba(249,115,22,.1); color:var(--sim); border:1px solid rgba(249,115,22,.25);font-size:.52rem;margin-left:3px}

/* Levels */
.sig-levels{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-bottom:8px}
.level{background:rgba(0,0,0,.22);border-radius:6px;padding:5px 7px;text-align:center}
.lbl{font-size:.52rem;color:var(--muted);font-family:var(--mono);text-transform:uppercase;margin-bottom:2px}
.val{font-family:var(--mono);font-size:.75rem;font-weight:700}
.val.entry{color:var(--accent)}.val.stop{color:var(--sell)}.val.tp{color:var(--buy)}

/* 3 metric bars */
.metrics{display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-bottom:7px}
.mbox{background:rgba(0,0,0,.18);border-radius:6px;padding:5px 7px}
.mlbl{font-size:.52rem;color:var(--muted);font-family:var(--mono);text-transform:uppercase;margin-bottom:3px}
.mbar-w{height:3px;background:rgba(255,255,255,.05);border-radius:2px}
.mbar{height:100%;border-radius:2px;transition:width .5s ease}
.mval{font-family:var(--mono);font-size:.65rem;font-weight:700;margin-top:3px}
.b-score.high{background:var(--buy)}.b-score.mid{background:var(--warn)}.b-score.low{background:var(--sell)}
.b-conf{background:#8b5cf6}.b-forca{background:#38bdf8}

/* Indicator chips */
.ind-row{display:flex;flex-wrap:wrap;gap:4px;margin-top:5px}
.chip{font-family:var(--mono);font-size:.56rem;padding:2px 6px;border-radius:3px;
  background:rgba(255,255,255,.03);border:1px solid var(--border);color:var(--muted)}
.chip span{color:var(--text)}
.mtf-ok  {background:rgba(34,197,94,.08); color:var(--buy); border:1px solid rgba(34,197,94,.2)}
.mtf-fail{background:rgba(239,68,68,.08); color:var(--sell);border:1px solid rgba(239,68,68,.2)}

/* Histórico */
.hist-item{background:var(--bg3);border:1px solid var(--border);
  border-radius:9px;padding:10px 12px;margin-bottom:7px}
.hist-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.hist-asset{font-weight:600;font-size:.82rem}
.hist-tf{font-family:var(--mono);font-size:.55rem;color:var(--muted);margin-left:4px}
.hist-res{font-family:var(--mono);font-size:.6rem;font-weight:700;padding:2px 8px;border-radius:4px}
.hist-res.win {background:rgba(34,197,94,.1); color:var(--buy)}
.hist-res.loss{background:rgba(239,68,68,.1); color:var(--sell)}
.hist-res.pend{background:rgba(245,158,11,.1);color:var(--warn)}
.hist-lvl{display:flex;flex-wrap:wrap;gap:8px;font-family:var(--mono);
  font-size:.6rem;color:var(--muted)}
.hist-lvl span{color:var(--text)}
.hist-date{font-family:var(--mono);font-size:.55rem;color:var(--muted);margin-top:4px}

.empty{text-align:center;padding:40px 20px;color:var(--muted);
  font-size:.78rem;font-family:var(--mono)}
.empty .ico{font-size:1.7rem;margin-bottom:10px}

.footer{margin-top:24px;padding-top:14px;border-top:1px solid var(--border);
  font-family:var(--mono);font-size:.58rem;color:var(--muted);text-align:center;line-height:2.1}
</style>
</head>
<body>
<div class="wrap">

<div class="header">
  <div class="logo-block">
    <span class="logo">VALVERDE TRADE IA</span>
    <span class="logo-tag">v3.0 · 22 ativos · MTF</span>
  </div>
  <div class="header-right">
    <div class="live-dot"></div>
    <span class="live-text" id="last-update">--:--</span>
    <button class="refresh-btn" onclick="carregarTudo()">↻ ATUALIZAR</button>
  </div>
</div>

<div class="tabs">
  <button class="tab active"  data-cat="Todos"       onclick="setTab(this,'Todos')">Todos (22)</button>
  <button class="tab t-fx"    data-cat="Forex"       onclick="setTab(this,'Forex')">💱 Forex (7)</button>
  <button class="tab t-co"    data-cat="Commodities" onclick="setTab(this,'Commodities')">🛢 Commodities (6)</button>
  <button class="tab t-cr"    data-cat="Cripto"      onclick="setTab(this,'Cripto')">₿ Cripto (2)</button>
  <button class="tab t-id"    data-cat="Índices"     onclick="setTab(this,'Índices')">📊 Índices (6)</button>
  <button class="tab t-ac"    data-cat="Ações"       onclick="setTab(this,'Ações')">🍎 Ações (2)</button>
</div>

<div class="grid">
  <div class="panel">
    <div class="panel-head">
      <span class="panel-title">Sinais Recentes · 15m</span>
      <span class="panel-count" id="count-sinais">—</span>
    </div>
    <div class="panel-body" id="sinais-container">
      <div class="empty"><div class="ico">⟳</div>Carregando 22 ativos...</div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-head">
      <span class="panel-title">Histórico de Sinais</span>
      <span class="panel-count" id="count-hist">—</span>
    </div>
    <div class="panel-body" id="historico-container">
      <div class="empty"><div class="ico">⟳</div>Carregando...</div>
    </div>
  </div>
</div>

<div class="footer">
  VALVERDE TRADE IA v3.0 · Forex · Commodities · Cripto · Índices · Ações<br>
  RSI · MACD · Bollinger Bands · EMA 9/21/50 · Volume · ATR · Multi-Timeframe · Score ≥ 65<br>
  ⚠ Apenas fins educacionais — não constitui recomendação de investimento
</div>
</div>

<script>
let todosOsSinais = [];
let catAtual = 'Todos';

function fmtPreco(v, tipo) {
  if (v == null) return '—';
  const n = Number(v);
  if (tipo === 'Forex') return n.toFixed(5);
  if (n > 10000) return n.toLocaleString('pt-BR',{maximumFractionDigits:0});
  if (n > 100)   return n.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});
  if (n > 1)     return n.toFixed(3);
  return n.toFixed(5);
}

function scoreClass(s){ return s>=75?'high':s>=65?'mid':'low'; }

function renderSinais(sinais) {
  const list = catAtual==='Todos' ? sinais : sinais.filter(s=>s.tipo===catAtual);
  document.getElementById('count-sinais').textContent = list.length + ' ativos';
  const el = document.getElementById('sinais-container');
  if (!list.length){
    el.innerHTML='<div class="empty"><div class="ico">📡</div>Sem sinais para esta categoria</div>';
    return;
  }
  el.innerHTML = list.map(s=>{
    const cls  = s.sinal==='COMPRA'?'buy':s.sinal==='VENDA'?'sell':'neutral';
    const sc   = scoreClass(s.score);
    const mhS  = s.macd_hist>=0?'+':'';
    const vcol = s.volume_ratio>=1.2?'color:var(--buy)':s.volume_ratio<0.9?'color:var(--sell)':'';
    const sim  = s.fonte==='simulado'?`<span class="badge sim">SIM</span>`:'';
    const fp   = v => fmtPreco(v,s.tipo);
    const sinalLabel = s.sinal==='COMPRA'?'▲ COMPRA':s.sinal==='VENDA'?'▼ VENDA':'— NEUTRO';
    const mhFmt = Math.abs(s.macd_hist)<0.000001
      ? s.macd_hist.toExponential(2)
      : Number(s.macd_hist).toFixed(6);

    return `
    <div class="sig-card ${cls}" onclick='abrirConfirmacao(${JSON.stringify(s)})'>
      <div class="sig-top">
        <div class="sig-asset">
          <span class="sig-emoji">${s.emoji}</span>
          <div>
            <div class="sig-name">${s.nome_exibicao} ${sim}</div>
            <div class="sig-sub">${s.tipo} · ${s.nome} · ${s.timeframe}</div>
          </div>
        </div>
        <span class="badge ${cls}">${sinalLabel}</span>
      </div>

      <div class="sig-levels">
        <div class="level"><div class="lbl">Entry</div><div class="val entry">${fp(s.preco)}</div></div>
        <div class="level"><div class="lbl">Stop</div><div class="val stop">${fp(s.stop_loss)}</div></div>
        <div class="level"><div class="lbl">TP</div><div class="val tp">${fp(s.take_profit)}</div></div>
      </div>

      <div class="metrics">
        <div class="mbox">
          <div class="mlbl">Score</div>
          <div class="mbar-w"><div class="mbar b-score ${sc}" style="width:${s.score}%"></div></div>
          <div class="mval">${s.score}/100</div>
        </div>
        <div class="mbox">
          <div class="mlbl">Confiança</div>
          <div class="mbar-w"><div class="mbar b-conf" style="width:${s.confianca}%"></div></div>
          <div class="mval">${s.confianca}%</div>
        </div>
        <div class="mbox">
          <div class="mlbl">Força</div>
          <div class="mbar-w"><div class="mbar b-forca" style="width:${s.forca}%"></div></div>
          <div class="mval">${s.forca}%</div>
        </div>
      </div>

      <div class="ind-row">
        <span class="chip">RSI <span>${s.rsi}</span></span>
        <span class="chip">MACD <span>${mhS}${mhFmt}</span></span>
        <span class="chip">Vol <span style="${vcol}">${s.volume_ratio}×</span></span>
        <span class="chip">Tend <span>${s.tendencia}</span></span>
        <span class="chip ${s.mtf_ok?'mtf-ok':'mtf-fail'}">${s.mtf_ok?'✓':'✗'} MTF</span>
      </div>
    </div>`;
  }).join('');
}

function renderHistorico(hist) {
  const el = document.getElementById('historico-container');
  document.getElementById('count-hist').textContent = hist.length + ' registros';
  if (!hist.length){
    el.innerHTML='<div class="empty"><div class="ico">📋</div>Nenhum sinal confirmado ainda<br><small>Clique em um card para registrar WIN/LOSS</small></div>';
    return;
  }
  el.innerHTML=[...hist].reverse().map(h=>{
    const rc=h.confirmado==='win'?'win':h.confirmado==='loss'?'loss':'pend';
    const rt=h.confirmado==='win'?'✓ WIN':h.confirmado==='loss'?'✗ LOSS':'◌ Pend';
    const fp=v=>fmtPreco(v,h.tipo||'');
    return `
    <div class="hist-item">
      <div class="hist-top">
        <div><span class="hist-asset">${h.emoji||'📊'} ${h.nome_exibicao||h.nome}</span>
          <span class="hist-tf">${h.timeframe} · ${h.sinal}</span></div>
        <span class="hist-res ${rc}">${rt}</span>
      </div>
      <div class="hist-lvl">
        Entry:<span>${fp(h.entry)}</span>
        Stop:<span>${fp(h.stop_loss)}</span>
        TP:<span>${fp(h.take_profit)}</span>
        Score:<span>${h.score||'—'}</span>
        Conf:<span>${h.confianca||'—'}%</span>
        Força:<span>${h.forca||'—'}%</span>
      </div>
      <div class="hist-date">${h.data||h.data_confirmacao||'—'}</div>
    </div>`;
  }).join('');
}

function setTab(el, cat) {
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  catAtual=cat;
  renderSinais(todosOsSinais);
}

async function carregarSinais() {
  try {
    const r=await fetch('/api/sinais');
    todosOsSinais=await r.json();
    renderSinais(todosOsSinais);
    document.getElementById('last-update').textContent=
      new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
  } catch(e){
    document.getElementById('sinais-container').innerHTML=
      `<div class="empty"><div class="ico">⚠</div>Erro: ${e.message}</div>`;
  }
}

async function carregarHistorico() {
  try {
    const r=await fetch('/historico');
    renderHistorico(await r.json());
  } catch(e){
    document.getElementById('historico-container').innerHTML=
      `<div class="empty"><div class="ico">⚠</div>Erro: ${e.message}</div>`;
  }
}

function abrirConfirmacao(s) {
  const fp=v=>fmtPreco(v,s.tipo);
  const res=confirm(
    `CONFIRMAR SINAL\n\n${s.emoji} ${s.nome_exibicao} · ${s.tipo} · ${s.timeframe}\n`+
    `Sinal: ${s.sinal}  |  Score: ${s.score}/100\n`+
    `Confiança: ${s.confianca}%  |  Força: ${s.forca}%\n`+
    `Entry: ${fp(s.preco)}  |  Stop: ${fp(s.stop_loss)}  |  TP: ${fp(s.take_profit)}\n`+
    `RSI: ${s.rsi}  |  MTF: ${s.mtf_ok?'OK':'FALHOU'}\n\n`+
    `OK = WIN   ·   Cancelar = LOSS`
  );
  if(res===null) return;
  fetch('/confirmar',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      simbolo:s.symbol,nome:s.nome,nome_exibicao:s.nome_exibicao,
      emoji:s.emoji,tipo:s.tipo,timeframe:s.timeframe,sinal:s.sinal,
      entry:s.preco,stop_loss:s.stop_loss,take_profit:s.take_profit,
      score:s.score,confianca:s.confianca,forca:s.forca,
      fonte:s.fonte,confirmado:res?'win':'loss',
      data:new Date().toLocaleString('pt-BR')
    })
  }).then(()=>carregarHistorico());
}

async function carregarTudo(){
  await Promise.all([carregarSinais(),carregarHistorico()]);
}
carregarTudo();
setInterval(carregarSinais,300_000);
</script>
</body>
</html>"""


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)

@app.get("/api/sinais")
async def get_sinais():
    sinais = []
    for symbol, cfg in SYMBOL_CONFIG.items():
        analysis = get_analysis(symbol, "15m")
        if not analysis:
            continue
        sinais.append({
            "symbol":        symbol,
            "nome":          cfg["nome"],
            "nome_exibicao": cfg["nome_exibicao"],
            "emoji":         cfg["emoji"],
            "tipo":          cfg["tipo"],
            "timeframe":     "15m",
            "preco":         analysis["preco"],
            "sinal":         analysis["sinal"],
            "score":         analysis["score"],
            "forca":         analysis["forca"],
            "confianca":     analysis["confianca"],
            "rsi":           analysis["rsi"],
            "macd_hist":     analysis["macd_hist"],
            "bb_upper":      analysis["bb_upper"],
            "bb_lower":      analysis["bb_lower"],
            "volume_ratio":  analysis["volume_ratio"],
            "tendencia":     analysis["tendencia"],
            "tendencia_sup": analysis["tendencia_sup"],
            "mtf_ok":        analysis["mtf_ok"],
            "stop_loss":     analysis["stop_loss"],
            "take_profit":   analysis["take_profit"],
            "entry":         analysis["preco"],
            "fonte":         analysis["fonte"],
            "data":          datetime.now().strftime("%d/%m %H:%M"),
        })
    return sinais

@app.get("/historico")
async def get_historico():
    return carregar_historico()

@app.post("/confirmar")
async def confirmar_sinal(sinal: dict):
    h = carregar_historico()
    h.append(sinal)
    salvar_historico(h)
    return {"ok": True}
