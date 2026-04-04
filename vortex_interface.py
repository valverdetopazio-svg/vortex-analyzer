from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime, timedelta
import os, json, requests, time, threading
from tradingview_ta import TA_Handler, Interval

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
    "CL=F": {"nome":"WTI","nome_exibicao":"Petróleo","tipo":"Commodities","emoji":"🛢️","base_fallback":78},
    "BTC-USD": {"nome":"BTC","nome_exibicao":"Bitcoin","tipo":"Cripto","emoji":"₿","base_fallback":66800},
    "ETH-USD": {"nome":"ETH","nome_exibicao":"Ethereum","tipo":"Cripto","emoji":"⟠","base_fallback":3300},
    "^GSPC": {"nome":"SP500","nome_exibicao":"S&P 500","tipo":"Índices","emoji":"🇺🇸","base_fallback":5200},
    "^IXIC": {"nome":"NASDAQ","nome_exibicao":"NASDAQ","tipo":"Índices","emoji":"💻","base_fallback":16400},
    "AAPL": {"nome":"AAPL","nome_exibicao":"Apple","tipo":"Ações","emoji":"🍎","base_fallback":220},
    "NVDA": {"nome":"NVDA","nome_exibicao":"NVIDIA","tipo":"Ações","emoji":"🎮","base_fallback":120},
}

TIMEFRAMES = {
    "5m": {"nome":"5min","expira":300,"atualiza":60},
    "15m": {"nome":"15min","expira":900,"atualiza":120},
    "1h": {"nome":"1hora","expira":3600,"atualiza":300},
    "4h": {"nome":"4horas","expira":14400,"atualiza":900},
    "1d": {"nome":"1dia","expira":86400,"atualiza":3600},
}

ATR_MULTIPLIER = {"Forex":{"stop":1.5,"tp":2.5},"Cripto":{"stop":2.5,"tp":4},"Commodities":{"stop":2,"tp":3.5},"Índices":{"stop":1.8,"tp":3},"Ações":{"stop":1.5,"tp":2.5}}
SCORE_MINIMO = 65
HISTORICO_FILE = "historico_sinais.json"

# Armazenamento: sinais_ativos[timeframe][symbol] = {"dados":{}, "timestamp":datetime}
sinais_ativos = {tf: {} for tf in TIMEFRAMES}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_historico(h):
    with open(HISTORICO_FILE, "w") as f:
        json.dump(h, f, indent=2)

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

def fetch_dados(symbol, interval):
    """Busca dados Yahoo Finance"""
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

def analisar(symbol, interval):
    dados = fetch_dados(symbol, interval)
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
    
    if rsi < 35 and macd_hist > 0 and tendencia != "BAIXA": sinal_bruto = "COMPRA"
    elif rsi > 65 and macd_hist < 0 and tendencia != "ALTA": sinal_bruto = "VENDA"
    elif rsi < 30: sinal_bruto = "COMPRA"
    elif rsi > 70: sinal_bruto = "VENDA"
    else: sinal_bruto = "NEUTRO"
    
    # Score
    score = 0
    if sinal_bruto == "COMPRA":
        score += 30 if rsi < 30 else 22 if rsi < 40 else 12 if rsi < 50 else 0
    else:
        score += 30 if rsi > 70 else 22 if rsi > 60 else 12 if rsi > 50 else 0
    score += 25 if (sinal_bruto=="COMPRA" and macd_hist>0) or (sinal_bruto=="VENDA" and macd_hist<0) else 10 if abs(macd_hist)<p*0.0005 else 0
    bw = bbu - bbl
    if bw > 0:
        pos = (p - bbl)/bw
        if sinal_bruto == "COMPRA":
            score += 25 if pos <= 0.1 else 15 if pos <= 0.3 else 8 if pos <= 0.5 else 0
        else:
            score += 25 if pos >= 0.9 else 15 if pos >= 0.7 else 8 if pos >= 0.5 else 0
    score += 10 if vr >= 1.5 else 7 if vr >= 1.2 else 4 if vr >= 1 else 0
    
    sinal_final = sinal_bruto if score >= SCORE_MINIMO else "NEUTRO"
    confianca = round(50 + score/2,1) if sinal_final != "NEUTRO" else round(score*0.6,1)
    forca = round((max(0,(50-rsi)/50*100) if sinal_final=="COMPRA" else max(0,(rsi-50)/50*100))*0.6 + (100 if (sinal_final=="COMPRA" and macd_hist>0) or (sinal_final=="VENDA" and macd_hist<0) else 30)*0.4,1)
    
    mult = ATR_MULTIPLIER.get(SYMBOL_CONFIG[symbol]["tipo"], {"stop":1.5,"tp":2.5})
    sl = round(p - mult["stop"]*atr,6) if sinal_final=="COMPRA" else round(p + mult["stop"]*atr,6)
    tp = round(p + mult["tp"]*atr,6) if sinal_final=="COMPRA" else round(p - mult["tp"]*atr,6)
    
    return {"preco":p, "rsi":rsi, "macd_hist":macd_hist, "volume_ratio":vr, "tendencia":tendencia,
            "sinal":sinal_final, "score":score, "confianca":confianca, "forca":forca, 
            "stop_loss":sl, "take_profit":tp, "fonte":fonte}

