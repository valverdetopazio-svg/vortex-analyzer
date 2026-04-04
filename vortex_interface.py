from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
import os, json, requests, time, threading

app = FastAPI(title="Valverde Trade IA")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ============================================================
# CONFIGURAÇÃO
# ============================================================
SYMBOL_CONFIG = {
    "EURUSD=X": {"nome":"EUR/USD","nome_exibicao":"Euro/Dólar","tipo":"Forex","emoji":"💶","base_fallback":1.085},
    "USDJPY=X": {"nome":"USD/JPY","nome_exibicao":"Dólar/Iene","tipo":"Forex","emoji":"💴","base_fallback":149.5},
    "GBPUSD=X": {"nome":"GBP/USD","nome_exibicao":"Libra/Dólar","tipo":"Forex","emoji":"💷","base_fallback":1.265},
    "USDCHF=X": {"nome":"USD/CHF","nome_exibicao":"Dólar/Franco","tipo":"Forex","emoji":"🇨🇭","base_fallback":0.895},
    "AUDUSD=X": {"nome":"AUD/USD","nome_exibicao":"Dólar Australiano","tipo":"Forex","emoji":"🦘","base_fallback":0.655},
    "USDCAD=X": {"nome":"USD/CAD","nome_exibicao":"Dólar/CAD","tipo":"Forex","emoji":"🍁","base_fallback":1.365},
    "NZDUSD=X": {"nome":"NZD/USD","nome_exibicao":"Dólar NZ","tipo":"Forex","emoji":"🥝","base_fallback":0.605},
    "GC=F": {"nome":"XAUUSD","nome_exibicao":"Ouro","tipo":"Commodities","emoji":"🥇","base_fallback":2350},
    "SI=F": {"nome":"XAGUSD","nome_exibicao":"Prata","tipo":"Commodities","emoji":"🥈","base_fallback":28.5},
    "PL=F": {"nome":"XPTUSD","nome_exibicao":"Platina","tipo":"Commodities","emoji":"⚗️","base_fallback":960},
    "CL=F": {"nome":"WTI","nome_exibicao":"Petróleo","tipo":"Commodities","emoji":"🛢️","base_fallback":78},
    "BZ=F": {"nome":"BRENT","nome_exibicao":"Brent","tipo":"Commodities","emoji":"⛽","base_fallback":82},
    "NG=F": {"nome":"NATGAS","nome_exibicao":"Gás Natural","tipo":"Commodities","emoji":"🔥","base_fallback":2.8},
    "BTC-USD": {"nome":"BTC","nome_exibicao":"Bitcoin","tipo":"Cripto","emoji":"₿","base_fallback":66800},
    "ETH-USD": {"nome":"ETH","nome_exibicao":"Ethereum","tipo":"Cripto","emoji":"⟠","base_fallback":3300},
    "^GDAXI": {"nome":"DAX","nome_exibicao":"DAX","tipo":"Índices","emoji":"🇩🇪","base_fallback":18200},
    "^FTSE": {"nome":"FTSE","nome_exibicao":"FTSE 100","tipo":"Índices","emoji":"🇬🇧","base_fallback":8200},
    "^N225": {"nome":"NIKKEI","nome_exibicao":"Nikkei","tipo":"Índices","emoji":"🇯🇵","base_fallback":38500},
    "^GSPC": {"nome":"SP500","nome_exibicao":"S&P 500","tipo":"Índices","emoji":"🇺🇸","base_fallback":5200},
    "^IXIC": {"nome":"NASDAQ","nome_exibicao":"NASDAQ","tipo":"Índices","emoji":"💻","base_fallback":16400},
    "^DJI": {"nome":"DOW30","nome_exibicao":"Dow Jones","tipo":"Índices","emoji":"📈","base_fallback":39000},
    "AAPL": {"nome":"AAPL","nome_exibicao":"Apple","tipo":"Ações","emoji":"🍎","base_fallback":220},
    "NVDA": {"nome":"NVDA","nome_exibicao":"NVIDIA","tipo":"Ações","emoji":"🎮","base_fallback":120},
}

ATR_MULTIPLIER = {"Forex":{"stop":1.5,"tp":2.5},"Cripto":{"stop":2.5,"tp":4},"Commodities":{"stop":2,"tp":3.5},"Índices":{"stop":1.8,"tp":3},"Ações":{"stop":1.5,"tp":2.5}}
SCORE_MINIMO = 65
HISTORICO_FILE = "historico_sinais.json"

