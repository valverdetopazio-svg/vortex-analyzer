"""
VALVERDE TRADE IA - Sistema de Análise com Confirmação de Sinais
Com Tracking de Win/Loss e Estatísticas por Ativo e Timeframe
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from tradingview_ta import TA_Handler, Interval
from datetime import datetime
import os
import json
from typing import Dict, List

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
    "GC=F": {"symbol": "GC1!", "screener": "commodity", "exchange": "COMEX", "nome": "XAU", "tipo": "Commodities"},
    "BTC-USD": {"symbol": "BTCUSD", "screener": "crypto", "exchange": "BINANCE", "nome": "BTC", "tipo": "Cripto"},
    "ETH-USD": {"symbol": "ETHUSD", "screener": "crypto", "exchange": "BINANCE", "nome": "ETH", "tipo": "Cripto"},
    "AAPL": {"symbol": "AAPL", "screener": "america", "exchange": "NASDAQ", "nome": "AAPL", "tipo": "Ações"},
    "NVDA": {"symbol": "NVDA", "screener": "america", "exchange": "NASDAQ", "nome": "NVDA", "tipo": "Ações"},
    "EURUSD=X": {"symbol": "EURUSD", "screener": "forex", "exchange": "FX", "nome": "EUR/USD", "tipo": "Forex"}
}

INTERVAL_MAP = {
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "30m": Interval.INTERVAL_30_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
}

# Arquivo para armazenar histórico de sinais
HISTORICO_FILE = "historico_sinais.json"

def carregar_historico():
    """Carrega histórico de sinais do arquivo"""
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_historico(historico):
    """Salva histórico de sinais no arquivo"""
    with open(HISTORICO_FILE, "w") as f:
        json.dump(historico, f, indent=2)

def calcular_estatisticas(historico, ativo=None, timeframe=None):
    """Calcula estatísticas de win/loss por ativo e timeframe"""
    # Filtrar por ativo e timeframe se especificado
    filtrados = historico
    if ativo:
        filtrados = [s for s in filtrados if s.get('ativo') == ativo]
    if timeframe:
        filtrados = [s for s in filtrados if s.get('timeframe') == timeframe]
    
    # Sinais confirmados apenas
    confirmados = [s for s in filtrados if s.get('confirmado') is not None]
    
    total = len(confirmados)
    wins = len([s for s in confirmados if s.get('confirmado') == 'win'])
    losses = len([s for s in confirmados if s.get('confirmado') == 'loss'])
    
    win_rate = round((wins / total * 100) if total > 0 else 0, 1)
    
    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate
    }


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
        
        # Determinar sinal
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
        
        # Calcular Stop e Take
        atr = indicators.get('ATR', preco * 0.005)
        stop_loss = preco - (2 * atr) if sinal == "COMPRA" else preco + (2 * atr)
        take_profit = preco + (2 * atr) if sinal == "COMPRA" else preco - (2 * atr)
        
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
        print(f"Erro TradingView: {e}")
        return None


# ============================================
# INTERFACE HTML COMPLETA
# ============================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Valverde Trade IA</title>
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
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 30px;
        }

        .logo {
            font-size: 2em;
            font-weight: bold;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        .subtitle {
            color: #8892b0;
            font-size: 0.85em;
        }

        /* Grid de Ativos - VISÍVEL */
        .assets-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: center;
            margin-bottom: 20px;
        }

        .asset-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 10px 20px;
            border-radius: 40px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
            font-weight: 500;
        }

        .asset-btn:hover {
            background: rgba(123, 44, 191, 0.3);
            border-color: #7b2cbf;
        }

        .asset-btn.active {
            background: linear-gradient(90deg, #7b2cbf, #9b4dff);
            border-color: transparent;
        }

        /* Grid de Timeframes - VISÍVEL */
        .timeframes-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-bottom: 20px;
        }

        .tf-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 8px 18px;
            border-radius: 40px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 13px;
        }

        .tf-btn:hover {
            background: rgba(123, 44, 191, 0.3);
        }

        .tf-btn.active {
            background: linear-gradient(90deg, #7b2cbf, #9b4dff);
        }

        /* Botão Analisar */
        .analyze-btn {
            display: block;
            width: 100%;
            max-width: 200px;
            margin: 0 auto 30px;
            background: linear-gradient(90deg, #00c853, #00e676);
            border: none;
            padding: 12px 24px;
            border-radius: 40px;
            color: white;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .analyze-btn:hover {
            transform: scale(1.02);
        }

        /* Card Principal */
        .signal-card {
            background: rgba(15, 20, 40, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 30px;
            text-align: center;
            margin-bottom: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .signal-badge {
            display: inline-block;
            padding: 8px 28px;
            border-radius: 50px;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 16px;
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
            font-size: 3em;
            font-weight: bold;
            margin: 15px 0;
        }

        /* Grid Entry/Stop/TP */
        .trade-levels {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .level-card {
            background: rgba(15, 20, 40, 0.8);
            border-radius: 20px;
            padding: 16px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .level-label {
            font-size: 0.75em;
            color: #8892b0;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .level-value {
            font-size: 1.3em;
            font-weight: bold;
        }

        .level-stop {
            color: #ff1744;
        }

        .level-tp {
            color: #00e676;
        }

        /* Botões de Confirmação */
        .confirm-buttons {
            display: flex;
            gap: 16px;
            justify-content: center;
            margin-top: 20px;
            margin-bottom: 30px;
        }

        .win-btn {
            background: linear-gradient(135deg, #00c853, #00e676);
            border: none;
            padding: 12px 40px;
            border-radius: 40px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
        }

        .loss-btn {
            background: linear-gradient(135deg, #d50000, #ff1744);
            border: none;
            padding: 12px 40px;
            border-radius: 40px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            font-size: 16px;
        }

        /* Estatísticas */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stats-card {
            background: rgba(15, 20, 40, 0.8);
            border-radius: 20px;
            padding: 16px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .stats-title {
            font-size: 0.8em;
            color: #8892b0;
            margin-bottom: 8px;
        }

        .stats-value {
            font-size: 1.5em;
            font-weight: bold;
        }

        .stats-win-rate {
            font-size: 1.8em;
            font-weight: bold;
            color: #00e676;
        }

        /* Histórico */
        .history-card {
            background: rgba(15, 20, 40, 0.8);
            border-radius: 24px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .history-title {
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 16px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .history-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            flex-wrap: wrap;
            gap: 10px;
        }

        .history-sinal {
            font-weight: bold;
        }

        .history-confirm {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
        }

        .history-win {
            background: rgba(0, 200, 83, 0.2);
            color: #00e676;
        }

        .history-loss {
            background: rgba(213, 0, 0, 0.2);
            color: #ff1744;
        }

        .history-pending {
            background: rgba(255, 143, 0, 0.2);
            color: #ffab40;
        }

        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
            color: #8892b0;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 20px;
            color: #8892b0;
            font-size: 0.7em;
            margin-top: 30px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        @media (max-width: 600px) {
            .price { font-size: 2.2em; }
            .trade-levels { grid-template-columns: 1fr; gap: 10px; }
            .confirm-buttons { flex-direction: column; align-items: center; }
            .win-btn, .loss-btn { width: 80%; }
            .assets-grid, .timeframes-grid { gap: 8px; }
            .asset-btn, .tf-btn { padding: 6px 14px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="logo">📊 Valverde Trade IA</div>
            <div class="subtitle">Análises de Trading com Inteligência Artificial</div>
        </div>

        <!-- Ativos - VISÍVEL -->
        <div class="assets-grid" id="assetsGrid">
            <button class="asset-btn" data-symbol="GC=F">🥇 XAU (Ouro) - Commodities</button>
            <button class="asset-btn" data-symbol="BTC-USD">₿ BTC (Bitcoin) - Cripto</button>
            <button class="asset-btn" data-symbol="ETH-USD">⟠ ETH (Ethereum) - Cripto</button>
            <button class="asset-btn" data-symbol="AAPL">🍎 AAPL (Apple) - Ações</button>
            <button class="asset-btn" data-symbol="NVDA">🎮 NVDA (NVIDIA) - Ações</button>
        </div>

        <!-- Timeframes - VISÍVEL -->
        <div class="timeframes-grid" id="timeframesGrid">
            <button class="tf-btn" data-interval="5m">5 minutos</button>
            <button class="tf-btn" data-interval="15m">15 minutos</button>
            <button class="tf-btn" data-interval="30m">30 minutos</button>
            <button class="tf-btn" data-interval="1h">1 hora</button>
            <button class="tf-btn" data-interval="4h">4 horas</button>
            <button class="tf-btn" data-interval="1d">1 dia</button>
        </div>

        <!-- Botão Analisar -->
        <button class="analyze-btn" onclick="analisar()">🚀 Analisar Agora</button>

        <!-- Loading -->
        <div id="loading" style="display: none;" class="loading">🔄 Carregando análise...</div>

        <!-- Conteúdo Principal -->
        <div id="conteudo"></div>

        <!-- Footer -->
        <div class="footer">
            <p>Valverde Trade IA • Dados fornecidos pelo TradingView</p>
            <p>⚠️ Apenas para fins educacionais • Não é recomendação de investimento</p>
        </div>
    </div>

    <script>
        let currentAnalysis = null;
        let currentAtivo = "GC=F";
        let currentTimeframe = "15m";

        // Configurar eventos dos botões
        document.querySelectorAll('.asset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.asset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentAtivo = btn.dataset.symbol;
                analisar();
            });
        });

        document.querySelectorAll('.tf-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentTimeframe = btn.dataset.interval;
                analisar();
            });
        });

        // Ativar primeiro botão por padrão
        document.querySelector('.asset-btn').classList.add('active');
        document.querySelector('.tf-btn').classList.add('active');

        async function analisar() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('conteudo').innerHTML = '';
            
            try {
                const response = await fetch(`/analyze?symbol=${currentAtivo}&interval=${currentTimeframe}`);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('conteudo').innerHTML = `<div class="signal-card" style="color:#ff1744">❌ ${data.error}</div>`;
                } else {
                    currentAnalysis = data;
                    renderizarAnalise(data);
                    carregarHistoricoEStats();
                }
            } catch (error) {
                document.getElementById('conteudo').innerHTML = `<div class="signal-card" style="color:#ff1744">❌ Erro: ${error.message}</div>`;
            }
            
            document.getElementById('loading').style.display = 'none';
        }

        function renderizarAnalise(data) {
            const sinalClass = data.sinal === 'COMPRA' ? 'signal-compra' : (data.sinal === 'VENDA' ? 'signal-venda' : 'signal-neutro');
            
            const html = `
                <div class="signal-card">
                    <div class="signal-badge ${sinalClass}">
                        🎯 ${data.sinal}
                    </div>
                    <div class="asset-info">
                        ${data.nome} • ${data.timeframe}
                    </div>
                    <div class="asset-info" style="font-size: 0.8em;">
                        ${data.data}
                    </div>
                    <div class="price">
                        ${data.entry}
                    </div>
                    <div style="font-size: 0.85em; color: #8892b0;">
                        Confiança: ${data.confianca}% • Força: ${data.forca}%
                    </div>
                </div>

                <div class="trade-levels">
                    <div class="level-card">
                        <div class="level-label">📊 ENTRY</div>
                        <div class="level-value">${data.entry}</div>
                    </div>
                    <div class="level-card">
                        <div class="level-label">⛔ STOP</div>
                        <div class="level-value level-stop">${data.stop_loss}</div>
                    </div>
                    <div class="level-card">
                        <div class="level-label">✅ TP 1</div>
                        <div class="level-value level-tp">${data.take_profit}</div>
                    </div>
                </div>

                <div class="confirm-buttons">
                    <button class="win-btn" onclick="confirmarSinal('win')">✅ WIN - Acertou</button>
                    <button class="loss-btn" onclick="confirmarSinal('loss')">❌ LOSS - Errou</button>
                </div>
            `;
            
            document.getElementById('conteudo').innerHTML = html;
        }

        async function confirmarSinal(resultado) {
            if (!currentAnalysis) return;
            
            const confirmacao = {
                ...currentAnalysis,
                confirmado: resultado,
                data_confirmacao: new Date().toLocaleString()
            };
            
            const response = await fetch('/confirmar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(confirmacao)
            });
            
            if (response.ok) {
                alert(`✅ Sinal registrado como ${resultado.toUpperCase()}!`);
                carregarHistoricoEStats();
            }
        }

        async function carregarHistoricoEStats() {
            try {
                const response = await fetch(`/estatisticas?ativo=${currentAtivo}&timeframe=${currentTimeframe}`);
                const stats = await response.json();
                
                const historyResponse = await fetch('/historico');
                const historico = await historyResponse.json();
                
                let statsHtml = `
                    <div class="stats-grid">
                        <div class="stats-card">
                            <div class="stats-title">📊 Total de Sinais</div>
                            <div class="stats-value">${stats.total}</div>
                        </div>
                        <div class="stats-card">
                            <div class="stats-title">✅ Wins</div>
                            <div class="stats-value" style="color: #00e676;">${stats.wins}</div>
                        </div>
                        <div class="stats-card">
                            <div class="stats-title">❌ Losses</div>
                            <div class="stats-value" style="color: #ff1744;">${stats.losses}</div>
                        </div>
                        <div class="stats-card">
                            <div class="stats-title">📈 Win Rate</div>
                            <div class="stats-win-rate">${stats.win_rate}%</div>
                        </div>
                    </div>
                `;
                
                let historicoHtml = `
                    <div class="history-card">
                        <div class="history-title">📜 Histórico de Sinais (${currentAtivo} - ${currentTimeframe})</div>
                `;
                
                const filtrados = historico.filter(h => h.ativo === currentAtivo && h.timeframe === currentTimeframe);
                
                if (filtrados.length === 0) {
                    historicoHtml += `<div style="text-align: center; padding: 20px; color: #8892b0;">Nenhum sinal registrado ainda</div>`;
                } else {
                    filtrados.slice().reverse().forEach(item => {
                        const confirmClass = item.confirmado === 'win' ? 'history-win' : (item.confirmado === 'loss' ? 'history-loss' : 'history-pending');
                        const confirmText = item.confirmado === 'win' ? 'WIN' : (item.confirmado === 'loss' ? 'LOSS' : 'Pendente');
                        
                        historicoHtml += `
                            <div class="history-item">
                                <div>
                                    <div class="history-sinal ${item.sinal === 'COMPRA' ? 'history-win' : 'history-loss'}">${item.sinal}</div>
                                    <div style="font-size: 0.7em; color: #8892b0;">${item.data}</div>
                                </div>
                                <div>Entry: ${item.entry}</div>
                                <div>Stop: ${item.stop_loss}</div>
                                <div>TP: ${item.take_profit}</div>
                                <div class="history-confirm ${confirmClass}">${confirmText}</div>
                            </div>
                        `;
                    });
                }
                
                historicoHtml += `</div>`;
                
                const conteudo = document.getElementById('conteudo');
                conteudo.innerHTML += statsHtml + historicoHtml;
                
            } catch (error) {
                console.log('Erro:', error);
            }
        }

        // Carregar análise inicial
        analisar();
    </script>
</body>
</html>
"""


# ============================================
# ENDPOINTS DA API
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
        resultado['ativo'] = symbol
        return resultado
    return {"error": "Não foi possível obter análise do TradingView"}

@app.post("/confirmar")
async def confirmar_sinal(sinal: dict):
    """Confirma um sinal como win ou loss"""
    historico = carregar_historico()
    
    # Adicionar ID único
    sinal['id'] = datetime.now().timestamp()
    sinal['ativo_nome'] = SYMBOL_CONFIG.get(sinal.get('simbolo', ''), {}).get('nome', sinal.get('nome'))
    
    historico.append(sinal)
    salvar_historico(historico)
    
    return {"status": "ok"}

@app.get("/estatisticas")
async def get_estatisticas(
    ativo: str = Query(None),
    timeframe: str = Query(None)
):
    """Retorna estatísticas de win/loss"""
    historico = carregar_historico()
    return calcular_estatisticas(historico, ativo, timeframe)

@app.get("/historico")
async def get_historico():
    """Retorna todo o histórico de sinais"""
    return carregar_historico()


# ============================================
# SERVIDOR
# ============================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Valverde Trade IA")
    print(f"📍 Acesse: http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
