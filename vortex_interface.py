from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vortex Trade Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; font-size: 2em; }
        .card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            text-align: center;
        }
        .sinal-compra { background: linear-gradient(135deg, #00c853, #00e676); }
        .sinal-venda { background: linear-gradient(135deg, #d50000, #ff1744); }
        .sinal-neutro { background: linear-gradient(135deg, #ff8f00, #ffab40); }
        .preco { font-size: 3em; font-weight: bold; margin: 20px 0; }
        select, button {
            padding: 12px 24px;
            margin: 10px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
        }
        button {
            background: #7b2cbf;
            color: white;
        }
        button:hover { background: #9b4dff; transform: scale(1.02); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .metric {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
        }
        .loading { text-align: center; padding: 40px; }
        .variacao-positiva { color: #00e676; }
        .variacao-negativa { color: #ff1744; }
        @media (max-width: 768px) {
            .preco { font-size: 2em; }
            h1 { font-size: 1.5em; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🔬 Vortex Trade Analyzer</h1>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <select id="symbol">
            <option value="GC=F">🥇 XAU (Ouro)</option>
            <option value="BTC-USD">₿ Bitcoin</option>
            <option value="ETH-USD">⟠ Ethereum</option>
            <option value="AAPL">🍎 Apple</option>
            <option value="NVDA">🎮 NVIDIA</option>
        </select>
        <select id="interval">
            <option value="5m">5 minutos</option>
            <option value="15m" selected>15 minutos</option>
            <option value="1h">1 hora</option>
            <option value="1d">1 dia</option>
        </select>
        <button onclick="analisar()">🚀 Analisar Agora</button>
    </div>
    
    <div id="resultado" class="loading">📊 Clique em "Analisar Agora" para começar</div>
</div>

<script>
async function analisar() {
    const symbol = document.getElementById('symbol').value;
    const interval = document.getElementById('interval').value;
    
    const div = document.getElementById('resultado');
    div.innerHTML = '<div class="loading">🔄 Carregando análise em tempo real...</div>';
    
    try {
        const response = await fetch(`/analyze?symbol=${symbol}&interval=${interval}`);
        const data = await response.json();
        
        if (data.error) {
            div.innerHTML = `<div class="card">❌ Erro: ${data.error}</div>`;
            return;
        }
        
        const sinalClass = data.sinal === 'COMPRA' ? 'sinal-compra' : 
                          (data.sinal === 'VENDA' ? 'sinal-venda' : 'sinal-neutro');
        const variacaoClass = data.variacao >= 0 ? 'variacao-positiva' : 'variacao-negativa';
        
        div.innerHTML = `
            <div class="card ${sinalClass}">
                <h2 style="font-size: 2em;">🎯 ${data.sinal}</h2>
                <div class="preco">${data.nome} • ${data.timeframe}</div>
                <div class="preco" style="font-size: 2.5em;">${data.preco}</div>
                <div class="${variacaoClass}" style="font-size: 1.2em;">${data.variacao >= 0 ? '+' : ''}${data.variacao}% (24h)</div>
                <div style="margin-top: 15px;">${data.data}</div>
                <div style="margin-top: 10px; font-size: 1.1em;">🎲 Confiança: ${data.confianca}% | 💪 Força: ${data.forca}%</div>
            </div>
            
            <div class="grid">
                <div class="metric">📊 ENTRY<br><strong style="font-size: 1.3em;">${data.entry}</strong></div>
                <div class="metric">⛔ STOP LOSS<br><strong style="color: #ff1744; font-size: 1.3em;">${data.stop_loss}</strong></div>
                <div class="metric">✅ TAKE PROFIT<br><strong style="color: #00e676; font-size: 1.3em;">${data.take_profit}</strong></div>
            </div>
            
            <div class="grid">
                <div class="metric">📈 RSI (14)<br><strong>${data.rsi}</strong><br><small>${data.rsi < 30 ? '🟢 Sobrevendido' : (data.rsi > 70 ? '🔴 Sobrecomprado' : '🟡 Neutro')}</small></div>
                <div class="metric">📊 MA20<br><strong>${data.ma20}</strong></div>
                <div class="metric">📊 MA50<br><strong>${data.ma50}</strong></div>
                <div class="metric">⚡ ATR<br><strong>${data.atr}</strong><br><small>Volatilidade</small></div>
            </div>
            
            <div class="grid">
                <div class="metric">🛡️ Suporte<br><strong>${data.suporte}</strong></div>
                <div class="metric">🚀 Resistência<br><strong>${data.resistencia}</strong></div>
                <div class="metric">📐 Range<br><strong>${(data.resistencia - data.suporte).toFixed(2)}</strong></div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <small>⚠️ Análise baseada em RSI, MACD, Médias Móveis e ATR. Dados em tempo real via Yahoo Finance.<br>
                Este conteúdo é apenas para fins educacionais e não constitui recomendação de investimento.</small>
            </div>
        `;
    } catch(e) {
        div.innerHTML = `<div class="card">❌ Erro de conexão: ${e.message}</div>`;
    }
}

// Carregar análise automaticamente ao abrir a página
analisar();
</script>
</body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(content=HTML)

@app.get("/analyze")
async def analyze(
    symbol: str = Query("GC=F"),
    interval: str = Query("15m")
):
    try:
        ticker = yf.Ticker(symbol)
        dados = ticker.history(period="5d", interval=interval)
        
        if dados.empty:
            return {"error": "Não foi possível buscar dados"}
        
        preco_atual = dados['Close'].iloc[-1]
        df = dados
        
        # RSI
        delta = df['Close'].diff()
        ganho = delta.where(delta > 0, 0).rolling(14).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = ganho / perda
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Médias
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma50 = df['Close'].rolling(50).mean().iloc[-1]
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        
        # Suporte/Resistência
        suporte = df['Low'].rolling(20).min().iloc[-1]
        resistencia = df['High'].rolling(20).max().iloc[-1]
        
        # ATR
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        
        # Pontuação
        pontos_compra = 0
        pontos_venda = 0
        
        if rsi < 30:
            pontos_compra += 1
        elif rsi > 70:
            pontos_venda += 1
            
        if preco_atual > ma20:
            pontos_compra += 1
        else:
            pontos_venda += 1
            
        if preco_atual > ma50:
            pontos_compra += 1
        else:
            pontos_venda += 1
            
        if macd.iloc[-1] > macd_signal.iloc[-1]:
            pontos_compra += 1
        else:
            pontos_venda += 1
        
        # Decisão
        total = pontos_compra + pontos_venda
        if total == 0:
            sinal = "NEUTRO"
            confianca = 50
            forca = 50
        else:
            forca = (pontos_compra / total) * 100
            if forca >= 60:
                sinal = "COMPRA"
            elif forca <= 40:
                sinal = "VENDA"
            else:
                sinal = "NEUTRO"
            confianca = int(abs(forca - 50) * 2 + 50)
            if confianca > 100:
                confianca = 100
        
        stop_loss = preco_atual - (2 * atr)
        take_profit = preco_atual + (2 * atr)
        
        # Variação
        preco_anterior = df['Close'].iloc[0]
        variacao = ((preco_atual - preco_anterior) / preco_anterior) * 100
        
        nomes = {"GC=F": "XAU", "BTC-USD": "BTC", "ETH-USD": "ETH", "AAPL": "AAPL", "NVDA": "NVDA"}
        
        return {
            'data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'nome': nomes.get(symbol, symbol),
            'timeframe': interval,
            'preco': round(preco_atual, 2),
            'variacao': round(variacao, 2),
            'sinal': sinal,
            'confianca': confianca,
            'forca': round(forca, 1),
            'rsi': round(rsi, 1),
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'suporte': round(suporte, 2),
            'resistencia': round(resistencia, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'entry': round(preco_atual, 2),
            'atr': round(atr, 2)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
