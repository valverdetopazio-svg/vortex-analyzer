from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
import os, json, requests, time, threading

# ============================================================
# INICIALIZAÇÃO DO FASTAPI (DEVE VIR PRIMEIRO)
# ============================================================
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

# ============================================================
# SISTEMA DE EXPIRAÇÃO DE SINAIS (15 minutos)
# ============================================================

# Armazenamento em memória dos sinais ativos com timestamp
sinais_ativos = {}  # {symbol: {"dados": sinal, "timestamp": datetime}}

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_historico(h):
    with open(HISTORICO_FILE, "w") as f:
        json.dump(h, f, indent=2)

def mover_sinal_para_historico(symbol, sinal_data):
    """Move um sinal expirado para o histórico"""
    historico = carregar_historico()
    
    # Adiciona dados de expiração
    sinal_data["data_confirmacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sinal_data["status"] = "expirado"
    sinal_data["motivo"] = "Tempo limite de 15 minutos excedido"
    
    historico.append(sinal_data)
    salvar_historico(historico)
    
    # Remove dos sinais ativos
    if symbol in sinais_ativos:
        del sinais_ativos[symbol]
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sinal expirado: {sinal_data.get('nome_exibicao')} - {sinal_data.get('sinal')}")

def verificar_sinais_expirados():
    """Verifica periodicamente sinais com mais de 15 minutos"""
    while True:
        try:
            agora = datetime.now()
            expirados = []
            
            for symbol, item in sinais_ativos.items():
                tempo_passado = (agora - item["timestamp"]).total_seconds()
                if tempo_passado > 900:  # 15 minutos = 900 segundos
                    expirados.append((symbol, item["dados"]))
            
            # Move sinais expirados para o histórico
            for symbol, sinal in expirados:
                mover_sinal_para_historico(symbol, sinal)
                
            time.sleep(30)  # Verifica a cada 30 segundos
            
        except Exception as e:
            print(f"Erro ao verificar sinais expirados: {e}")
            time.sleep(60)

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
# FUNÇÃO PARA PROCESSAR E ARMAZENAR SINAIS
# ============================================================

def processar_e_armazenar_sinais():
    """Processa todos os ativos e armazena sinais ativos com timestamp"""
    for symbol, cfg in SYMBOL_CONFIG.items():
        analysis = get_analysis(symbol, "15m")
        if not analysis or analysis["sinal"] == "NEUTRO":
            # Remove sinal se ficou neutro
            if symbol in sinais_ativos:
                del sinais_ativos[symbol]
            continue
        
        agora = datetime.now()
        
        sinal_data = {
            "symbol": symbol,
            "nome": cfg["nome"],
            "nome_exibicao": cfg["nome_exibicao"],
            "emoji": cfg["emoji"],
            "tipo": cfg["tipo"],
            "timeframe": "15m",
            "preco": analysis["preco"],
            "sinal": analysis["sinal"],
            "score": analysis["score"],
            "forca": analysis["forca"],
            "confianca": analysis["confianca"],
            "rsi": analysis["rsi"],
            "macd_hist": analysis["macd_hist"],
            "bb_upper": analysis["bb_upper"],
            "bb_lower": analysis["bb_lower"],
            "volume_ratio": analysis["volume_ratio"],
            "tendencia": analysis["tendencia"],
            "tendencia_sup": analysis["tendencia_sup"],
            "mtf_ok": analysis["mtf_ok"],
            "stop_loss": analysis["stop_loss"],
            "take_profit": analysis["take_profit"],
            "entry": analysis["preco"],
            "fonte": analysis["fonte"],
            "data": agora.strftime("%d/%m %H:%M"),
            "data_completa": agora.strftime("%d/%m/%Y %H:%M:%S"),
            "horario_confirmacao": agora.strftime("%H:%M:%S"),
            "timestamp_criacao": agora.isoformat()
        }
        
        # Verifica se já existe um sinal ativo para este símbolo
        if symbol in sinais_ativos:
            sinal_existente = sinais_ativos[symbol]["dados"]
            # Se o sinal mudou (COMPRA -> VENDA ou vice-versa), move o antigo pro histórico
            if sinal_existente["sinal"] != sinal_data["sinal"]:
                mover_sinal_para_historico(symbol, sinal_existente)
                # Adiciona novo sinal
                sinais_ativos[symbol] = {
                    "dados": sinal_data,
                    "timestamp": agora
                }
        else:
            # Novo sinal
            sinais_ativos[symbol] = {
                "dados": sinal_data,
                "timestamp": agora
            }

# Inicia a thread de verificação em background
threading.Thread(target=verificar_sinais_expirados, daemon=True).start()

# ============================================================
# ENDPOINTS DA API
# ============================================================

@app.get("/api/sinais")
async def get_sinais():
    """Retorna apenas sinais ativos (com menos de 15 minutos)"""
    # Processa e atualiza sinais
    processar_e_armazenar_sinais()
    
    # Converte para lista e adiciona tempo restante
    sinais_retorno = []
    for symbol, item in sinais_ativos.items():
        sinal = item["dados"].copy()
        timestamp_criacao = item["timestamp"]
        tempo_passado = (datetime.now() - timestamp_criacao).total_seconds()
        tempo_restante = max(0, 900 - tempo_passado)
        
        # Adiciona informações de expiração
        sinal["tempo_restante"] = int(tempo_restante)
        sinal["tempo_restante_formatado"] = f"{int(tempo_restante // 60)}min {int(tempo_restante % 60)}s"
        sinal["expiracao"] = (timestamp_criacao + timedelta(seconds=900)).strftime("%H:%M:%S")
        
        # Garante que o horário de confirmação está presente
        if "horario_confirmacao" not in sinal:
            sinal["horario_confirmacao"] = timestamp_criacao.strftime("%H:%M:%S")
        if "data_completa" not in sinal:
            sinal["data_completa"] = timestamp_criacao.strftime("%d/%m/%Y %H:%M:%S")
        
        sinais_retorno.append(sinal)
    
    return sinais_retorno

@app.get("/historico")
async def get_historico():
    return carregar_historico()

@app.post("/confirmar")
async def confirmar_sinal(sinal: dict):
    """Confirma um sinal com WIN/LOSS e mantém o horário original"""
    h = carregar_historico()
    
    # Preserva o horário original se existir
    if "horario_confirmacao" not in sinal:
        sinal["horario_confirmacao"] = datetime.now().strftime("%H:%M:%S")
    if "data_completa" not in sinal:
        sinal["data_completa"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    sinal["data_confirmacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    h.append(sinal)
    salvar_historico(h)
    return {"ok": True}

@app.get("/api/sinais/expirados")
async def get_sinais_expirados():
    """Retorna apenas sinais expirados do histórico"""
    historico = carregar_historico()
    expirados = [s for s in historico if s.get("status") == "expirado"]
    return expirados

# ============================================================
# HTML (versão simplificada para não estourar o limite)
# ============================================================

HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Valverde Trade IA</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#060a17;--bg2:#0c1122;--bg3:#101728;--border:rgba(255,255,255,0.06);--bord2:rgba(255,255,255,0.12);--text:#dde4f0;--muted:#4e6080;--accent:#38bdf8;--buy:#22c55e;--sell:#ef4444;--warn:#f59e0b;--sim:#f97316;--mono:'Space Mono',monospace;--sans:'DM Sans',sans-serif;}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--sans);background:var(--bg);color:var(--text);padding:20px}
.wrap{max-width:1380px;margin:0 auto}
.header{display:flex;justify-content:space-between;margin-bottom:20px;padding-bottom:10px;border-bottom:1px solid var(--border)}
.logo{font-family:var(--mono);font-size:1.1rem;color:var(--accent)}
.refresh-btn{background:transparent;border:1px solid var(--bord2);color:var(--text);cursor:pointer;padding:5px 12px;border-radius:6px}
.tabs{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:15px}
.tab{padding:5px 12px;border-radius:20px;cursor:pointer;border:1px solid var(--border);background:transparent;color:var(--muted)}
.tab.active{background:rgba(56,189,248,.12);border-color:var(--accent);color:var(--accent)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.panel{background:var(--bg2);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.panel-head{padding:12px 16px;border-bottom:1px solid var(--border);background:var(--bg3);display:flex;justify-content:space-between}
.panel-body{padding:12px;max-height:80vh;overflow-y:auto}
.sig-card{background:var(--bg3);border:1px solid var(--border);border-radius:11px;padding:12px;margin-bottom:9px;cursor:pointer}
.sig-card.buy{border-left:3px solid var(--buy)}
.sig-card.sell{border-left:3px solid var(--sell)}
.sig-top{display:flex;justify-content:space-between;margin-bottom:10px}
.sig-name{font-weight:600}
.badge{padding:3px 9px;border-radius:5px;font-size:.7rem;font-weight:700}
.badge.buy{background:rgba(34,197,94,.14);color:var(--buy)}
.badge.sell{background:rgba(239,68,68,.14);color:var(--sell)}
.sig-time{margin-top:8px;padding-top:6px;border-top:1px solid var(--border);font-size:.6rem;color:var(--muted)}
.sig-expiry{font-size:.6rem;color:var(--warn);margin-top:4px}
.hist-item{background:var(--bg3);border:1px solid var(--border);border-radius:9px;padding:10px;margin-bottom:7px}
.hist-time{font-size:.55rem;color:var(--muted);margin-top:4px}
</style>
</head>
<body>
<div class="wrap">
<div class="header">
<span class="logo">VALVERDE TRADE IA v3.0</span>
<button class="refresh-btn" onclick="carregarTudo()">↻ ATUALIZAR</button>
</div>
<div class="tabs">
<button class="tab active" onclick="setTab('Todos')">Todos</button>
<button class="tab" onclick="setTab('Forex')">Forex</button>
<button class="tab" onclick="setTab('Commodities')">Commodities</button>
<button class="tab" onclick="setTab('Cripto')">Cripto</button>
<button class="tab" onclick="setTab('Índices')">Índices</button>
<button class="tab" onclick="setTab('Ações')">Ações</button>
</div>
<div class="grid">
<div class="panel"><div class="panel-head"><span>Sinais Ativos</span><span id="count-sinais">—</span></div><div class="panel-body" id="sinais-container">Carregando...</div></div>
<div class="panel"><div class="panel-head"><span>Histórico</span><span id="count-hist">—</span></div><div class="panel-body" id="historico-container">Carregando...</div></div>
</div>
</div>
<script>
let todosSinais=[],catAtual='Todos';
function fmtPreco(v,t){if(v==null)return'—';let n=Number(v);if(t==='Forex')return n.toFixed(5);if(n>10000)return n.toLocaleString();return n.toFixed(2)}
function renderSinais(){let lista=catAtual==='Todos'?todosSinais:todosSinais.filter(s=>s.tipo===catAtual);document.getElementById('count-sinais').innerHTML=lista.length;let html=lista.map(s=>`<div class="sig-card ${s.sinal==='COMPRA'?'buy':'sell'}" onclick='confirmar(${JSON.stringify(s)})'><div class="sig-top"><div><b>${s.emoji} ${s.nome_exibicao}</b><br><small>${s.tipo}</small></div><span class="badge ${s.sinal==='COMPRA'?'buy':'sell'}">${s.sinal==='COMPRA'?'▲ COMPRA':'▼ VENDA'}</span></div><div>Entry: ${fmtPreco(s.preco,s.tipo)} | Stop: ${fmtPreco(s.stop_loss,s.tipo)} | TP: ${fmtPreco(s.take_profit,s.tipo)}</div><div>Score: ${s.score} | Conf: ${s.confianca}%</div><div class="sig-time">🕐 Confirmado: ${s.horario_confirmacao}</div><div class="sig-expiry">⏱ Expira em: ${s.tempo_restante_formatado}</div></div>`).join('');document.getElementById('sinais-container').innerHTML=html||'<div>Sem sinais</div>';}
function renderHistorico(hist){let html=hist.slice().reverse().map(h=>`<div class="hist-item"><div><b>${h.emoji} ${h.nome_exibicao}</b> - ${h.sinal}</div><div>Entry: ${fmtPreco(h.entry,h.tipo)} | SL: ${fmtPreco(h.stop_loss,h.tipo)} | TP: ${fmtPreco(h.take_profit,h.tipo)}</div><div class="hist-time">🕐 Confirmado: ${h.horario_confirmacao} | ${h.status==='expirado'?'⚠ Expirado':h.confirmado==='win'?'✓ WIN':'◌ Pend'}</div></div>`).join('');document.getElementById('historico-container').innerHTML=html||'<div>Sem histórico</div>';document.getElementById('count-hist').innerHTML=hist.length;}
async function carregarSinais(){let r=await fetch('/api/sinais');todosSinais=await r.json();renderSinais();}
async function carregarHistorico(){let r=await fetch('/historico');renderHistorico(await r.json());}
async function confirmar(s){let res=confirm(`Confirmar ${s.nome_exibicao} - ${s.sinal}?\nOK = WIN | Cancelar = LOSS`);if(res!==null){await fetch('/confirmar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...s,confirmado:res?'win':'loss',data_confirmacao:new Date().toLocaleString()})});carregarHistorico();}}
function setTab(cat){catAtual=cat;document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));event.target.classList.add('active');renderSinais();}
async function carregarTudo(){await Promise.all([carregarSinais(),carregarHistorico()]);}
carregarTudo();setInterval(carregarSinais,300000);
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)

# ============================================================
# MAIN (para execução local)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