# ============================================================
# TIMEFRAME AUTOMÁTICO POR TIPO DE ATIVO
# ============================================================
def get_timeframe_by_type(tipo):
    """Retorna o melhor timeframe baseado no tipo do ativo"""
    timeframes = {
        "Forex": "15m",      # Forex: 15 minutos (day trade)
        "Cripto": "1h",      # Cripto: 1 hora (volatilidade alta)
        "Commodities": "1h", # Commodities: 1 hora
        "Índices": "1h",     # Índices: 1 hora
        "Ações": "1d"        # Ações: 1 dia (swing trade)
    }
    return timeframes.get(tipo, "1h")

def get_expiracao_by_tipo(tipo):
    """Tempo de expiração do sinal baseado no tipo"""
    expiracao = {
        "Forex": 900,        # 15 minutos
        "Cripto": 3600,      # 1 hora
        "Commodities": 3600, # 1 hora
        "Índices": 3600,     # 1 hora
        "Ações": 86400       # 24 horas
    }
    return expiracao.get(tipo, 3600)

# ============================================================
# ARMAZENAMENTO
# ============================================================
sinais_ativos = {}  # {symbol: {"dados": sinal, "timestamp": datetime}}

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
def calcular_ema(closes, p):
    if len(closes) < p: return closes[-1]
    k = 2/(p+1)
    ema = sum(closes[:p])/p
    for val in closes[p:]: ema = val*k + ema*(1-k)
    return ema

def calcular_rsi(closes, p=14):
    if len(closes) < p+1: return 50
    g = p = 0
    for i in range(-p,0):
        d = closes[i] - closes[i-1]
        if d > 0: g += d
        else: p += abs(d)
    return 100 - (100/(1+g/p)) if p > 0 else 100

def calcular_macd(closes):
    if len(closes) < 35: return 0,0,0
    ema12 = calcular_ema(closes,12)
    ema26 = calcular_ema(closes,26)
    return ema12, ema26, ema12 - ema26

def calcular_bollinger(closes):
    if len(closes) < 20: return closes[-1], closes[-1], closes[-1]
    r = closes[-20:]
    ma = sum(r)/20
    std = (sum((c-ma)**2 for c in r)/20)**0.5
    return ma+2*std, ma, ma-2*std

def calcular_atr(closes):
    if len(closes) < 2: return closes[-1]*0.005
    v = [abs(closes[i]-closes[i-1]) for i in range(-14,0)]
    return sum(v)/len(v) if v else closes[-1]*0.005

def calcular_volume_ratio(volumes):
    if len(volumes) < 21: return 1
    media = sum(volumes[-21:-1])/20
    return volumes[-1]/media if media else 1

# ============================================================
# FONTES DE DADOS
# ============================================================
def fetch_dados(symbol, interval):
    """Busca dados do Yahoo Finance"""
    try:
        yi = "1h" if interval=="4h" else interval
        rng = {"5m":"5d","15m":"5d","1h":"30d","4h":"60d","1d":"6mo"}.get(interval,"5d")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={yi}&range={rng}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            res = r.json().get("chart",{}).get("result",[{}])[0]
            q = res.get("indicators",{}).get("quote",[{}])[0]
            closes = [c for c in q.get("close",[]) if c]
            volumes = [v for v in q.get("volume",[]) if v]
            if closes:
                return {"closes":closes, "volumes":volumes or [1000000]*len(closes), "fonte":"yahoo"}
    except: pass
    
    # Fallback simulado
    import random
    base = SYMBOL_CONFIG.get(symbol,{}).get("base_fallback",100)
    random.seed(int(time.time()/300) + hash(symbol+interval)%9999)
    return {"closes":[base*(1+random.uniform(-0.02,0.02)) for _ in range(100)], 
            "volumes":[random.uniform(500000,2000000) for _ in range(100)], 
            "fonte":"simulado"}

# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================
def analisar(symbol):
    """Analisa um ativo com o timeframe automático baseado no tipo"""
    cfg = SYMBOL_CONFIG[symbol]
    tipo = cfg["tipo"]
    intervalo = get_timeframe_by_type(tipo)
    
    dados = fetch_dados(symbol, intervalo)
    closes, volumes, fonte = dados["closes"], dados["volumes"], dados["fonte"]
    if len(closes) < 35: return None
    
    p = closes[-1]
    rsi = calcular_rsi(closes)
    _, _, macd_hist = calcular_macd(closes)
    bbu, _, bbl = calcular_bollinger(closes)
    atr = calcular_atr(closes)
    vr = round(calcular_volume_ratio(volumes),2)
    ema9, ema21, ema50 = calcular_ema(closes,9), calcular_ema(closes,21), calcular_ema(closes,50)
    
    tendencia = "ALTA" if ema9 > ema21 > ema50 else "BAIXA" if ema9 < ema21 < ema50 else "LATERAL"
    
    # Regras de sinal
    if rsi < 35 and macd_hist > 0 and tendencia != "BAIXA": sinal_bruto = "COMPRA"
    elif rsi > 65 and macd_hist < 0 and tendencia != "ALTA": sinal_bruto = "VENDA"
    elif rsi < 30: sinal_bruto = "COMPRA"
    elif rsi > 70: sinal_bruto = "VENDA"
    else: sinal_bruto = "NEUTRO"
    
    # Cálculo do Score
    score = 0
    if sinal_bruto == "COMPRA":
        score += 30 if rsi < 30 else 22 if rsi < 40 else 12 if rsi < 50 else 0
    else:
        score += 30 if rsi > 70 else 22 if rsi > 60 else 12 if rsi > 50 else 0
    
    score += 25 if (sinal_bruto=="COMPRA" and macd_hist>0) or (sinal_bruto=="VENDA" and macd_hist<0) else 0
    score += 10 if abs(macd_hist) < p*0.0005 else 0
    
    bw = bbu - bbl
    if bw > 0:
        pos = (p - bbl)/bw
        if sinal_bruto == "COMPRA":
            score += 25 if pos <= 0.1 else 15 if pos <= 0.3 else 8 if pos <= 0.5 else 0
        else:
            score += 25 if pos >= 0.9 else 15 if pos >= 0.7 else 8 if pos >= 0.5 else 0
    
    score += 10 if vr >= 1.5 else 7 if vr >= 1.2 else 4 if vr >= 1 else 0
    
    sinal_final = sinal_bruto if score >= SCORE_MINIMO else "NEUTRO"
    confianca = round(50 + score/2, 1) if sinal_final != "NEUTRO" else round(score*0.6, 1)
    
    # Força do sinal
    if sinal_final == "COMPRA":
        forca = round(max(0, (50 - rsi) / 50 * 100) * 0.6 + (100 if macd_hist > 0 else 30) * 0.4, 1)
    elif sinal_final == "VENDA":
        forca = round(max(0, (rsi - 50) / 50 * 100) * 0.6 + (100 if macd_hist < 0 else 30) * 0.4, 1)
    else:
        forca = 50
    
    # Stop Loss e Take Profit
    mult = ATR_MULTIPLIER.get(tipo, {"stop":1.5, "tp":2.5})
    sl = round(p - mult["stop"] * atr, 6) if sinal_final == "COMPRA" else round(p + mult["stop"] * atr, 6)
    tp = round(p + mult["tp"] * atr, 6) if sinal_final == "COMPRA" else round(p - mult["tp"] * atr, 6)
    
    return {
        "preco": p, "rsi": rsi, "macd_hist": macd_hist,
        "volume_ratio": vr, "tendencia": tendencia,
        "sinal": sinal_final, "score": score, "confianca": confianca,
        "forca": forca, "stop_loss": sl, "take_profit": tp,
        "fonte": fonte, "timeframe_used": intervalo
    }

# ============================================================
# PROCESSAMENTO
# ============================================================
def processar_todos():
    """Processa todos os ativos com timeframe automático"""
    for symbol, cfg in SYMBOL_CONFIG.items():
        analise = analisar(symbol)
        if not analise or analise["sinal"] == "NEUTRO":
            if symbol in sinais_ativos:
                del sinais_ativos[symbol]
            continue
        
        agora = datetime.now()
        sinal = {
            "symbol": symbol,
            "nome": cfg["nome"],
            "nome_exibicao": cfg["nome_exibicao"],
            "emoji": cfg["emoji"],
            "tipo": cfg["tipo"],
            "timeframe": analise["timeframe_used"],
            "preco": analise["preco"],
            "sinal": analise["sinal"],
            "score": analise["score"],
            "forca": analise["forca"],
            "confianca": analise["confianca"],
            "rsi": analise["rsi"],
            "macd_hist": analise["macd_hist"],
            "volume_ratio": analise["volume_ratio"],
            "tendencia": analise["tendencia"],
            "stop_loss": analise["stop_loss"],
            "take_profit": analise["take_profit"],
            "entry": analise["preco"],
            "fonte": analise["fonte"],
            "horario": agora.strftime("%H:%M:%S"),
            "timestamp": agora
        }
        
        if symbol in sinais_ativos:
            if sinais_ativos[symbol]["dados"]["sinal"] != sinal["sinal"]:
                historico = carregar_historico()
                sinal_antigo = sinais_ativos[symbol]["dados"]
                sinal_antigo["data_fim"] = agora.strftime("%d/%m/%Y %H:%M:%S")
                sinal_antigo["status"] = "substituido"
                historico.append(sinal_antigo)
                salvar_historico(historico)
                sinais_ativos[symbol] = {"dados": sinal, "timestamp": agora}
        else:
            sinais_ativos[symbol] = {"dados": sinal, "timestamp": agora}

