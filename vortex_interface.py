# ============================================================
# HTML COM CÓDIGO DOS ATIVOS
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
.logo small{font-size:0.7rem;color:var(--muted)}
.refresh-btn{background:transparent;border:1px solid var(--bord2);color:var(--text);cursor:pointer;padding:5px 12px;border-radius:6px;font-family:var(--mono);font-size:0.75rem}
.refresh-btn:hover{border-color:var(--accent);color:var(--accent)}
.tabs{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:15px}
.tab{padding:5px 12px;border-radius:20px;cursor:pointer;border:1px solid var(--border);background:transparent;color:var(--muted);font-size:0.75rem;transition:all 0.2s}
.tab:hover{border-color:var(--bord2);color:var(--text)}
.tab.active{background:rgba(56,189,248,.12);border-color:var(--accent);color:var(--accent)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.panel{background:var(--bg2);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.panel-head{padding:12px 16px;border-bottom:1px solid var(--border);background:var(--bg3);display:flex;justify-content:space-between;align-items:center}
.panel-title{font-family:var(--mono);font-size:0.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
.panel-count{background:rgba(56,189,248,.1);padding:2px 8px;border-radius:12px;font-family:var(--mono);font-size:0.65rem;color:var(--accent)}
.panel-body{padding:12px;max-height:80vh;overflow-y:auto}
.panel-body::-webkit-scrollbar{width:4px}
.panel-body::-webkit-scrollbar-thumb{background:var(--bord2);border-radius:4px}
.sig-card{background:var(--bg3);border:1px solid var(--border);border-radius:11px;padding:12px;margin-bottom:9px;cursor:pointer;transition:all 0.2s}
.sig-card:hover{transform:translateY(-1px);border-color:var(--bord2)}
.sig-card.buy{border-left:3px solid var(--buy)}
.sig-card.sell{border-left:3px solid var(--sell)}
.sig-card.neutral{border-left:3px solid var(--warn)}
.sig-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.sig-info{flex:1}
.sig-name{font-weight:600;font-size:0.9rem;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sig-code{font-family:var(--mono);font-size:0.6rem;background:rgba(255,255,255,0.05);padding:2px 6px;border-radius:4px;color:var(--accent)}
.sig-type{font-size:0.6rem;color:var(--muted);margin-top:3px}
.badge{padding:3px 9px;border-radius:5px;font-size:0.7rem;font-weight:700;font-family:var(--mono)}
.badge.buy{background:rgba(34,197,94,.14);color:var(--buy);border:1px solid rgba(34,197,94,.3)}
.badge.sell{background:rgba(239,68,68,.14);color:var(--sell);border:1px solid rgba(239,68,68,.3)}
.badge.neutral{background:rgba(245,158,11,.14);color:var(--warn);border:1px solid rgba(245,158,11,.3)}
.sig-levels{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0;background:rgba(0,0,0,0.2);border-radius:8px;padding:8px}
.level{text-align:center}
.level-label{font-size:0.55rem;color:var(--muted);font-family:var(--mono);text-transform:uppercase}
.level-value{font-family:var(--mono);font-size:0.75rem;font-weight:700;margin-top:2px}
.level-value.entry{color:var(--accent)}
.level-value.stop{color:var(--sell)}
.level-value.tp{color:var(--buy)}
.sig-metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}
.metric{background:rgba(0,0,0,0.2);border-radius:6px;padding:5px;text-align:center}
.metric-label{font-size:0.55rem;color:var(--muted);font-family:var(--mono)}
.metric-value{font-family:var(--mono);font-size:0.7rem;font-weight:700;margin-top:2px}
.sig-indicators{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0}
.indicator{font-family:var(--mono);font-size:0.55rem;background:rgba(255,255,255,0.03);padding:2px 6px;border-radius:4px;border:1px solid var(--border)}
.indicator span{color:var(--text)}
.sig-time{margin-top:8px;padding-top:6px;border-top:1px solid var(--border);font-size:0.6rem;color:var(--muted);display:flex;align-items:center;gap:8px}
.sig-expiry{font-size:0.6rem;color:var(--warn);margin-top:4px;display:flex;align-items:center;gap:5px}
.hist-item{background:var(--bg3);border:1px solid var(--border);border-radius:9px;padding:10px;margin-bottom:7px}
.hist-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.hist-name{font-weight:600;font-size:0.8rem}
.hist-code{font-family:var(--mono);font-size:0.55rem;background:rgba(255,255,255,0.05);padding:1px 4px;border-radius:3px;margin-left:5px}
.hist-result{padding:2px 8px;border-radius:4px;font-size:0.6rem;font-weight:700}
.hist-result.win{background:rgba(34,197,94,.1);color:var(--buy)}
.hist-result.loss{background:rgba(239,68,68,.1);color:var(--sell)}
.hist-result.pend{background:rgba(245,158,11,.1);color:var(--warn)}
.hist-levels{font-size:0.65rem;color:var(--muted);margin:5px 0;display:flex;flex-wrap:wrap;gap:10px}
.hist-levels span{color:var(--text)}
.hist-time{font-size:0.55rem;color:var(--muted);margin-top:4px;display:flex;align-items:center;gap:8px}
.empty{text-align:center;padding:40px;color:var(--muted);font-size:0.8rem}
</style>
</head>
<body>
<div class="wrap">
<div class="header">
<div class="logo">VALVERDE TRADE IA <small>v3.0 · 22 ativos · MTF</small></div>
<button class="refresh-btn" onclick="carregarTudo()">↻ ATUALIZAR</button>
</div>
<div class="tabs">
<button class="tab active" onclick="setTab(this,'Todos')">📊 Todos (22)</button>
<button class="tab" onclick="setTab(this,'Forex')">💱 Forex (7)</button>
<button class="tab" onclick="setTab(this,'Commodities')">🛢 Commodities (6)</button>
<button class="tab" onclick="setTab(this,'Cripto')">₿ Cripto (2)</button>
<button class="tab" onclick="setTab(this,'Índices')">📈 Índices (6)</button>
<button class="tab" onclick="setTab(this,'Ações')">🍎 Ações (2)</button>
</div>
<div class="grid">
<div class="panel">
<div class="panel-head">
<span class="panel-title">🔥 SINAIS ATIVOS · 15 MINUTOS</span>
<span class="panel-count" id="count-sinais">—</span>
</div>
<div class="panel-body" id="sinais-container">
<div class="empty">⟳ Carregando sinais...</div>
</div>
</div>
<div class="panel">
<div class="panel-head">
<span class="panel-title">📋 HISTÓRICO DE SINAIS</span>
<span class="panel-count" id="count-hist">—</span>
</div>
<div class="panel-body" id="historico-container">
<div class="empty">⟳ Carregando histórico...</div>
</div>
</div>
</div>
</div>

<script>
let todosSinais = [];
let catAtual = 'Todos';

function fmtPreco(v, tipo) {
    if (v == null) return '—';
    let n = Number(v);
    if (tipo === 'Forex') return n.toFixed(5);
    if (n > 10000) return n.toLocaleString('pt-BR', {maximumFractionDigits: 0});
    if (n > 100) return n.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    if (n > 1) return n.toFixed(3);
    return n.toFixed(5);
}

function renderSinais() {
    let lista = catAtual === 'Todos' ? todosSinais : todosSinais.filter(s => s.tipo === catAtual);
    document.getElementById('count-sinais').innerHTML = lista.length;
    
    if (lista.length === 0) {
        document.getElementById('sinais-container').innerHTML = '<div class="empty">📡 Nenhum sinal ativo no momento</div>';
        return;
    }
    
    let html = lista.map(s => {
        const sinalClass = s.sinal === 'COMPRA' ? 'buy' : (s.sinal === 'VENDA' ? 'sell' : 'neutral');
        const sinalLabel = s.sinal === 'COMPRA' ? '▲ COMPRA' : (s.sinal === 'VENDA' ? '▼ VENDA' : '● NEUTRO');
        const mhS = s.macd_hist >= 0 ? '+' : '';
        const mhFmt = Math.abs(s.macd_hist) < 0.000001 ? s.macd_hist.toExponential(2) : Number(s.macd_hist).toFixed(6);
        
        return `
        <div class="sig-card ${sinalClass}" onclick='confirmarSinal(${JSON.stringify(s)})'>
            <div class="sig-top">
                <div class="sig-info">
                    <div class="sig-name">
                        <span>${s.emoji}</span>
                        <span>${s.nome_exibicao}</span>
                        <span class="sig-code">${s.nome}</span>
                        ${s.fonte === 'simulado' ? '<span style="font-size:0.55rem;color:var(--sim)">⚠ SIM</span>' : ''}
                    </div>
                    <div class="sig-type">${s.tipo} · Timeframe: ${s.timeframe}</div>
                </div>
                <span class="badge ${sinalClass}">${sinalLabel}</span>
            </div>
            
            <div class="sig-levels">
                <div class="level">
                    <div class="level-label">ENTRY</div>
                    <div class="level-value entry">${fmtPreco(s.preco, s.tipo)}</div>
                </div>
                <div class="level">
                    <div class="level-label">STOP LOSS</div>
                    <div class="level-value stop">${fmtPreco(s.stop_loss, s.tipo)}</div>
                </div>
                <div class="level">
                    <div class="level-label">TAKE PROFIT</div>
                    <div class="level-value tp">${fmtPreco(s.take_profit, s.tipo)}</div>
                </div>
            </div>
            
            <div class="sig-metrics">
                <div class="metric">
                    <div class="metric-label">SCORE</div>
                    <div class="metric-value">${s.score}/100</div>
                </div>
                <div class="metric">
                    <div class="metric-label">CONFIANÇA</div>
                    <div class="metric-value">${s.confianca}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">FORÇA</div>
                    <div class="metric-value">${s.forca}%</div>
                </div>
            </div>
            
            <div class="sig-indicators">
                <div class="indicator">RSI <span>${s.rsi}</span></div>
                <div class="indicator">MACD <span>${mhS}${mhFmt}</span></div>
                <div class="indicator">Volume <span>${s.volume_ratio}×</span></div>
                <div class="indicator">Tendência <span>${s.tendencia}</span></div>
                <div class="indicator">${s.mtf_ok ? '✓' : '✗'} MTF</div>
            </div>
            
            <div class="sig-time">
                <span>🕐 Confirmado:</span>
                <strong>${s.horario_confirmacao || '--:--:--'}</strong>
                <span>${s.data_completa || s.data || ''}</span>
            </div>
            
            <div class="sig-expiry">
                <span>⏱ Expira em:</span>
                <strong class="timer-${s.symbol.replace(/[^a-zA-Z0-9]/g, '_')}" data-expiry="${s.expiracao}">${s.tempo_restante_formatado}</strong>
                <span>(até ${s.expiracao})</span>
            </div>
        </div>`;
    }).join('');
    
    document.getElementById('sinais-container').innerHTML = html;
    
    // Iniciar contadores regressivos
    iniciarContadores();
}

function iniciarContadores() {
    setInterval(() => {
        document.querySelectorAll('[data-expiry]').forEach(el => {
            const expiryTime = el.getAttribute('data-expiry');
            if (expiryTime) {
                const now = new Date();
                const [hours, minutes, seconds] = expiryTime.split(':');
                const expiry = new Date();
                expiry.setHours(parseInt(hours), parseInt(minutes), parseInt(seconds || 0));
                
                const diff = expiry - now;
                if (diff <= 0) {
                    el.textContent = 'Expirado';
                    el.style.color = '#ef4444';
                } else {
                    const mins = Math.floor(diff / 60000);
                    const secs = Math.floor((diff % 60000) / 1000);
                    el.textContent = `${mins}min ${secs}s`;
                }
            }
        });
    }, 1000);
}

function renderHistorico(hist) {
    document.getElementById('count-hist').innerHTML = hist.length;
    
    if (hist.length === 0) {
        document.getElementById('historico-container').innerHTML = '<div class="empty">📋 Nenhum sinal no histórico<br><small>Clique em um sinal para registrar WIN/LOSS</small></div>';
        return;
    }
    
    let html = hist.slice().reverse().map(h => {
        const resultClass = h.confirmado === 'win' ? 'win' : (h.confirmado === 'loss' ? 'loss' : 'pend');
        const resultText = h.confirmado === 'win' ? '✓ WIN' : (h.confirmado === 'loss' ? '✗ LOSS' : '◌ Pendente');
        
        return `
        <div class="hist-item">
            <div class="hist-header">
                <div>
                    <span class="hist-name">${h.emoji} ${h.nome_exibicao}</span>
                    <span class="hist-code">${h.nome}</span>
                </div>
                <span class="hist-result ${resultClass}">${resultText}</span>
            </div>
            <div class="hist-levels">
                <span>Entry: ${fmtPreco(h.entry, h.tipo)}</span>
                <span>SL: ${fmtPreco(h.stop_loss, h.tipo)}</span>
                <span>TP: ${fmtPreco(h.take_profit, h.tipo)}</span>
                <span>Score: ${h.score || '—'}</span>
                <span>Conf: ${h.confianca || '—'}%</span>
            </div>
            <div class="hist-time">
                <span>🕐 Confirmado: <strong>${h.horario_confirmacao || '--:--:--'}</strong></span>
                <span>📅 ${h.data_completa || h.data_confirmacao || h.data || '—'}</span>
                ${h.status === 'expirado' ? '<span style="color:var(--warn)">⚠ Expirado automaticamente</span>' : ''}
            </div>
        </div>`;
    }).join('');
    
    document.getElementById('historico-container').innerHTML = html;
}

async function confirmarSinal(sinal) {
    const res = confirm(
        `📊 CONFIRMAR RESULTADO\n\n` +
        `${sinal.emoji} ${sinal.nome_exibicao} (${sinal.nome})\n` +
        `Sinal: ${sinal.sinal}\n` +
        `Score: ${sinal.score}/100 | Confiança: ${sinal.confianca}%\n` +
        `Entry: ${fmtPreco(sinal.preco, sinal.tipo)}\n` +
        `Stop: ${fmtPreco(sinal.stop_loss, sinal.tipo)}\n` +
        `TP: ${fmtPreco(sinal.take_profit, sinal.tipo)}\n\n` +
        `OK = WIN  |  Cancelar = LOSS`
    );
    
    if (res !== null) {
        const confirmacao = {
            ...sinal,
            confirmado: res ? 'win' : 'loss',
            data_confirmacao: new Date().toLocaleString('pt-BR'),
            horario_confirmacao_manual: new Date().toLocaleTimeString('pt-BR')
        };
        
        await fetch('/confirmar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(confirmacao)
        });
        
        carregarHistorico();
    }
}

async function carregarSinais() {
    try {
        const r = await fetch('/api/sinais');
        todosSinais = await r.json();
        renderSinais();
        document.getElementById('last-update').innerHTML = new Date().toLocaleTimeString('pt-BR');
    } catch(e) {
        console.error('Erro ao carregar sinais:', e);
    }
}

async function carregarHistorico() {
    try {
        const r = await fetch('/historico');
        const hist = await r.json();
        renderHistorico(hist);
    } catch(e) {
        console.error('Erro ao carregar histórico:', e);
    }
}

function setTab(el, cat) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    catAtual = cat;
    renderSinais();
}

async function carregarTudo() {
    await Promise.all([carregarSinais(), carregarHistorico()]);
}

// Inicializar
carregarTudo();
setInterval(carregarSinais, 300000); // Atualizar a cada 5 minutos
</script>
</body>
</html>"""

@app.get("/")
async def root():
    return HTMLResponse(content=HTML_PAGE)
