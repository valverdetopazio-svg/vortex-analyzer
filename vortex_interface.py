"""
VORTEX TRADE ANALYZER - Com TradingView API
Usa a análise técnica do TradingView diretamente
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from tradingview_ta import TA_Handler, Interval
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

app = FastAPI(title="Vortex Trade Analyzer API")

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Mapeamento de Símbolos para TradingView
# ============================================
# Cada ativo precisa de: symbol, screener, exchange corretos
SYMBOL_CONFIG = {
    "GC=F": {  # Ouro
        "symbol": "GC1!",
        "screener": "commodity",
        "exchange": "COMEX"
    },
    "BTC-USD": {  # Bitcoin
        "symbol": "BTCUSD",
        "screener": "crypto",
        "exchange": "BINANCE"
    },
    "ETH-USD": {  # Ethereum
        "symbol": "ETHUSD",
        "screener": "crypto",
        "exchange": "BINANCE"
    },
    "AAPL": {  # Apple
        "symbol": "AAPL",
        "screener": "america",
        "exchange": "NASDAQ"
    },
    "NVDA": {  # NVIDIA
        "symbol": "NVDA",
        "screener": "america",
        "exchange": "NASDAQ"
    },
    "EURUSD=X": {  # EUR/USD
        "symbol": "EURUSD",
        "screener": "forex",
        "exchange": "FX"
    }
}

# Mapeamento de intervalos
INTERVAL_MAP = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
    "1W": Interval.INTERVAL_1_WEEK,
    "1M": Interval.INTERVAL_1_MONTH
}

# Nomes amigáveis
NOMES = {
    "GC=F": "XAU",
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
    "AAPL": "AAPL",
    "NVDA": "NVDA",
    "EURUSD=X": "EUR/USD"
}


class VortexTradingViewAnalyzer:
    def __init__(self, simbolo="GC=F", timeframe="15m"):
        self.simbolo = simbolo
        self.timeframe = timeframe
        self.config = SYMBOL_CONFIG.get(simbolo)
        self.analysis = None
        self.preco_atual = 0
        
    def get_analysis(self):
        """Busca análise técnica diretamente do TradingView"""
        try:
            if not self.config:
                return {"error": f"Símbolo {self.simbolo} não configurado"}
            
            interval = INTERVAL_MAP.get(self.timeframe, Interval.INTERVAL_15_MINUTES)
            
            # Criar handler do TradingView
            handler = TA_Handler(
                symbol=self.config["symbol"],
                screener=self.config["screener"],
                exchange=self.config["exchange"],
                interval=interval
            )
            
            # Buscar análise
            analysis = handler.get_analysis()
            self.analysis = analysis
            
            # Extrair dados
            indicators = analysis.indicators
            summary = analysis.summary
            
            # Preço atual (vem dos indicadores)
            self.preco_atual = indicators.get('close', indicators.get('price', 0))
            
            # Extrair valores dos indicadores
            rsi = indicators.get('RSI', 50)
            macd = indicators.get('MACD.macd', 0)
            macd_signal = indicators.get('MACD.signal', 0)
            ma20 = indicators.get('EMA20', indicators.get('SMA20', self.preco_atual))
            ma50 = indicators.get('EMA50', indicators.get('SMA50', self.preco_atual))
            
            # Suporte e Resistência (aproximados)
            pivot = indicators.get('Pivot', self.preco_atual)
            suporte = pivot * 0.99 if pivot else self.preco_atual * 0.99
            resistencia = pivot * 1.01 if pivot else self.preco_atual * 1.01
            
            # ATR (volatilidade) - aproximado
            atr = indicators.get('ATR', self.preco_atual * 0.005)
            
            # Extrair pontuação da recomendação
            buy = summary.get('BUY', 0)
            sell = summary.get('SELL', 0)
            neutral = summary.get('NEUTRAL', 0)
            recommendation = summary.get('RECOMMENDATION', 'NEUTRAL')
            
            # Converter recomendação para nosso formato
            if recommendation == 'STRONG_BUY':
                sinal = "COMPRA"
                forca = 85
            elif recommendation == 'BUY':
                sinal = "COMPRA"
                forca = 70
            elif recommendation == 'NEUTRAL':
                sinal = "NEUTRO"
                forca = 50
            elif recommendation == 'SELL':
                sinal = "VENDA"
                forca = 30
            elif recommendation == 'STRONG_SELL':
                sinal = "VENDA"
                forca = 15
            else:
                sinal = "NEUTRO"
                forca = 50
            
            # Calcular confiança baseada na força do sinal
            confianca = abs(forca - 50) * 2 + 50
            if confianca > 100:
                confianca = 100
            
            # Stop Loss e Take Profit
            stop_loss = self.preco_atual - (2 * atr)
            take_profit = self.preco_atual + (2 * atr)
            
            # Variação aproximada
            variacao = ((self.preco_atual - ma50) / ma50) * 100 if ma50 else 0
            
            return {
                'data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'simbolo': self.simbolo,
                'nome': NOMES.get(self.simbolo, self.simbolo),
                'timeframe': self.timeframe,
                'preco': round(self.preco_atual, 2),
                'variacao': round(variacao, 2),
                'sinal': sinal,
                'confianca': confianca,
                'forca': forca,
                'recomendacao_tradingview': recommendation,
                'rsi': round(rsi, 1),
                'ma20': round(ma20, 2),
                'ma50': round(ma50, 2),
                'suporte': round(suporte, 2),
                'resistencia': round(resistencia, 2),
                'stop_loss': round(stop_loss, 2),
                'take_profit': round(take_profit, 2),
                'entry': round(self.preco_atual, 2),
                'atr': round(atr, 2),
                'pontuacao': {
                    'compra': buy,
                    'venda': sell,
                    'neutro': neutral
                }
            }
            
        except Exception as e:
            return {"error": f"Erro ao buscar dados do TradingView: {str(e)}"}


# ============================================
# ENDPOINTS DA API
# ============================================

@app.get("/")
async def root():
    return {"message": "Vortex Trade Analyzer API com TradingView", "status": "online"}

@app.get("/analyze")
async def analyze(
    symbol: str = Query("GC=F", description="Ativo (GC=F, BTC-USD, AAPL)"),
    interval: str = Query("15m", description="Timeframe (1m,5m,15m,1h,4h,1d)")
):
    """Retorna análise técnica do TradingView"""
    analyzer = VortexTradingViewAnalyzer(simbolo=symbol, timeframe=interval)
    resultado = analyzer.get_analysis()
    return resultado

@app.get("/available")
async def get_available_symbols():
    """Retorna lista de símbolos disponíveis"""
    return {
        "symbols": [
            {"id": "GC=F", "name": "XAU (Ouro)", "type": "commodity"},
            {"id": "BTC-USD", "name": "Bitcoin", "type": "crypto"},
            {"id": "ETH-USD", "name": "Ethereum", "type": "crypto"},
            {"id": "AAPL", "name": "Apple", "type": "stock"},
            {"id": "NVDA", "name": "NVIDIA", "type": "stock"},
            {"id": "EURUSD=X", "name": "EUR/USD", "type": "forex"}
        ]
    }


# ============================================
# INTERFACE HTML COMPLETA
# ============================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vortex Trade Analyzer - TradingView</title>
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
        h1 { text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #8892b0; margin-bottom: 30px; }
        .controls {
            text-align: center;
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        select, button {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
        }
        select {
            background: rgba(255,255,255,0.1);
            color: white;
        }
        button {
            background: #7b2cbf;
            color: white;
        }
        button:hover { background: #9b4dff; transform: scale(1.02); }
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
        .tv-badge {
            display: inline-block;
            background: rgba(0,0,0,0.3);
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            margin-top: 10px;
        }
        @media (max-width: 768px) {
            .preco { font-size: 2em; }
            h1 { font-size: 1.5em; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🔬 Vortex Trade Analyzer</h1>
    <div class="subtitle">Powered by TradingView • Análise Técnica em Tempo Real</div>
    
    <div class="controls">
        <select id="symbol">
            <option value="GC=F">🥇 XAU (Ouro)</option>
            <option value="BTC-USD">₿ Bitcoin</option>
            <option value="ETH-USD">⟠ Ethereum</option>
            <option value="AAPL">🍎 Apple</option>
            <option value="NVDA">🎮 NVIDIA</option>
            <option value="EURUSD=X">💶 EUR/USD</option>
        </select>
        <select id="interval">
            <option value="1m">1 minuto</option>
            <option value="5m">5 minutos</option>
            <option value="15m" selected>15 minutos</option>
            <option value="1h">1 hora</option>
            <option value="4h">4 horas</option>
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
    div.innerHTML = '<div class="loading">🔄 Buscando análise do TradingView...</div>';
    
    try {
        const response = await fetch(`/analyze?symbol=${symbol}&interval=${interval}`);
        const data = await response.json();
        
        if (data.error) {
            div.innerHTML = `<div class="card">❌ ${data.error}</div>`;
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
                <div class="${variacaoClass}">${data.variacao >= 0 ? '+' : ''}${data.variacao}%</div>
                <div style="margin-top: 10px;">${data.data}</div>
                <div class="tv-badge">📊 TradingView: ${data.recomendacao_tradingview}</div>
                <div style="margin-top: 10px;">🎲 Confiança: ${data.confianca}% | 💪 Força: ${data.forca}%</div>
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
                <div class="metric">⚡ ATR<br><strong>${data.atr}</strong></div>
            </div>
            
            <div class="grid">
                <div class="metric">🛡️ Suporte<br><strong>${data.suporte}</strong></div>
                <div class="metric">🚀 Resistência<br><strong>${data.resistencia}</strong></div>
                <div class="metric">📐 Pontuação TV<br><strong>👍 ${data.pontuacao.compra} / 👎 ${data.pontuacao.venda} / ➖ ${data.pontuacao.neutro}</strong></div>
            </div>
            
            <div class="card" style="margin-top: 20px;">
                <small>✅ Análise fornecida pelo TradingView • Dados em tempo real • Indicadores: RSI, MACD, Médias Móveis, Estocástico, etc.<br>
                ⚠️ Apenas para fins educacionais • Não é recomendação de investimento</small>
            </div>
        `;
    } catch(e) {
        div.innerHTML = `<div class="card">❌ Erro de conexão: ${e.message}<br><br>Verifique se o servidor está rodando</div>`;
    }
}

// Carregar análise automaticamente
analisar();
</script>
</body>
</html>
"""


@app.get("/interface")
async def interface():
    return HTMLResponse(content=HTML_PAGE)


# ============================================
# SERVIDOR
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Vortex Trade Analyzer com TradingView")
    print(f"📡 API: http://localhost:{port}")
    print(f"📊 Interface: http://localhost:{port}/interface")
    print(f"📈 Teste: http://localhost:{port}/analyze?symbol=GC=F")
    uvicorn.run(app, host="0.0.0.0", port=port)