def verificar_expiracao():
    """Verifica sinais expirados baseado no tipo do ativo"""
    while True:
        agora = datetime.now()
        for symbol, item in list(sinais_ativos.items()):
            tipo = SYMBOL_CONFIG[symbol]["tipo"]
            expira_em = get_expiracao_by_tipo(tipo)
            
            if (agora - item["timestamp"]).total_seconds() > expira_em:
                historico = carregar_historico()
                sinal = item["dados"]
                sinal["data_expiracao"] = agora.strftime("%d/%m/%Y %H:%M:%S")
                sinal["status"] = "expirado"
                historico.append(sinal)
                salvar_historico(historico)
                del sinais_ativos[symbol]
        time.sleep(30)

# Iniciar threads
threading.Thread(target=verificar_expiracao, daemon=True).start()
threading.Thread(target=lambda: [time.sleep(1), processar_todos()], daemon=True).start()

# ============================================================
# ENDPOINTS
# ============================================================
@app.get("/api/sinais")
async def get_sinais():
    """Retorna todos os sinais ativos"""
    processar_todos()
    resultado = []
    for item in sinais_ativos.values():
        s = item["dados"].copy()
        tipo = SYMBOL_CONFIG[s["symbol"]]["tipo"]
        tempo = (datetime.now() - item["timestamp"]).total_seconds()
        restante = max(0, get_expiracao_by_tipo(tipo) - tempo)
        s["expira_em"] = f"{int(restante//60)}min {int(restante%60)}s"
        resultado.append(s)
    return resultado

@app.get("/api/analise/{symbol}")
async def get_analise_unica(symbol: str):
    """Retorna análise de um ativo específico"""
    if symbol not in SYMBOL_CONFIG:
        return {"erro": "Símbolo não encontrado"}
    return analisar(symbol)

@app.get("/historico")
async def get_historico():
    return carregar_historico()

@app.post("/confirmar")
async def confirmar(sinal: dict):
    h = carregar_historico()
    sinal["confirmado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    h.append(sinal)
    salvar_historico(h)
    return {"ok": True}

# ============================================================
# HTML SIMPLES
# ============================================================
HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Valverde Trade IA</title>
<style>
body{font-family:monospace;background:#0a0e1a;color:#e5e7eb;padding:20px}
.card{background:#111827;border-radius:8px;padding:15px;margin-bottom:10px;border-left:3px solid}
.buy{border-left-color:#10b981}
.sell{border-left-color:#ef4444}
.header{display:flex;justify-content:space-between;margin-bottom:20px}
button{background:#1f2937;color:white;border:none;padding:5px 10px;cursor:pointer}
</style>
</head>
<body>
<div class="header"><h1>VALVERDE TRADE IA</h1><button onclick="location.reload()">⟳ ATUALIZAR</button></div>
<div id="sinais"></div>
<script>
async function carregar(){
    const r=await fetch('/api/sinais');
    const dados=await r.json();
    const html=dados.map(s=>`
        <div class="card ${s.sinal==='COMPRA'?'buy':'sell'}">
            <div><b>${s.emoji} ${s.nome_exibicao}</b> (${s.nome}) - ${s.timeframe}</div>
            <div>Sinal: <b>${s.sinal}</b> | Score: ${s.score} | Conf: ${s.confianca}%</div>
            <div>Entry: ${s.entry} | Stop: ${s.stop_loss} | TP: ${s.take_profit}</div>
            <div>RSI: ${s.rsi} | Tendência: ${s.tendencia} | Expira: ${s.expira_em}</div>
            <small>🕐 ${s.horario} | 📡 ${s.fonte}</small>
        </div>
    `).join('');
    document.getElementById('sinais').innerHTML=html||'<div>Sem sinais ativos</div>';
}
carregar();
setInterval(carregar,60000);
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(content=HTML)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