def processar_todos():
    for tf in TIMEFRAMES:
        for symbol, cfg in SYMBOL_CONFIG.items():
            analise = analisar(symbol, tf)
            if not analise or analise["sinal"] == "NEUTRO":
                if symbol in sinais_ativos[tf]:
                    del sinais_ativos[tf][symbol]
                continue
            
            agora = datetime.now()
            sinal = {
                "symbol": symbol, "nome": cfg["nome"], "nome_exibicao": cfg["nome_exibicao"],
                "emoji": cfg["emoji"], "tipo": cfg["tipo"], "timeframe": tf,
                "timeframe_nome": TIMEFRAMES[tf]["nome"], "preco": analise["preco"],
                "sinal": analise["sinal"], "score": analise["score"], "forca": analise["forca"],
                "confianca": analise["confianca"], "rsi": analise["rsi"],
                "macd_hist": analise["macd_hist"], "volume_ratio": analise["volume_ratio"],
                "tendencia": analise["tendencia"], "stop_loss": analise["stop_loss"],
                "take_profit": analise["take_profit"], "entry": analise["preco"],
                "fonte": analise["fonte"], "horario": agora.strftime("%H:%M:%S"),
                "timestamp": agora
            }
            
            if symbol in sinais_ativos[tf]:
                if sinais_ativos[tf][symbol]["dados"]["sinal"] != sinal["sinal"]:
                    historico = carregar_historico()
                    sinal_antigo = sinais_ativos[tf][symbol]["dados"]
                    sinal_antigo["data_fim"] = agora.strftime("%d/%m/%Y %H:%M:%S")
                    sinal_antigo["status"] = "substituido"
                    historico.append(sinal_antigo)
                    salvar_historico(historico)
                    sinais_ativos[tf][symbol] = {"dados": sinal, "timestamp": agora}
            else:
                sinais_ativos[tf][symbol] = {"dados": sinal, "timestamp": agora}

def verificar_expiracao():
    while True:
        agora = datetime.now()
        for tf, config in TIMEFRAMES.items():
            expira_em = config["expira"]
            for symbol, item in list(sinais_ativos[tf].items()):
                if (agora - item["timestamp"]).total_seconds() > expira_em:
                    historico = carregar_historico()
                    sinal = item["dados"]
                    sinal["data_expiracao"] = agora.strftime("%d/%m/%Y %H:%M:%S")
                    sinal["status"] = "expirado"
                    historico.append(sinal)
                    salvar_historico(historico)
                    del sinais_ativos[tf][symbol]
        time.sleep(30)

threading.Thread(target=verificar_expiracao, daemon=True).start()
threading.Thread(target=lambda: [time.sleep(1), processar_todos()], daemon=True).start()

