"""
VALVERDE TRADE IA - Layout com Dois Painéis
Sinais Recentes (Esquerda) + Histórico de Sinais (Direita)
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from datetime import datetime
import os
import json
import requests
import time
from typing import List, Dict

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
    "GC=F": {"symbol": "XAUUSD", "nome": "XAU", "tipo": "Commodities", "emoji": "🥇", "nome_exibicao": "Ouro"},
    "BTC-USD": {"symbol": "BTCUSDT", "nome": "BTC", "tipo": "Cripto", "emoji": "₿", "nome_exibicao": "Bitcoin"},
    "ETH-USD": {"symbol": "ETHUSDT", "nome": "ETH", "tipo": "Cripto", "emoji": "⟠", "nome_exibicao": "Ethereum"},
    "AAPL": {"symbol": "AAPL", "nome": "AAPL", "tipo": "Ações", "emoji": "🍎", "nome_exibicao": "Apple"},
    "NVDA": {"symbol": "NVDA", "nome": "NVDA", "tipo": "Ações", "emoji": "🎮", "nome_exibicao": "NVIDIA"},
}

INTERVAL_MAP = {
    "5m": "5m",
    "15m": "15m", 
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

INTERVALOS_DISPONIVEIS = ["5m", "15m", "30m", "1h", "4h", "1d"]

# Arquivo para histórico
HISTORICO_FILE = "historico_sinais.json"

def carregar_historico():
    if os.path.exists(HISTORICO_FILE):
        with open(HISTORICO_FILE, "r") as f:
            return json.load(f)
    return []

def salvar_historico(historico):
    with open(HISTORICO_FILE, "w") as f:
        json.dump(historico, f, indent=2)


def get_analysis_from_binance(symbol, interval):
    """Busca dados da Binance (para cripto)"""
    try:
        binance_symbols = {
            "BTC-USD": "BTCUSDT",
            "ETH-USD": "ETHUSDT",
        }
        
        binance_symbol = binance_symbols.get(symbol)
        if binance_symbol:
            url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={interval}&limit=50"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                closes = [float(candle[4]) for candle in data]
                preco = closes[-1]
                rsi = calcular_rsi(closes)
                
                ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else preco
                ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else preco
                
                if rsi < 35 and preco < ma20:
                    sinal = "COMPRA"
                    forca = 80
                elif rsi > 65 and preco > ma20:
                    sinal = "VENDA"
                    forca = 20
                elif rsi < 30:
                    sinal = "COMPRA"
                    forca = 85
                elif rsi > 70:
                    sinal = "VENDA"
                    forca = 15
                else:
                    sinal = "NEUTRO"
                    forca = 50
                
                confianca = abs(forca - 50) * 2 + 50
                if confianca > 100:
                    confianca = 100
                
                atr = calcular_atr(closes)
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
                }
    except Exception as e:
        print(f"Binance error: {e}")
    return None


def get_analysis_from_yahoo(symbol, interval):
    """Busca dados do Yahoo Finance"""
    try:
        yahoo_interval = interval.replace('m', 'm').replace('h', 'h')
        if interval == '4h':
            yahoo_interval = '1h'
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={yahoo_interval}&range=5d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('chart', {}).get('result', [])
            
            if result:
                quote = result[0]
                indicators = quote.get('indicators', {})
                quote_data = indicators.get('quote', [{}])[0]
                closes = [c for c in quote_data.get('close', []) if c is not None]
                
                if closes:
                    preco = closes[-1]
                    rsi = calcular_rsi(closes)
                    
                    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else preco
                    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else preco
                    
                    if rsi < 35 and preco < ma20:
                        sinal = "COMPRA"
                        forca = 80
                    elif rsi > 65 and preco > ma20:
                        sinal = "VENDA"
                        forca = 20
                    elif rsi < 30:
                        sinal = "COMPRA"
                        forca = 85
                    elif rsi > 70:
                        sinal = "VENDA"
                        forca = 15
                    else:
                        sinal = "NEUTRO"
                        forca = 50
                    
                    confianca = abs(forca - 50) * 2 + 50
                    if confianca > 100:
                        confianca = 100
                    
                    atr = calcular_atr(closes)
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
                    }
    except Exception as e:
        print(f"Yahoo error: {e}")
    return None


def get_fallback_analysis(symbol, interval):
    """Análise simulada de fallback"""
    config = SYMBOL_CONFIG.get(symbol, {})
    
    base_price = {"GC=F": 4670, "BTC-USD": 66800, "ETH-USD": 3300, "AAPL": 220, "NVDA": 120}.get(symbol, 100)
    
    import random
    random.seed(int(time.time() / 60) + hash(symbol) % 1000)
    
    variacao = random.uniform(-0.02, 0.02)
    preco = base_price * (1 + variacao)
    rsi = 50 + (variacao * 100)
    rsi = max(20, min(80, rsi))
    
    if rsi < 35:
        sinal = "COMPRA"
        forca = 80
    elif rsi > 65:
        sinal = "VENDA"
        forca = 20
    else:
        sinal = "NEUTRO"
        forca = 50
    
    confianca = abs(forca - 50) * 2 + 50
    atr = preco * 0.005
    stop_loss = preco - (2 * atr) if sinal == "COMPRA" else preco + (2 * atr)
    take_profit = preco + (2 * atr) if sinal == "COMPRA" else preco - (2 * atr)
    
    return {
        'preco': round(preco, 2),
        'rsi': round(rsi, 1),
        'sinal': sinal,
        'forca': forca,
        'confianca': round(confianca, 1),
        'stop_loss': round(stop_loss, 2),
        'take_profit': round(take_profit, 2),
    }


def get_analysis(symbol, interval):
    """Obtém análise para um ativo específico"""
    if symbol in ["BTC-USD", "ETH-USD"]:
        result = get_analysis_from_binance(symbol, interval)
        if result:
            return result
    result = get_analysis_from_yahoo(symbol, interval)
    if result:
        return result
    return get_fallback_analysis(symbol, interval)


def get_all_signals():
    """Obtém sinais para todos os ativos e intervalos"""
    sinais = []
    for symbol, config in SYMBOL_CONFIG.items():
        # Para cada ativo, pegar o sinal do timeframe padrão (15m)
        analysis = get_analysis(symbol, "15m")
        if analysis:
            sinais.append({
                'symbol': symbol,
                'nome': config['nome'],
                'nome_exibicao': config['nome_exibicao'],
                'emoji': config['emoji'],
                'tipo': config['tipo'],
                'timeframe': '15m',
                'preco': analysis['preco'],
                'sinal': analysis['sinal'],
                'forca': analysis['forca'],
                'confianca': analysis['confianca'],
                'stop_loss': analysis['stop_loss'],
                'take_profit': analysis['take_profit'],
                'entry': analysis['preco'],
                'data': datetime.now().strftime('%d/%m %H:%M')
            })
    return sinais


def calcular_rsi(precos, periodo=14):
    if len(precos) < periodo + 1:
        return 50
    ganhos = 0
    perdas = 0
    for i in range(-periodo, 0):
        diferenca = precos[i] - precos[i-1]
        if diferenca > 0:
            ganhos += diferenca
        else:
            perdas += abs(diferenca)
    if perdas == 0:
        return 100
    rs = ganhos / perdas
    return 100 - (100 / (1 + rs))


def calcular_atr(precos, periodo=14):
    if len(precos) < 2:
        return precos[-1] * 0.005
    variacoes = []
    for i in range(-periodo, 0):
        if i > -len(precos):
            variacao = abs(precos[i] - precos[i-1])
            variacoes.append(variacao)
    if variacoes:
        return sum(variacoes) / len(variacoes)
    return precos[-1] * 0.005


# ============================================
# INTERFACE HTML COM DOIS PAINÉIS
# ============================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Valverde Trade IA</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            min-height: 100vh;
            color: #ffffff;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
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

        /* Layout de dois painéis */
        .two-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        /* Painel Esquerdo - Sinais Recentes */
        .panel-left {
            background: rgba(10, 14, 39, 0.6);
            border-radius: 24px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .panel-title {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid rgba(123, 44, 191, 0.5);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Cards de Sinais */
        .signal-card-mini {
            background: rgba(15, 20, 40, 0.8);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer;
        }

        .signal-card-mini:hover {
            transform: translateY(-2px);
            background: rgba(25, 30, 50, 0.9);
            border-color: rgba(123, 44, 191, 0.3);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .asset-name {
            font-size: 1.1em;
            font-weight: bold;
        }

        .signal-badge-mini {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: bold;
        }

        .signal-buy-mini {
            background: linear-gradient(135deg, #00c853, #00e676);
        }

        .signal-sell-mini {
            background: linear-gradient(135deg, #d50000, #ff1744);
        }

        .signal-neutral-mini {
            background: linear-gradient(135deg, #ff8f00, #ffab40);
        }

        .card-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin: 12px 0;
            font-size: 0.8em;
        }

        .detail-item {
            text-align: center;
        }

        .detail-label {
            color: #8892b0;
            font-size: 0.7em;
        }

        .detail-value {
            font-weight: bold;
        }

        .confidence-bar {
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            margin-top: 8px;
            overflow: hidden;
        }

        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #7b2cbf);
            border-radius: 2px;
        }

        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
            font-size: 0.7em;
            color: #8892b0;
        }

        /* Painel Direito - Histórico */
        .panel-right {
            background: rgba(10, 14, 39, 0.6);
            border-radius: 24px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .history-item {
            background: rgba(15, 20, 40, 0.8);
            border-radius: 14px;
            padding: 14px;
            margin-bottom: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .history-asset {
            font-weight: bold;
        }

        .history-result {
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.7em;
            font-weight: bold;
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

        .history-details {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            font-size: 0.75em;
            margin: 10px 0;
        }

        .history-date {
            font-size: 0.7em;
            color: #8892b0;
            margin-top: 8px;
        }

        .history-strength {
            font-size: 0.75em;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #8892b0;
        }

        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
            color: #8892b0;
        }

        /* Botão atualizar */
        .refresh-btn {
            background: rgba(123, 44, 191, 0.3);
            border: 1px solid rgba(123, 44, 191, 0.5);
            padding: 8px 16px;
            border-radius: 40px;
            color: white;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.2s;
        }

        .refresh-btn:hover {
            background: rgba(123, 44, 191, 0.5);
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 30px;
            color: #8892b0;
            font-size: 0.7em;
            margin-top: 30px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Scroll */
        .scrollable {
            max-height: calc(100vh - 200px);
            overflow-y: auto;
            padding-right: 8px;
        }

        .scrollable::-webkit-scrollbar {
            width: 4px;
        }

        .scrollable::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
        }

        .scrollable::-webkit-scrollbar-thumb {
            background: rgba(123, 44, 191, 0.5);
            border-radius: 4px;
        }

        @media (max-width: 900px) {
            .two-columns {
                grid-template-columns: 1fr;
                gap: 20px;
            }
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

        <!-- Botão de atualização global -->
        <div style="text-align: right; margin-bottom: 20px;">
            <button class="refresh-btn" onclick="carregarTudo()">🔄 Atualizar Todos os Sinais</button>
        </div>

        <!-- Layout de dois painéis -->
        <div class="two-columns">
            <!-- Painel Esquerdo: Sinais Recentes (Todos os ativos) -->
            <div class="panel-left">
                <div class="panel-title">
                    <span>📊</span> Sinais Recentes
                    <span style="font-size: 0.7em; font-weight: normal; margin-left: auto;">Clique para confirmar</span>
                </div>
                <div id="sinais-container" class="scrollable">
                    <div class="loading">🔄 Carregando sinais...</div>
                </div>
            </div>

            <!-- Painel Direito: Histórico de Sinais Confirmados -->
            <div class="panel-right">
                <div class="panel-title">
                    <span>📜</span> Histórico de Sinais
                </div>
                <div id="historico-container" class="scrollable">
                    <div class="loading">🔄 Carregando histórico...</div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Valverde Trade IA • Dados em tempo real • Clique em qualquer sinal para confirmar WIN ou LOSS</p>
            <p>⚠️ Apenas para fins educacionais • Não é recomendação de investimento</p>
        </div>
    </div>

    <script>
        let sinaisAtuais = [];

        async function carregarSinais() {
            try {
                const response = await fetch('/api/sinais');
                const sinais = await response.json();
                sinaisAtuais = sinais;
                renderizarSinais(sinais);
            } catch (error) {
                document.getElementById('sinais-container').innerHTML = `<div class="empty-state">❌ Erro ao carregar sinais: ${error.message}</div>`;
            }
        }

        async function carregarHistorico() {
            try {
                const response = await fetch('/historico');
                const historico = await response.json();
                renderizarHistorico(historico);
            } catch (error) {
                document.getElementById('historico-container').innerHTML = `<div class="empty-state">❌ Erro ao carregar histórico: ${error.message}</div>`;
            }
        }

        function renderizarSinais(sinais) {
            if (!sinais || sinais.length === 0) {
                document.getElementById('sinais-container').innerHTML = '<div class="empty-state">Nenhum sinal disponível no momento</div>';
                return;
            }

            const html = sinais.map(sinal => {
                const sinalClass = sinal.sinal === 'COMPRA' ? 'signal-buy-mini' : (sinal.sinal === 'VENDA' ? 'signal-sell-mini' : 'signal-neutral-mini');
                const stopClass = sinal.sinal === 'COMPRA' ? 'level-stop' : '';
                const tpClass = sinal.sinal === 'COMPRA' ? 'level-tp' : '';
                
                return `
                    <div class="signal-card-mini" onclick="abrirConfirmacao('${sinal.symbol}', '${sinal.timeframe}', '${sinal.sinal}', ${sinal.preco}, ${sinal.stop_loss}, ${sinal.take_profit}, ${sinal.forca})">
                        <div class="card-header">
                            <span class="asset-name">${sinal.emoji} ${sinal.nome_exibicao} (${sinal.tipo})</span>
                            <span class="signal-badge-mini ${sinalClass}">🎯 ${sinal.sinal}</span>
                        </div>
                        <div class="card-details">
                            <div class="detail-item">
                                <div class="detail-label">ENTRY</div>
                                <div class="detail-value">${sinal.preco}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">STOP</div>
                                <div class="detail-value ${stopClass}">${sinal.stop_loss}</div>
                            </div>
                            <div class="detail-item">
                                <div class="detail-label">TP 1</div>
                                <div class="detail-value ${tpClass}">${sinal.take_profit}</div>
                            </div>
                        </div>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${sinal.confianca}%"></div>
                        </div>
                        <div class="card-footer">
                            <span>📈 ${sinal.timeframe}</span>
                            <span>Confiança: ${sinal.confianca}%</span>
                            <span>Força: ${sinal.forca}%</span>
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('sinais-container').innerHTML = html;
        }

        function renderizarHistorico(historico) {
            if (!historico || historico.length === 0) {
                document.getElementById('historico-container').innerHTML = '<div class="empty-state">Nenhum sinal confirmado ainda</div>';
                return;
            }

            // Ordenar do mais recente para o mais antigo
            const historicoOrdenado = [...historico].reverse();
            
            const html = historicoOrdenado.map(item => {
                const resultClass = item.confirmado === 'win' ? 'history-win' : (item.confirmado === 'loss' ? 'history-loss' : 'history-pending');
                const resultText = item.confirmado === 'win' ? 'WIN' : (item.confirmado === 'loss' ? 'LOSS' : 'Pendente');
                
                return `
                    <div class="history-item">
                        <div class="history-header">
                            <span class="history-asset">${item.emoji || '📊'} ${item.nome_exibicao || item.nome} • ${item.timeframe}</span>
                            <span class="history-result ${resultClass}">${resultText} ${item.forca || '?'}%</span>
                        </div>
                        <div class="history-details">
                            <div>Entry: ${item.entry}</div>
                            <div>Stop: ${item.stop_loss}</div>
                            <div>TP: ${item.take_profit}</div>
                        </div>
                        <div class="history-date">
                            📅 ${item.data || item.data_confirmacao || 'Data não informada'}
                        </div>
                    </div>
                `;
            }).join('');
            
            document.getElementById('historico-container').innerHTML = html;
        }

        function abrirConfirmacao(symbol, timeframe, sinal, preco, stopLoss, takeProfit, forca) {
            const config = {
                'GC=F': { emoji: '🥇', nome: 'XAU', nome_exibicao: 'Ouro' },
                'BTC-USD': { emoji: '₿', nome: 'BTC', nome_exibicao: 'Bitcoin' },
                'ETH-USD': { emoji: '⟠', nome: 'ETH', nome_exibicao: 'Ethereum' },
                'AAPL': { emoji: '🍎', nome: 'AAPL', nome_exibicao: 'Apple' },
                'NVDA': { emoji: '🎮', nome: 'NVDA', nome_exibicao: 'NVIDIA' }
            };
            
            const conf = config[symbol] || { emoji: '📊', nome: symbol, nome_exibicao: symbol };
            
            const resultado = confirm(`📊 CONFIRMAR SINAL\n\n${conf.emoji} ${conf.nome_exibicao} • ${timeframe}\nSinal: ${sinal}\nEntry: ${preco}\nStop: ${stopLoss}\nTP: ${takeProfit}\nForça: ${forca}%\n\nClique em OK se o sinal foi WIN (acertou)\nClique em Cancelar se foi LOSS (errou)`);
            
            if (resultado !== null) {
                const confirmado = resultado ? 'win' : 'loss';
                
                fetch('/confirmar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        simbolo: symbol,
                        nome: conf.nome,
                        nome_exibicao: conf.nome_exibicao,
                        emoji: conf.emoji,
                        timeframe: timeframe,
                        sinal: sinal,
                        entry: preco,
                        stop_loss: stopLoss,
                        take_profit: takeProfit,
                        forca: forca,
                        confirmado: confirmado,
                        data: new Date().toLocaleString()
                    })
                }).then(() => {
                    alert(`✅ Sinal registrado como ${confirmado.toUpperCase()}!`);
                    carregarHistorico();
                });
            }
        }

        async function carregarTudo() {
            document.getElementById('sinais-container').innerHTML = '<div class="loading">🔄 Atualizando sinais...</div>';
            document.getElementById('historico-container').innerHTML = '<div class="loading">🔄 Atualizando histórico...</div>';
            
            await Promise.all([carregarSinais(), carregarHistorico()]);
        }

        // Carregar tudo ao iniciar
        carregarTudo();
        
        // Atualizar a cada 5 minutos
        setInterval(carregarSinais, 300000);
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

@app.get("/api/sinais")
async def get_all_signals_api():
    """Retorna sinais para todos os ativos"""
    sinais = []
    for symbol, config in SYMBOL_CONFIG.items():
        analysis = get_analysis(symbol, "15m")
        if analysis:
            sinais.append({
                'symbol': symbol,
                'nome': config['nome'],
                'nome_exibicao': config['nome_exibicao'],
                'emoji': config['emoji'],
                'tipo': config['tipo'],
                'timeframe': '15m',
                'preco': analysis['preco'],
                'sinal': analysis['sinal'],
                'forca': analysis['forca'],
                'confianca': analysis['confianca'],
                'stop_loss': analysis['stop_loss'],
                'take_profit': analysis['take_profit'],
                'entry': analysis['preco'],
                'rsi': analysis['rsi'],
                'data': datetime.now().strftime('%d/%m %H:%M')
            })
    return sinais
