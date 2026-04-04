"""
VALVERDE TRADE IA - Sinais Precisos
Melhorias: MTF, Score Ponderado, MACD, Bollinger Bands, ATR por ativo, Volume, Badge Simulado
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime
import os
import json
import requests
import time

app = FastAPI(title="Valverde Trade IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# CONFIGURAÇÕES
# ============================================

SYMBOL_CONFIG = {
    "GC=F":    {"symbol": "XAUUSD",  "nome": "XAU",  "tipo": "Commodities", "emoji": "🥇", "nome_exibicao": "Ouro"},
    "BTC-USD": {"symbol": "BTCUSDT", "nome": "BTC",  "tipo": "Cripto",      "emoji": "₿",  "nome_exibicao": "Bitcoin"},
    "ETH-USD": {"symbol": "ETHUSDT", "nome": "ETH",  "tipo": "Cripto",      "emoji": "⟠",  "nome_exibicao": "Ethereum"},
    "AAPL":    {"symbol": "AAPL",    "nome": "AAPL", "tipo": "Ações",       "emoji": "🍎", "nome_exibicao": "Apple"},
    "NVDA":    {"symbol": "NVDA",    "nome": "NVDA", "tipo": "Ações",       "emoji": "🎮", "nome_exibicao": "NVIDIA"},
}

# Multiplicadores ATR por tipo de ativo (Stop, TP) — R:R mínimo de 1.5:1
ATR_MULTIPLIER = {
    "Cripto":      {"stop": 2.5, "tp": 4.0},
    "Commodities": {"stop": 2.0, "tp": 3.5},
    "Ações":       {"stop": 1.5, "tp": 2.5},
}

SCORE_MINIMO = 65   # Só emite sinal se score >= 65

HISTORICO_FILE = "historico_sinais.json"

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_historico(historico):
    with open(HISTORICO_FILE, "w") as f:
        json.dump(historico, f, indent=2)


# ============================================
# INDICADORES TÉCNICOS
# ============================================

def calcular_ema(closes, periodo):
    if len(closes) < periodo:
        return closes[-1]
    k = 2 / (periodo + 1)
    ema = sum(closes[:periodo]) / periodo
    for preco in closes[periodo:]:
        ema = preco * k + ema * (1 - k)
    return ema


def calcular_rsi(closes, periodo=14):
    if len(closes) < periodo + 1:
        return 50.0
    ganhos, perdas = 0.0, 0.0
    for i in range(-periodo, 0):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            ganhos += diff
        else:
            perdas += abs(diff)
    if perdas == 0:
        return 100.0
    rs = ganhos / perdas
    return round(100 - (100 / (1 + rs)), 1)


def calcular_macd(closes, fast=12, slow=26, signal_period=9):
    """Retorna (macd_line, signal_line, histograma)"""
    if len(closes) < slow + signal_period:
        return 0.0, 0.0, 0.0
    ema_fast   = calcular_ema(closes, fast)
    ema_slow   = calcular_ema(closes, slow)
    macd_line  = ema_fast - ema_slow

    # Calcula EMA do MACD para a signal line
    macd_values = []
    for i in range(slow - 1, len(closes)):
        ef = calcular_ema(closes[:i + 1], fast)
        es = calcular_ema(closes[:i + 1], slow)
        macd_values.append(ef - es)

    if len(macd_values) < signal_period:
        return macd_line, macd_line, 0.0

    signal_line = calcular_ema(macd_values, signal_period)
    histograma  = macd_line - signal_line
    return round(macd_line, 4), round(signal_line, 4), round(histograma, 4)


def calcular_bollinger(closes, periodo=20, desvios=2):
    """Retorna (upper, middle, lower)"""
    if len(closes) < periodo:
        p = closes[-1]
        return p, p, p
    recentes  = closes[-periodo:]
    ma        = sum(recentes) / periodo
    variancia = sum((c - ma) ** 2 for c in recentes) / periodo
    std       = variancia ** 0.5
    return round(ma + desvios * std, 4), round(ma, 4), round(ma - desvios * std, 4)


def calcular_atr(closes, periodo=14):
    if len(closes) < 2:
        return closes[-1] * 0.005
    variacoes = [abs(closes[i] - closes[i - 1]) for i in range(max(-periodo, -(len(closes) - 1)), 0)]
    return sum(variacoes) / len(variacoes) if variacoes else closes[-1] * 0.005


def calcular_volume_ratio(volumes, periodo=20):
    """Volume atual vs média dos últimos N candles"""
    if not volumes or len(volumes) < 2:
        return 1.0
    media = sum(volumes[-periodo - 1:-1]) / min(periodo, len(volumes) - 1)
    if media == 0:
        return 1.0
    return round(volumes[-1] / media, 2)


def calcular_score(rsi, macd_hist, preco, bb_upper, bb_lower, sinal, volume_ratio, mtf_ok):
    """
    Score ponderado 0-100:
      RSI           30 pts
      MACD hist     25 pts
      Bollinger BB  25 pts
      Volume        10 pts
      MTF alinhado  10 pts
    """
    score = 0

    # RSI (30 pts)
    if sinal == "COMPRA":
        if rsi < 30:   score += 30
        elif rsi < 40: score += 22
        elif rsi < 50: score += 12
    else:
        if rsi > 70:   score += 30
        elif rsi > 60: score += 22
        elif rsi > 50: score += 12

    # MACD histograma (25 pts)
    if sinal == "COMPRA" and macd_hist > 0:  score += 25
    elif sinal == "VENDA" and macd_hist < 0: score += 25
    elif abs(macd_hist) < preco * 0.0005:    score += 10  # cruzando zero — sinal fraco

    # Bollinger Bands (25 pts)
    banda_largura = bb_upper - bb_lower
    if banda_largura > 0:
        posicao = (preco - bb_lower) / banda_largura  # 0 = fundo, 1 = topo
        if sinal == "COMPRA":
            if posicao <= 0.1:   score += 25
            elif posicao <= 0.3: score += 15
            elif posicao <= 0.5: score += 8
        else:
            if posicao >= 0.9:   score += 25
            elif posicao >= 0.7: score += 15
            elif posicao >= 0.5: score += 8

    # Volume (10 pts)
    if volume_ratio >= 1.5:   score += 10
    elif volume_ratio >= 1.2: score += 7
    elif volume_ratio >= 1.0: score += 4

    # MTF alinhado (10 pts)
    if mtf_ok:
        score += 10

    return min(score, 100)


# ============================================
# FONTES DE DADOS
# ============================================

def fetch_binance(symbol, interval, limit=100):
    binance_map = {"BTC-USD": "BTCUSDT", "ETH-USD": "ETHUSDT"}
    bs = binance_map.get(symbol)
    if not bs:
        return None
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={bs}&interval={interval}&limit={limit}"
        r   = requests.get(url, timeout=10)
        if r.status_code == 200:
            data    = r.json()
            closes  = [float(c[4]) for c in data]
            volumes = [float(c[5]) for c in data]
            return {"closes": closes, "volumes": volumes, "fonte": "binance"}
    except Exception as e:
        print(f"Binance error [{symbol}/{interval}]: {e}")
    return None


def fetch_yahoo(symbol, interval, limit=100):
    try:
        yahoo_interval = interval if interval != "4h" else "1h"
        range_map = {"5m": "5d", "15m": "5d", "30m": "5d", "1h": "30d", "4h": "60d", "1d": "6mo"}
        rng     = range_map.get(interval, "5d")
        url     = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={yahoo_interval}&range={rng}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r       = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            result = r.json().get("chart", {}).get("result", [])
            if result:
                q       = result[0].get("indicators", {}).get("quote", [{}])[0]
                closes  = [c for c in q.get("close",  []) if c is not None]
                volumes = [v for v in q.get("volume", []) if v is not None]
                if closes:
                    return {"closes": closes, "volumes": volumes, "fonte": "yahoo"}
    except Exception as e:
        print(f"Yahoo error [{symbol}/{interval}]: {e}")
    return None


def fetch_fallback(symbol, interval):
    import random
    base = {"GC=F": 4670, "BTC-USD": 66800, "ETH-USD": 3300, "AAPL": 220, "NVDA": 120}.get(symbol, 100)
    random.seed(int(time.time() / 300) + hash(symbol + interval) % 9999)
    closes  = [base * (1 + random.uniform(-0.025, 0.025)) for _ in range(100)]
    volumes = [random.uniform(800_000, 2_000_000) for _ in range(100)]
    return {"closes": closes, "volumes": volumes, "fonte": "simulado"}


def fetch_candles(symbol, interval):
    if symbol in ("BTC-USD", "ETH-USD"):
        d = fetch_binance(symbol, interval)
        if d:
            return d
    d = fetch_yahoo(symbol, interval)
    if d:
        return d
    return fetch_fallback(symbol, interval)


# ============================================
# ANÁLISE PRINCIPAL
# ============================================

def analisar(symbol, interval, closes, volumes):
    preco  = closes[-1]
    config = SYMBOL_CONFIG.get(symbol, {})
    tipo   = config.get("tipo", "Ações")

    # Indicadores
    rsi                      = calcular_rsi(closes)
    macd_line, signal_line, macd_hist = calcular_macd(closes)
    bb_upper, bb_middle, bb_lower     = calcular_bollinger(closes)
    atr                      = calcular_atr(closes)
    volume_ratio             = calcular_volume_ratio(volumes)

    # EMAs para tendência
    ema9  = calcular_ema(closes, 9)
    ema21 = calcular_ema(closes, 21)
    ema50 = calcular_ema(closes, 50)

    # Direção primária pelo EMA cruzamento
    if ema9 > ema21 > ema50:
        tendencia = "ALTA"
    elif ema9 < ema21 < ema50:
        tendencia = "BAIXA"
    else:
        tendencia = "LATERAL"

    # Sinal bruto
    if rsi < 35 and macd_hist > 0 and tendencia != "BAIXA":
        sinal_bruto = "COMPRA"
    elif rsi > 65 and macd_hist < 0 and tendencia != "ALTA":
        sinal_bruto = "VENDA"
    elif rsi < 30:
        sinal_bruto = "COMPRA"
    elif rsi > 70:
        sinal_bruto = "VENDA"
    else:
        sinal_bruto = "NEUTRO"

    return {
        "preco":        round(preco, 4),
        "rsi":          rsi,
        "macd_hist":    macd_hist,
        "bb_upper":     bb_upper,
        "bb_middle":    bb_middle,
        "bb_lower":     bb_lower,
        "atr":          atr,
        "volume_ratio": volume_ratio,
        "ema9":         round(ema9,  4),
        "ema21":        round(ema21, 4),
        "ema50":        round(ema50, 4),
        "tendencia":    tendencia,
        "sinal_bruto":  sinal_bruto,
        "tipo":         tipo,
    }


def get_analysis(symbol, interval):
    """Análise completa com MTF, score ponderado e filtros"""
    # Timeframe principal
    dados   = fetch_candles(symbol, interval)
    closes  = dados["closes"]
    volumes = dados["volumes"]
    fonte   = dados["fonte"]

    if len(closes) < 30:
        return None

    analise = analisar(symbol, interval, closes, volumes)
    preco   = analise["preco"]
    tipo    = analise["tipo"]

    # ── Multi-timeframe: validação no timeframe superior ──
    tf_superior_map = {"5m": "15m", "15m": "1h", "30m": "1h", "1h": "4h", "4h": "1d", "1d": "1d"}
    tf_superior     = tf_superior_map.get(interval, "1h")
    mtf_ok          = True
    tendencia_sup   = "LATERAL"

    if tf_superior != interval:
        dados_sup = fetch_candles(symbol, tf_superior)
        if dados_sup and len(dados_sup["closes"]) >= 30:
            analise_sup  = analisar(symbol, tf_superior, dados_sup["closes"], dados_sup["volumes"])
            tendencia_sup = analise_sup["tendencia"]
            sinal_bruto   = analise["sinal_bruto"]
            # Conflito: sinal de compra em tendência de baixa (ou vice-versa)
            if sinal_bruto == "COMPRA" and tendencia_sup == "BAIXA":
                mtf_ok = False
            elif sinal_bruto == "VENDA" and tendencia_sup == "ALTA":
                mtf_ok = False

    # ── Score ponderado ──
    score = calcular_score(
        rsi          = analise["rsi"],
        macd_hist    = analise["macd_hist"],
        preco        = preco,
        bb_upper     = analise["bb_upper"],
        bb_lower     = analise["bb_lower"],
        sinal        = analise["sinal_bruto"],
        volume_ratio = analise["volume_ratio"],
        mtf_ok       = mtf_ok,
    )

    # ── Filtro de score mínimo ──
    sinal_final = analise["sinal_bruto"]
    if score < SCORE_MINIMO or not mtf_ok:
        sinal_final = "NEUTRO"

    # ── Stop / TP ajustados por tipo de ativo ──
    mult       = ATR_MULTIPLIER.get(tipo, ATR_MULTIPLIER["Ações"])
    atr        = analise["atr"]
    stop_loss  = round(preco - mult["stop"] * atr, 4) if sinal_final == "COMPRA" else round(preco + mult["stop"] * atr, 4)
    take_profit= round(preco + mult["tp"]   * atr, 4) if sinal_final == "COMPRA" else round(preco - mult["tp"]   * atr, 4)

    return {
        "preco":          preco,
        "rsi":            analise["rsi"],
        "macd_hist":      analise["macd_hist"],
        "bb_upper":       analise["bb_upper"],
        "bb_lower":       analise["bb_lower"],
        "volume_ratio":   analise["volume_ratio"],
        "ema9":           analise["ema9"],
        "ema21":          analise["ema21"],
        "ema50":          analise["ema50"],
        "tendencia":      analise["tendencia"],
        "tendencia_sup":  tendencia_sup,
        "sinal":          sinal_final,
        "score":          score,
        "mtf_ok":         mtf_ok,
        "stop_loss":      stop_loss,
        "take_profit":    take_profit,
        "fonte":          fonte,
    }


# ============================================
# INTERFACE HTML
# ============================================

HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Valverde Trade IA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #070b18;
    --bg2:      #0d1226;
    --bg3:      #121830;
    --border:   rgba(255,255,255,0.07);
    --border2:  rgba(255,255,255,0.13);
    --text:     #e2e8f0;
    --muted:    #64748b;
    --accent:   #38bdf8;
    --buy:      #22c55e;
    --sell:     #ef4444;
    --neutral:  #f59e0b;
    --sim:      #f97316;
    --mono:     'Space Mono', monospace;
    --sans:     'DM Sans', sans-serif;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 24px 20px;
  }

  /* Noise texture overlay */
  body::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    pointer-events: none; opacity: .6;
  }

  .wrap { position: relative; z-index: 1; max-width: 1340px; margin: 0 auto; }

  /* ── Header ── */
  .header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 32px; padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }
  .logo-block { display: flex; align-items: baseline; gap: 10px; }
  .logo {
    font-family: var(--mono);
    font-size: 1.25rem; font-weight: 700;
    color: var(--accent);
    letter-spacing: -0.5px;
  }
  .logo-tag {
    font-family: var(--mono);
    font-size: 0.65rem; color: var(--muted);
    border: 1px solid var(--border2);
    padding: 2px 7px; border-radius: 4px;
  }
  .header-right { display: flex; align-items: center; gap: 12px; }
  .live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--buy);
    box-shadow: 0 0 6px var(--buy);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% { opacity: 1; } 50% { opacity: 0.4; }
  }
  .live-text { font-size: 0.72rem; color: var(--muted); font-family: var(--mono); }
  .refresh-btn {
    background: transparent;
    border: 1px solid var(--border2);
    color: var(--text); cursor: pointer;
    font-family: var(--mono); font-size: 0.7rem;
    padding: 6px 14px; border-radius: 6px;
    transition: border-color .2s, color .2s;
  }
  .refresh-btn:hover { border-color: var(--accent); color: var(--accent); }

  /* ── Grid ── */
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }

  /* ── Panel ── */
  .panel {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 16px; overflow: hidden;
  }
  .panel-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg3);
  }
  .panel-title {
    font-family: var(--mono); font-size: 0.72rem;
    letter-spacing: 0.08em; color: var(--muted);
    text-transform: uppercase;
  }
  .panel-count {
    font-family: var(--mono); font-size: 0.65rem;
    background: rgba(56,189,248,0.1);
    color: var(--accent); padding: 2px 8px;
    border-radius: 20px;
  }
  .panel-body { padding: 16px; max-height: 78vh; overflow-y: auto; }
  .panel-body::-webkit-scrollbar { width: 3px; }
  .panel-body::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

  /* ── Signal Card ── */
  .sig-card {
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 12px; padding: 14px 16px;
    margin-bottom: 12px; cursor: pointer;
    transition: border-color .2s, transform .15s;
  }
  .sig-card:hover { border-color: var(--border2); transform: translateY(-1px); }
  .sig-card.buy  { border-left: 3px solid var(--buy); }
  .sig-card.sell { border-left: 3px solid var(--sell); }
  .sig-card.neutral { border-left: 3px solid var(--neutral); }

  .sig-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .sig-asset { display: flex; align-items: center; gap: 8px; }
  .sig-emoji { font-size: 1.1rem; }
  .sig-name { font-weight: 600; font-size: 0.95rem; }
  .sig-type { font-size: 0.65rem; color: var(--muted); font-family: var(--mono); }

  .badge {
    font-family: var(--mono); font-size: 0.68rem; font-weight: 700;
    padding: 4px 10px; border-radius: 5px; letter-spacing: 0.05em;
  }
  .badge.buy     { background: rgba(34,197,94,.15);  color: var(--buy);  border: 1px solid rgba(34,197,94,.3);  }
  .badge.sell    { background: rgba(239,68,68,.15);  color: var(--sell); border: 1px solid rgba(239,68,68,.3);  }
  .badge.neutral { background: rgba(245,158,11,.15); color: var(--neutral); border: 1px solid rgba(245,158,11,.3); }
  .badge.sim     { background: rgba(249,115,22,.12); color: var(--sim);  border: 1px solid rgba(249,115,22,.3);  font-size: 0.6rem; margin-left: 6px; }

  .sig-levels {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 8px; margin-bottom: 12px;
  }
  .level { background: rgba(0,0,0,0.25); border-radius: 7px; padding: 7px 10px; text-align: center; }
  .level-lbl { font-size: 0.58rem; color: var(--muted); font-family: var(--mono); text-transform: uppercase; margin-bottom: 3px; }
  .level-val { font-family: var(--mono); font-size: 0.82rem; font-weight: 700; }
  .level-val.entry   { color: var(--accent); }
  .level-val.stop    { color: var(--sell); }
  .level-val.tp      { color: var(--buy); }

  /* ── Score Bar ── */
  .score-row {
    display: flex; align-items: center; gap: 10px;
    font-size: 0.7rem; color: var(--muted); font-family: var(--mono);
  }
  .score-bar { flex: 1; height: 3px; background: rgba(255,255,255,.06); border-radius: 2px; }
  .score-fill { height: 100%; border-radius: 2px; transition: width .6s ease; }
  .score-fill.high   { background: var(--buy); }
  .score-fill.mid    { background: var(--neutral); }
  .score-fill.low    { background: var(--sell); }

  /* ── Indicators row ── */
  .ind-row {
    display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px;
  }
  .ind-chip {
    font-family: var(--mono); font-size: 0.6rem;
    padding: 2px 8px; border-radius: 4px;
    background: rgba(255,255,255,.04);
    border: 1px solid var(--border);
    color: var(--muted);
  }
  .ind-chip span { color: var(--text); }

  .mtf-chip {
    font-family: var(--mono); font-size: 0.6rem;
    padding: 2px 8px; border-radius: 4px;
  }
  .mtf-ok   { background: rgba(34,197,94,.1);  color: var(--buy);  border: 1px solid rgba(34,197,94,.2); }
  .mtf-fail { background: rgba(239,68,68,.1);  color: var(--sell); border: 1px solid rgba(239,68,68,.2); }

  /* ── Histórico ── */
  .hist-item {
    background: var(--bg3); border: 1px solid var(--border);
    border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;
  }
  .hist-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
  .hist-asset { font-weight: 600; font-size: 0.88rem; }
  .hist-tf { font-family: var(--mono); font-size: 0.6rem; color: var(--muted); margin-left: 6px; }
  .hist-result { font-family: var(--mono); font-size: 0.65rem; font-weight: 700; padding: 2px 9px; border-radius: 4px; }
  .hist-result.win  { background: rgba(34,197,94,.12);  color: var(--buy);  }
  .hist-result.loss { background: rgba(239,68,68,.12);  color: var(--sell); }
  .hist-result.pend { background: rgba(245,158,11,.12); color: var(--neutral); }

  .hist-levels { display: flex; gap: 16px; font-family: var(--mono); font-size: 0.68rem; color: var(--muted); }
  .hist-levels span { color: var(--text); }
  .hist-date { font-family: var(--mono); font-size: 0.6rem; color: var(--muted); margin-top: 6px; }

  /* ── Empty / Loading ── */
  .empty { text-align: center; padding: 48px 20px; color: var(--muted); font-size: 0.82rem; font-family: var(--mono); }
  .empty .ico { font-size: 2rem; margin-bottom: 10px; }

  /* ── Footer ── */
  .footer {
    margin-top: 32px; padding-top: 20px;
    border-top: 1px solid var(--border);
    font-family: var(--mono); font-size: 0.62rem;
    color: var(--muted); text-align: center; line-height: 2;
  }
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div class="logo-block">
      <span class="logo">VALVERDE TRADE IA</span>
      <span class="logo-tag">v2.0 · MTF + Score</span>
    </div>
    <div class="header-right">
      <div class="live-dot"></div>
      <span class="live-text" id="last-update">--:--</span>
      <button class="refresh-btn" onclick="carregarTudo()">↻ ATUALIZAR</button>
    </div>
  </div>

  <div class="grid">
    <!-- Sinais -->
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">Sinais Recentes · 15m</span>
        <span class="panel-count" id="count-sinais">—</span>
      </div>
      <div class="panel-body" id="sinais-container">
        <div class="empty"><div class="ico">⟳</div>Carregando...</div>
      </div>
    </div>

    <!-- Histórico -->
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
    VALVERDE TRADE IA · Análise Multi-Timeframe · Score ≥ 65 para emissão de sinal<br>
    RSI · MACD · Bollinger Bands · EMA · Volume · ATR calibrado por ativo<br>
    ⚠ Apenas fins educacionais — não é recomendação de investimento
  </div>
</div>

<script>
function fmt(n, d=2) {
  if (n == null) return '—';
  return Number(n).toLocaleString('pt-BR', {minimumFractionDigits:d, maximumFractionDigits:d});
}

function scoreClass(s) {
  if (s >= 75) return 'high';
  if (s >= 65) return 'mid';
  return 'low';
}

function renderSinais(sinais) {
  const el = document.getElementById('sinais-container');
  document.getElementById('count-sinais').textContent = sinais.length + ' ativos';

  if (!sinais.length) {
    el.innerHTML = '<div class="empty"><div class="ico">📡</div>Nenhum sinal disponível</div>';
    return;
  }

  el.innerHTML = sinais.map(s => {
    const cls  = s.sinal === 'COMPRA' ? 'buy' : s.sinal === 'VENDA' ? 'sell' : 'neutral';
    const bcls = s.sinal === 'COMPRA' ? 'buy' : s.sinal === 'VENDA' ? 'sell' : 'neutral';
    const scls = scoreClass(s.score);
    const mtfHtml = s.mtf_ok
      ? `<span class="mtf-chip mtf-ok">✓ MTF</span>`
      : `<span class="mtf-chip mtf-fail">✗ MTF</span>`;
    const simBadge = s.fonte === 'simulado' ? `<span class="badge sim">SIMULADO</span>` : '';
    const macdSign = s.macd_hist >= 0 ? '+' : '';
    const volColor = s.volume_ratio >= 1.2 ? 'color:var(--buy)' : s.volume_ratio < 0.9 ? 'color:var(--sell)' : '';

    return `
    <div class="sig-card ${cls}" onclick="abrirConfirmacao(${JSON.stringify(s)})">
      <div class="sig-top">
        <div class="sig-asset">
          <span class="sig-emoji">${s.emoji}</span>
          <div>
            <div class="sig-name">${s.nome_exibicao} ${simBadge}</div>
            <div class="sig-type">${s.tipo} · ${s.timeframe}</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
          <span class="badge ${bcls}">${s.sinal === 'COMPRA' ? '▲ COMPRA' : s.sinal === 'VENDA' ? '▼ VENDA' : '— NEUTRO'}</span>
        </div>
      </div>

      <div class="sig-levels">
        <div class="level">
          <div class="level-lbl">Entry</div>
          <div class="level-val entry">${fmt(s.preco, s.preco > 100 ? 2 : 4)}</div>
        </div>
        <div class="level">
          <div class="level-lbl">Stop</div>
          <div class="level-val stop">${fmt(s.stop_loss, s.stop_loss > 100 ? 2 : 4)}</div>
        </div>
        <div class="level">
          <div class="level-lbl">TP</div>
          <div class="level-val tp">${fmt(s.take_profit, s.take_profit > 100 ? 2 : 4)}</div>
        </div>
      </div>

      <div class="score-row">
        <span>SCORE</span>
        <div class="score-bar">
          <div class="score-fill ${scls}" style="width:${s.score}%"></div>
        </div>
        <span>${s.score}/100</span>
      </div>

      <div class="ind-row">
        <span class="ind-chip">RSI <span>${s.rsi}</span></span>
        <span class="ind-chip">MACD <span>${macdSign}${fmt(s.macd_hist,4)}</span></span>
        <span class="ind-chip">Vol <span style="${volColor}">${s.volume_ratio}×</span></span>
        <span class="ind-chip">Tend <span>${s.tendencia}</span></span>
        ${mtfHtml}
      </div>
    </div>`;
  }).join('');
}

function renderHistorico(hist) {
  const el = document.getElementById('historico-container');
  document.getElementById('count-hist').textContent = hist.length + ' registros';

  if (!hist.length) {
    el.innerHTML = '<div class="empty"><div class="ico">📋</div>Nenhum sinal confirmado ainda<br><small>Clique em um sinal para registrar WIN ou LOSS</small></div>';
    return;
  }

  el.innerHTML = [...hist].reverse().map(h => {
    const rc = h.confirmado === 'win' ? 'win' : h.confirmado === 'loss' ? 'loss' : 'pend';
    const rt = h.confirmado === 'win' ? '✓ WIN' : h.confirmado === 'loss' ? '✗ LOSS' : '◌ Pendente';
    return `
    <div class="hist-item">
      <div class="hist-top">
        <div>
          <span class="hist-asset">${h.emoji || '📊'} ${h.nome_exibicao || h.nome}</span>
          <span class="hist-tf">${h.timeframe} · ${h.sinal}</span>
        </div>
        <span class="hist-result ${rc}">${rt}</span>
      </div>
      <div class="hist-levels">
        Entry: <span>${fmt(h.entry, h.entry > 100 ? 2 : 4)}</span>
        &nbsp; Stop: <span>${fmt(h.stop_loss, h.stop_loss > 100 ? 2 : 4)}</span>
        &nbsp; TP: <span>${fmt(h.take_profit, h.take_profit > 100 ? 2 : 4)}</span>
        &nbsp; Score: <span>${h.score || '—'}</span>
      </div>
      <div class="hist-date">${h.data || h.data_confirmacao || '—'}</div>
    </div>`;
  }).join('');
}

async function carregarSinais() {
  try {
    const r = await fetch('/api/sinais');
    const d = await r.json();
    renderSinais(d);
    document.getElementById('last-update').textContent =
      new Date().toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
  } catch(e) {
    document.getElementById('sinais-container').innerHTML =
      `<div class="empty"><div class="ico">⚠</div>Erro: ${e.message}</div>`;
  }
}

async function carregarHistorico() {
  try {
    const r = await fetch('/historico');
    const d = await r.json();
    renderHistorico(d);
  } catch(e) {
    document.getElementById('historico-container').innerHTML =
      `<div class="empty"><div class="ico">⚠</div>Erro: ${e.message}</div>`;
  }
}

function abrirConfirmacao(s) {
  const res = confirm(
    `📊 CONFIRMAR SINAL\n\n` +
    `${s.emoji} ${s.nome_exibicao} · ${s.timeframe}\n` +
    `Sinal: ${s.sinal}  |  Score: ${s.score}/100\n` +
    `Entry: ${s.preco}  |  Stop: ${s.stop_loss}  |  TP: ${s.take_profit}\n` +
    `RSI: ${s.rsi}  |  MACD: ${s.macd_hist}  |  MTF: ${s.mtf_ok ? 'OK' : 'FALHOU'}\n\n` +
    `OK = WIN (acertou) · Cancelar = LOSS (errou)`
  );
  if (res === null) return;
  fetch('/confirmar', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      simbolo: s.symbol, nome: s.nome, nome_exibicao: s.nome_exibicao,
      emoji: s.emoji, timeframe: s.timeframe, sinal: s.sinal,
      entry: s.preco, stop_loss: s.stop_loss, take_profit: s.take_profit,
      score: s.score, fonte: s.fonte,
      confirmado: res ? 'win' : 'loss',
      data: new Date().toLocaleString('pt-BR')
    })
  }).then(() => { carregarHistorico(); });
}

async function carregarTudo() {
  await Promise.all([carregarSinais(), carregarHistorico()]);
}

carregarTudo();
setInterval(carregarSinais, 300_000);
</script>
</body>
</html>
"""


# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)


@app.get("/api/sinais")
async def get_sinais():
    sinais = []
    for symbol, config in SYMBOL_CONFIG.items():
        analysis = get_analysis(symbol, "15m")
        if not analysis:
            continue
        sinais.append({
            "symbol":       symbol,
            "nome":         config["nome"],
            "nome_exibicao":config["nome_exibicao"],
            "emoji":        config["emoji"],
            "tipo":         config["tipo"],
            "timeframe":    "15m",
            "preco":        analysis["preco"],
            "sinal":        analysis["sinal"],
            "score":        analysis["score"],
            "rsi":          analysis["rsi"],
            "macd_hist":    analysis["macd_hist"],
            "bb_upper":     analysis["bb_upper"],
            "bb_lower":     analysis["bb_lower"],
            "volume_ratio": analysis["volume_ratio"],
            "tendencia":    analysis["tendencia"],
            "tendencia_sup":analysis["tendencia_sup"],
            "mtf_ok":       analysis["mtf_ok"],
            "stop_loss":    analysis["stop_loss"],
            "take_profit":  analysis["take_profit"],
            "entry":        analysis["preco"],
            "fonte":        analysis["fonte"],
            "data":         datetime.now().strftime("%d/%m %H:%M"),
        })
    return sinais


@app.get("/historico")
async def get_historico():
    return carregar_historico()


@app.post("/confirmar")
async def confirmar_sinal(sinal: dict):
    historico = carregar_historico()
    historico.append(sinal)
    salvar_historico(historico)
    return {"ok": True}