# ============================================================
# ENDPOINTS
# ============================================================
@app.get("/api/sinais/{timeframe}")
async def get_sinais(timeframe: str):
    if timeframe not in TIMEFRAMES:
        return {"erro": "Timeframe inválido. Use: 5m, 15m, 1h, 4h, 1d"}
    
    processar_todos()
    resultado = []
    for item in sinais_ativos[timeframe].values():
        s = item["dados"].copy()
        tempo = (datetime.now() - item["timestamp"]).total_seconds()
        restante = max(0, TIMEFRAMES[timeframe]["expira"] - tempo)
        s["expira_em"] = f"{int(restante//60)}min {int(restante%60)}s"
        resultado.append(s)
    return resultado

@app.get("/api/sinais")
async def get_sinais_padrao():
    return await get_sinais("15m")

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
# HTML
# ============================================================
HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Valverde Trade IA - Múltiplos Timeframes</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0e1a;--card:#111827;--border:#1f2937;--text:#e5e7eb;--muted:#6b7280;--buy:#10b981;--sell:#ef4444;--accent:#3b82f6}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Space Mono',monospace;background:var(--bg);color:var(--text);padding:20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:10px}
h1{font-size:1.2rem;color:var(--accent)}
.tf-buttons{display:flex;gap:8px;flex-wrap:wrap}
.tf-btn{padding:6px 12px;background:var(--card);border:1px solid var(--border);color:var(--muted);border-radius:6px;cursor:pointer;font-family:monospace;font-size:0.8rem}
.tf-btn.active{background:var(--accent);color:white;border-color:var(--accent)}
.refresh-btn{padding:6px 12px;background:var(--card);border:1px solid var(--border);color:var(--text);border-radius:6px;cursor:pointer}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:15px}
@media(max-width:768px){.grid{grid-template-columns:1fr}}
.panel{background:var(--card);border-radius:12px;border:1px solid var(--border);overflow:hidden}
.panel-header{padding:12px 15px;background:rgba(0,0,0,0.2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between}
.panel-body{padding:12px;max-height:70vh;overflow-y:auto}
.sinal-card{background:rgba(0,0,0,0.2);border-radius:8px;padding:12px;margin-bottom:10px;cursor:pointer;border-left:3px solid var(--muted)}
.sinal-card.buy{border-left-color:var(--buy)}
.sinal-card.sell{border-left-color:var(--sell)}
.card-header{display:flex;justify-content:space-between;margin-bottom:8px}
.asset{font-weight:bold;font-size:0.9rem}
.asset-code{font-size:0.7rem;color:var(--muted)}
.badge{padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:bold}
.badge.buy{background:rgba(16,185,129,0.2);color:var(--buy)}
.badge.sell{background:rgba(239,68,68,0.2);color:var(--sell)}
.precos{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0;font-size:0.7rem}
.metrics{display:flex;gap:10px;margin:8px 0;font-size:0.65rem;color:var(--muted)}
.time{font-size:0.6rem;color:var(--muted);margin-top:6px;padding-top:6px;border-top:1px solid var(--border)}
.hist-item{background:rgba(0,0,0,0.2);border-radius:6px;padding:8px;margin-bottom:6px;font-size:0.7rem}
.empty{text-align:center;padding:40px;color:var(--muted)}
</style>
</head>
<body>
<div class="header">
<h1>🔮 VALVERDE TRADE IA - MULTI TIMEFRAME</h1>
<div style="display:flex;gap:10px">
<div class="tf-buttons" id="tf-buttons"></div>
<button class="refresh-btn" onclick="carregarTudo()">⟳ ATUALIZAR</button>
</div>
</div>
<div class="grid">
<div class="panel"><div class="panel-header"><span>📊 SINAIS ATIVOS</span><span id="count-sinais">-</span></div><div class="panel-body" id="sinais-container">Carregando...</div></div>
<div class="panel"><div class="panel-header"><span>📜 HISTÓRICO</span><span id="count-hist">-</span></div><div class="panel-body" id="historico-container">Carregando...</div></div>
</div>
<script>
let timeframeAtual = '15m';
const timeframes = {'5m':'5min','15m':'15min','1h':'1hora','4h':'4horas','1d':'1dia'};

function criarBotoes() {
    const container = document.getElementById('tf-buttons');
    container.innerHTML = Object.keys(timeframes).map(tf => 
        `<button class="tf-btn ${tf===timeframeAtual?'active':''}" onclick="mudarTimeframe('${tf}')">${timeframes[tf]}</button>`
    ).join('');
}

function fmtPreco(v,tipo) {
    if(!v) return '—';
    let n = Number(v);
    if(tipo==='Forex') return n.toFixed(5);
    if(n>10000) return n.toLocaleString();
    return n.toFixed(2);
}

function renderSinais(sinais) {
    document.getElementById('count-sinais').innerText = sinais.length;
    if(!sinais.length) {
        document.getElementById('sinais-container').innerHTML = '<div class="empty">📡 Nenhum sinal ativo</div>';
        return;
    }
    document.getElementById('sinais-container').innerHTML = sinais.map(s => `
        <div class="sinal-card ${s.sinal==='COMPRA'?'buy':'sell'}" onclick="confirmarSinal(${JSON.stringify(s)})">
            <div class="card-header">
                <div><span class="asset">${s.emoji} ${s.nome}</span><br><span class="asset-code">${s.nome_exibicao}</span></div>
                <span class="badge ${s.sinal==='COMPRA'?'buy':'sell'}">${s.sinal==='COMPRA'?'▲ COMPRA':'▼ VENDA'}</span>
            </div>
            <div class="precos">
                <div>📈 Entry<br><strong>${fmtPreco(s.entry,s.tipo)}</strong></div>
                <div>🛑 Stop<br><strong style="color:var(--sell)">${fmtPreco(s.stop_loss,s.tipo)}</strong></div>
                <div>🎯 TP<br><strong style="color:var(--buy)">${fmtPreco(s.take_profit,s.tipo)}</strong></div>
            </div>
            <div class="metrics">
                <span>🎯 Score: ${s.score}</span>
                <span>💪 Força: ${s.forca}%</span>
                <span>📊 RSI: ${s.rsi}</span>
            </div>
            <div class="time">
                🕐 ${s.horario} | ⏱ Expira: ${s.expira_em} | 📡 ${s.fonte}
            </div>
        </div>
    `).join('');
}

function renderHistorico(hist) {
    document.getElementById('count-hist').innerText = hist.length;
    if(!hist.length) {
        document.getElementById('historico-container').innerHTML = '<div class="empty">📋 Nenhum registro</div>';
        return;
    }
    document.getElementById('historico-container').innerHTML = hist.slice().reverse().map(h => `
        <div class="hist-item">
            <strong>${h.emoji} ${h.nome}</strong> (${h.timeframe_nome}) - ${h.sinal}<br>
            Entry: ${fmtPreco(h.entry,h.tipo)} | SL: ${fmtPreco(h.stop_loss,h.tipo)} | TP: ${fmtPreco(h.take_profit,h.tipo)}<br>
            Score: ${h.score} | Status: ${h.status || 'pendente'}<br>
            <small>🕐 ${h.horario || h.data_fim || h.confirmado_em || '-'}</small>
        </div>
    `).join('');
}

async function mudarTimeframe(tf) {
    timeframeAtual = tf;
    criarBotoes();
    await carregarSinais();
}

async function carregarSinais() {
    try {
        const r = await fetch(`/api/sinais/${timeframeAtual}`);
        const data = await r.json();
        renderSinais(data);
    } catch(e) { console.error(e); }
}

async function carregarHistorico() {
    try {
        const r = await fetch('/historico');
        const data = await r.json();
        renderHistorico(data);
    } catch(e) { console.error(e); }
}

async function confirmarSinal(s) {
    const res = confirm(`Confirmar ${s.nome} (${s.timeframe_nome}) - ${s.sinal}?\nOK = WIN | Cancelar = LOSS`);
    if(res !== null) {
        await fetch('/confirmar', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({...s, confirmado: res?'win':'loss', status: res?'ganho':'perdido'})
        });
        carregarHistorico();
    }
}

async function carregarTudo() {
    await Promise.all([carregarSinais(), carregarHistorico()]);
}

criarBotoes();
carregarTudo();
setInterval(carregarSinais, 60000);
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(content=HTML)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
