"""
VALVERDE TRADE IA - Interface Profissional
Com design exatamente como solicitado
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from tradingview_ta import TA_Handler, Interval
from datetime import datetime
import os
import json

app = FastAPI(title="Vortex Trade IA")

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
    "GC=F": {"symbol": "GC1!", "screener": "commodity", "exchange": "COMEX", "nome": "XAU"},
    "BTC-USD": {"symbol": "BTCUSD", "screener": "crypto", "exchange": "BINANCE", "nome": "BTC"},
    "ETH-USD": {"symbol": "ETHUSD", "screener": "crypto", "exchange": "BINANCE", "nome": "ETH"},
    "AAPL": {"symbol": "AAPL", "screener": "america", "exchange": "NASDAQ", "nome": "AAPL"},
    "NVDA": {"symbol": "NVDA", "screener": "america", "exchange": "NASDAQ", "nome": "NVDA"}
}

INTERVAL_MAP = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
}

# Histórico de sinais (simulado - em produção viria de um banco de dados)
HISTORICO_SINAIS = [
    {
        "data": "02 de abr. de 2026, 18:03",
        "entry": 4676.4,
        "stop": 4669.03,
        "tp1": 4717.77,
        "sinal": "COMPRA",
        "forca": 87,
        "ativo": "XAU",
        "timeframe": "15m"
    },
    {
        "data": "27 de mar. de 2026, 14:38",
        "entry": 4494.33,
        "stop": 4474.92,
        "tp1": 4563.08,
        "sinal": "COMPRA",
        "forca": 82,
        "ativo": "XAU",
        "timeframe": "15m"
    }
]


def get_tradingview_analysis(symbol, interval):
    """Busca análise do TradingView"""
    try:
        config = SYMBOL_CONFIG.get(symbol)
        if not config:
            return None
        
        tv_interval = INTERVAL_MAP.get(interval, Interval.INTERVAL_15_MINUTES)
        
        handler = TA_Handler(
            symbol=config["symbol"],
            screener=config["screener"],
            exchange=config["exchange"],
            interval=tv_interval
        )
        
        analysis = handler.get_analysis()
        indicators = analysis.indicators
        
        preco = indicators.get('close', 0)
        rsi = indicators.get('RSI', 50)
        summary = analysis.summary
        recommendation = summary.get('RECOMMENDATION', 'NEUTRAL')
        
        # Determinar sinal baseado na recomendação do TradingView
        if recommendation in ['STRONG_BUY', 'BUY']:
            sinal = "COMPRA"
            forca = 85 if recommendation == 'STRONG_BUY' else 70
        elif recommendation in ['STRONG_SELL', 'SELL']:
            sinal = "VENDA"
            forca = 15 if recommendation == 'STRONG_SELL' else 30
        else:
            sinal = "NEUTRO"
            forca = 50
        
        confianca = abs(forca - 50) * 2 + 50
        if confianca > 100:
            confianca = 100
        
        # Calcular Stop e Take (baseado no ATR)
        atr = indicators.get('ATR', preco * 0.005)
        stop_loss = preco - (2 * atr)
        take_profit = preco + (2 * atr)
        
        return {
            'preco': round(preco, 2),
            'rsi': round(rsi, 1),
            'sinal': sinal,
            'forca': forca,
            'confianca': confianca,
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'data': datetime.now().strftime('%d de %b. de %Y, %H:%M'),
            'recomendacao': recommendation
        }
    except Exception as e:
        print(f"Erro: {e}")
        return None


# ============================================
# INTERFACE HTML EXATAMENTE COMO VOCÊ QUER
# ============================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vortex Trade IA</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            min-height: 100vh;
            color: #ffffff;
            padding: 40px 20px;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo {
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #8892b0;
            font-size: 0.9em;
        }

        /* Controles */
        .controls {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        select, button {
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 500;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        select {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        button {
            background: linear-gradient(90deg, #7b2cbf, #9b4dff);
            color: white;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(123, 44, 191, 0.4);
        }

        /* Card Principal do Sinal */
        .signal-card {
            background: rgba(15, 20, 40, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 40px;
            text-align: center;
            margin-bottom: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .signal-badge {
            display: inline-block;
            padding: 8px 24px;
            border-radius: 50px;
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 20px;
        }

        .signal-compra {
            background: linear-gradient(135deg, #00c853, #00e676);
            box-shadow: 0 0 20px rgba(0, 200, 83, 0.3);
        }

        .signal-venda {
            background: linear-gradient(135deg, #d50000, #ff1744);
            box-shadow: 0 0 20px rgba(213, 0, 0, 0.3);
        }

        .signal-neutro {
            background: linear-gradient(135deg, #ff8f00, #ffab40);
            box-shadow: 0 0 20px rgba(255, 143, 0, 0.3);
        }

        .asset-info {
            font-size: 0.9em;
            color: #8892b0;
            margin-bottom: 8px;
        }

        .price {
            font-size: 3.5em;
            font-weight: bold;
            margin: 20px 0;
        }

        /* Grid de Entry/Stop/TP */
        .trade-levels {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }

        .level-card {
            background: rgba(15, 20, 40, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .level-label {
            font-size: 0.8em;
            color: #8892b0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }

        .level-value {
            font-size: 1.5em;
            font-weight: bold;
        }

        .level-stop {
            color: #ff1744;
        }

        .level-tp {
            color: #00e676;
        }

        /* Histórico */
        .history-card {
            background: rgba(15, 20, 40, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .history-title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            transition: background 0.2s;
        }

        .history-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
        }

        .history-left {
            flex: 2;
        }

        .history-symbol {
            font-weight: bold;
            margin-bottom: 4px;
        }

        .history-date {
            font-size: 0.75em;
            color: #8892b0;
        }

        .history-details {
            font-size: 0.8em;
            color: #8892b0;
            margin-top: 4px;
        }

        .history-right {
            text-align: right;
        }

        .history-signal {
            font-weight: bold;
            margin-bottom: 4px;
        }

        .history-signal-compra {
            color: #00e676;
        }

        .history-signal-venda {
            color: #ff1744;
        }

        .history-strength {
            font-size: 0.75em;
            color: #8892b0;
        }

        .strength-bar {
            width: 60px;
            height: 3px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
            margin-top: 4px;
            overflow: hidden;
        }

        .strength-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            border-radius: 3px;
        }

        /* Loading */
        .loading {
            text-align: center;
            padding: 60px;
            color: #8892b0;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 30px;
            color: #8892b0;
            font-size: 0.7em;
            margin-top: 40px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Responsivo */
        @media (max-width: 600px) {
            .price {
                font-size: 2.5em;
            }
            .trade-levels {
                grid-template-columns: 1fr;
                gap: 12px;
            }
            .history-item {
                flex-direction: column;
                text-align: center;
            }
            .history-right {
                text-align: center;
                margin-top: 8px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo">🔬 Vortex Trade IA</div>
            <div class="subtitle">Análises de Trading com Inteligência Artificial</div>
        </div>

        <!-- Controls -->
        <div class="controls">
            <select id="symbolSelect">
                <option value="GC=F">🥇 XAU (Ouro) - Commodities</option>
                <option value="BTC-USD">₿ BTC (Bitcoin) - Cripto</option>
                <option value="ETH-USD">⟠ ETH (Ethereum) - Cripto</option>
                <option value="AAPL">🍎 AAPL (Apple) - Ações</option>
                <option value="NVDA">🎮 NVDA (NVIDIA) - Ações</option>
            </select>
            <select id="timeframeSelect">
                <option value="15m" selected>15 minutos</option>
                <option value="1h">1 hora</option>
                <option value="4h">4 horas</option>
                <option value="1d">1 dia</option>
            </select>
            <button onclick="analisar()">🚀 Analisar Agora</button>
        </div>

        <!-- Loading -->
        <div id="loading" style="display: none;" class="loading">🔄 Carregando análise...</div>

        <!-- Conteúdo -->
        <div id="conteudo"></div>

        <!-- Footer -->
        <div class="footer">
            <p>Vortex Trade IA • Dados fornecidos pelo TradingView • Análise em tempo real</p>
            <p style="margin-top: 8px;">⚠️ Apenas para fins educacionais • Não é recomendação de investimento</p>
        </div>
    </div>

    <script>
        // Histórico de sinais (vem do backend)
        let historicoSinais = [];

        async function analisar() {
            const symbol = document.getElementById('symbolSelect').value;
            const interval = document.getElementById('timeframeSelect').value;
            
            document.getElementById('loading').style.display = 'block';
            document.getElementById('conteudo').innerHTML = '';
            
            try {
                const response = await fetch(`/analyze?symbol=${symbol}&interval=${interval}`);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('conteudo').innerHTML = `<div class="signal-card" style="color:#ff1744">❌ ${data.error}</div>`;
                } else {
                    renderizarAnalise(data);
                }
            } catch (error) {
                document.getElementById('conteudo').innerHTML = `<div class="signal-card" style="color:#ff1744">❌ Erro de conexão: ${error.message}</div>`;
            }
            
            document.getElementById('loading').style.display = 'none';
        }

        function renderizarAnalise(data) {
            const sinalClass = data.sinal === 'COMPRA' ? 'signal-compra' : (data.sinal === 'VENDA' ? 'signal-venda' : 'signal-neutro');
            const stopClass = data.sinal === 'COMPRA' ? 'level-stop' : '';
            const tpClass = data.sinal === 'COMPRA' ? 'level-tp' : '';
            
            // Extrair nome do ativo
            const ativoNome = data.nome || data.simbolo.split('-')[0].split('=')[0];
            
            const html = `
                <!-- Card Principal do Sinal -->
                <div class="signal-card">
                    <div class="signal-badge ${sinalClass}">
                        🎯 ${data.sinal}
                    </div>
                    <div class="asset-info">
                        ${ativoNome} • ${data.timeframe}
                    </div>
                    <div class="asset-info" style="font-size: 0.8em;">
                        ${data.data}
                    </div>
                    <div class="price">
                        ${data.entry}
                    </div>
                    <div style="font-size: 0.8em; color: #8892b0;">
                        Confiança: ${data.confianca}% • Força: ${data.forca}%
                    </div>
                </div>

                <!-- Entry, Stop, TP -->
                <div class="trade-levels">
                    <div class="level-card">
                        <div class="level-label">📊 ENTRY</div>
                        <div class="level-value">${data.entry}</div>
                    </div>
                    <div class="level-card">
                        <div class="level-label">⛔ STOP</div>
                        <div class="level-value ${stopClass}">${data.stop_loss}</div>
                    </div>
                    <div class="level-card">
                        <div class="level-label">✅ TP 1</div>
                        <div class="level-value ${tpClass}">${data.take_profit}</div>
                    </div>
                </div>
            `;
            
            document.getElementById('conteudo').innerHTML = html;
            carregarHistorico();
        }

        async function carregarHistorico() {
            try {
                const response = await fetch('/history');
                const historico = await response.json();
                
                let historicoHtml = `
                    <div class="history-card">
                        <div class="history-title">📜 HISTÓRICO DE SINAIS</div>
                `;
                
                historico.forEach(item => {
                    const sinalClass = item.sinal === 'COMPRA' ? 'history-signal-compra' : 
                                      (item.sinal === 'VENDA' ? 'history-signal-venda' : '');
                    
                    historicoHtml += `
                        <div class="history-item">
                            <div class="history-left">
                                <div class="history-symbol">${item.ativo} • ${item.timeframe}</div>
                                <div class="history-date">${item.data}</div>
                                <div class="history-details">Entry: ${item.entry} | Stop: ${item.stop} | TP1: ${item.tp1}</div>
                            </div>
                            <div class="history-right">
                                <div class="history-signal ${sinalClass}">${item.sinal}</div>
                                <div class="history-strength">${item.forca}% força</div>
                                <div class="strength-bar">
                                    <div class="strength-fill" style="width: ${item.forca}%"></div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                historicoHtml += `</div>`;
                
                // Adicionar ao final do conteúdo
                const conteudo = document.getElementById('conteudo');
                conteudo.innerHTML += historicoHtml;
            } catch (error) {
                console.log('Erro ao carregar histórico:', error);
            }
        }

        // Carregar análise inicial
        analisar();
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

@app.get("/analyze")
async def analyze(
    symbol: str = Query("GC=F"),
    interval: str = Query("15m")
):
    """Retorna análise em tempo real"""
    resultado = get_tradingview_analysis(symbol, interval)
    if resultado:
        config = SYMBOL_CONFIG.get(symbol, {})
        resultado['simbolo'] = symbol
        resultado['nome'] = config.get('nome', symbol.split('-')[0].split('=')[0])
        resultado['timeframe'] = interval
        resultado['entry'] = resultado['preco']
        return resultado
    return {"error": "Não foi possível obter análise do TradingView"}

@app.get("/history")
async def get_history():
    """Retorna histórico de sinais"""
    return HISTORICO_SINAIS


# ============================================
# SERVIDOR
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Vortex Trade IA - Interface Profissional")
    print(f"📍 Acesse: http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
