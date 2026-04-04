# ============================================================
# FUNÇÃO MODIFICADA PARA ARMAZENAR HORÁRIO DE CONFIRMAÇÃO
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

# ============================================================
# HTML MODIFICADO - MOSTRANDO HORÁRIO DE CONFIRMAÇÃO
# ============================================================

# Adicione este CSS ao HTML_PAGE
additional_css = """
/* Estilos para horário de confirmação */
.sig-time {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    padding-top: 6px;
    border-top: 1px solid var(--border);
    font-family: var(--mono);
    font-size: .58rem;
    color: var(--muted);
}
.sig-time .time-badge {
    background: rgba(56, 189, 248, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--accent);
}
.sig-time .confirm-time {
    color: var(--text);
}
.sig-expiry {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: .58rem;
    color: var(--warn);
}
.sig-expiry .expiry-timer {
    font-weight: 700;
    color: var(--warn);
}
.hist-time {
    font-family: var(--mono);
    font-size: .55rem;
    color: var(--muted);
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.hist-time .confirm-badge {
    background: rgba(34, 197, 94, 0.1);
    padding: 1px 5px;
    border-radius: 3px;
    color: var(--buy);
}
"""

# Modifique a função renderSinais no JavaScript para incluir horário
def get_modified_js():
    return """
function renderSinais(sinais) {
  const list = catAtual==='Todos' ? sinais : sinais.filter(s=>s.tipo===catAtual);
  document.getElementById('count-sinais').textContent = list.length + ' ativos';
  const el = document.getElementById('sinais-container');
  if (!list.length){
    el.innerHTML='<div class="empty"><div class="ico">📡</div>Sem sinais para esta categoria</div>';
    return;
  }
  el.innerHTML = list.map(s=>{
    const cls  = s.sinal==='COMPRA'?'buy':s.sinal==='VENDA'?'sell':'neutral';
    const sc   = scoreClass(s.score);
    const mhS  = s.macd_hist>=0?'+':'';
    const vcol = s.volume_ratio>=1.2?'color:var(--buy)':s.volume_ratio<0.9?'color:var(--sell)':'';
    const sim  = s.fonte==='simulado'?`<span class="badge sim">SIM</span>`:'';
    const fp   = v => fmtPreco(v,s.tipo);
    const sinalLabel = s.sinal==='COMPRA'?'▲ COMPRA':s.sinal==='VENDA'?'▼ VENDA':'— NEUTRO';
    const mhFmt = Math.abs(s.macd_hist)<0.000001
      ? s.macd_hist.toExponential(2)
      : Number(s.macd_hist).toFixed(6);

    return `
    <div class="sig-card ${cls}" onclick='abrirConfirmacao(${JSON.stringify(s)})'>
      <div class="sig-top">
        <div class="sig-asset">
          <span class="sig-emoji">${s.emoji}</span>
          <div>
            <div class="sig-name">${s.nome_exibicao} ${sim}</div>
            <div class="sig-sub">${s.tipo} · ${s.nome} · ${s.timeframe}</div>
          </div>
        </div>
        <span class="badge ${cls}">${sinalLabel}</span>
      </div>

      <div class="sig-levels">
        <div class="level"><div class="lbl">Entry</div><div class="val entry">${fp(s.preco)}</div></div>
        <div class="level"><div class="lbl">Stop</div><div class="val stop">${fp(s.stop_loss)}</div></div>
        <div class="level"><div class="lbl">TP</div><div class="val tp">${fp(s.take_profit)}</div></div>
      </div>

      <div class="metrics">
        <div class="mbox">
          <div class="mlbl">Score</div>
          <div class="mbar-w"><div class="mbar b-score ${sc}" style="width:${s.score}%"></div></div>
          <div class="mval">${s.score}/100</div>
        </div>
        <div class="mbox">
          <div class="mlbl">Confiança</div>
          <div class="mbar-w"><div class="mbar b-conf" style="width:${s.confianca}%"></div></div>
          <div class="mval">${s.confianca}%</div>
        </div>
        <div class="mbox">
          <div class="mlbl">Força</div>
          <div class="mbar-w"><div class="mbar b-forca" style="width:${s.forca}%"></div></div>
          <div class="mval">${s.forca}%</div>
        </div>
      </div>

      <div class="ind-row">
        <span class="chip">RSI <span>${s.rsi}</span></span>
        <span class="chip">MACD <span>${mhS}${mhFmt}</span></span>
        <span class="chip">Vol <span style="${vcol}">${s.volume_ratio}×</span></span>
        <span class="chip">Tend <span>${s.tendencia}</span></span>
        <span class="chip ${s.mtf_ok?'mtf-ok':'mtf-fail'}">${s.mtf_ok?'✓':'✗'} MTF</span>
      </div>

      <div class="sig-time">
        <span>🕐 Confirmado:</span>
        <span class="time-badge">${s.horario_confirmacao || s.data.split(' ')[1] || '--:--:--'}</span>
        <span class="confirm-time">${s.data_completa || s.data}</span>
      </div>

      <div class="sig-expiry">
        <span>⏱ Expira em:</span>
        <span class="expiry-timer" data-expiry="${s.expiracao}">${s.tempo_restante_formatado}</span>
        <span>(${s.expiracao})</span>
      </div>
    </div>`;
  }).join('');
}

function renderHistorico(hist) {
  const el = document.getElementById('historico-container');
  document.getElementById('count-hist').textContent = hist.length + ' registros';
  if (!hist.length){
    el.innerHTML='<div class="empty"><div class="ico">📋</div>Nenhum sinal confirmado ainda<br><small>Clique em um card para registrar WIN/LOSS</small></div>';
    return;
  }
  el.innerHTML=[...hist].reverse().map(h=>{
    const rc=h.confirmado==='win'?'win':h.confirmado==='loss'?'loss':'pend';
    const rt=h.confirmado==='win'?'✓ WIN':h.confirmado==='loss'?'✗ LOSS':'◌ Pend';
    const fp=v=>fmtPreco(v,h.tipo||'');
    const horarioConfirm = h.horario_confirmacao || (h.data_confirmacao ? h.data_confirmacao.split(' ')[1] : (h.data ? h.data.split(' ')[1] : '--:--'));
    
    return `
    <div class="hist-item">
      <div class="hist-top">
        <div><span class="hist-asset">${h.emoji||'📊'} ${h.nome_exibicao||h.nome}</span>
          <span class="hist-tf">${h.timeframe} · ${h.sinal}</span></div>
        <span class="hist-res ${rc}">${rt}</span>
      </div>
      <div class="hist-lvl">
        Entry:<span>${fp(h.entry)}</span>
        Stop:<span>${fp(h.stop_loss)}</span>
        TP:<span>${fp(h.take_profit)}</span>
        Score:<span>${h.score||'—'}</span>
        Conf:<span>${h.confianca||'—'}%</span>
        Força:<span>${h.forca||'—'}%</span>
      </div>
      <div class="hist-time">
        <span>🕐 Confirmado:</span>
        <span class="confirm-badge">${horarioConfirm}</span>
        <span>${h.data_completa || h.data_confirmacao || h.data || '—'}</span>
        ${h.status === 'expirado' ? '<span style="color:var(--warn)">⚠ Expirado após 15min</span>' : ''}
      </div>
    </div>`;
  }).join('');
}
"""

# ============================================================
# ENDPOINT MODIFICADO PARA INCLUIR HORÁRIO
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

# ============================================================
# FUNÇÃO DE CONFIRMAÇÃO MODIFICADA
# ============================================================

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
