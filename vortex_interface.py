# ============================================================
# SISTEMA DE EXPIRAÇÃO DE SINAIS (15 minutos)
# ============================================================

import threading
from datetime import datetime, timedelta

# Armazenamento em memória dos sinais ativos com timestamp
sinais_ativos = {}  # {symbol: {"dados": sinal, "timestamp": datetime}}

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

# Inicia a thread de verificação em background
threading.Thread(target=verificar_sinais_expirados, daemon=True).start()

# ============================================================
# FUNÇÃO MODIFICADA PARA GERENCIAR SINAIS
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
            "data": datetime.now().strftime("%d/%m %H:%M"),
            "timestamp_criacao": datetime.now().isoformat()
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
                    "timestamp": datetime.now()
                }
        else:
            # Novo sinal
            sinais_ativos[symbol] = {
                "dados": sinal_data,
                "timestamp": datetime.now()
            }

# ============================================================
# NOVO ENDPOINT PARA CONSULTAR SINAIS ATIVOS COM TEMPO RESTANTE
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
        
        sinais_retorno.append(sinal)
    
    return sinais_retorno

@app.get("/api/sinais/ativos")
async def get_sinais_ativos():
    """Endpoint específico para sinais ativos"""
    return await get_sinais()

@app.get("/api/sinais/expirados")
async def get_sinais_expirados():
    """Retorna apenas sinais expirados do histórico"""
    historico = carregar_historico()
    expirados = [s for s in historico if s.get("status") == "expirado"]
    return expirados

# ============================================================
# HTML MODIFICADO (trecho relevante para mostrar tempo restante)
# ============================================================

# Adicione esta função JavaScript ao HTML_PAGE
def get_modified_html():
    return HTML_PAGE.replace(
        '</div>',
        '''
        <div class="sig-expiry" style="font-family:var(--mono);font-size:.58rem;color:var(--warn);margin-top:6px;padding-top:5px;border-top:1px solid var(--border)">
          ⏱ Expira em: <span class="expiry-timer" data-expiry="${s.expiracao}">${s.tempo_restante_formatado}</span>
        </div>
        </div>
        ''',
        1  # Apenas a primeira ocorrência (no lugar certo)
    )

# Adicione também um contador regressivo ao JavaScript
countdown_script = """
<script>
// Contador regressivo para expiração
function atualizarTemporizadores() {
    document.querySelectorAll('.expiry-timer').forEach(el => {
        const expiryTime = el.getAttribute('data-expiry');
        if (expiryTime) {
            const now = new Date();
            const [hours, minutes, seconds] = expiryTime.split(':');
            const expiry = new Date();
            expiry.setHours(parseInt(hours), parseInt(minutes), parseInt(seconds));
            
            const diff = expiry - now;
            if (diff <= 0) {
                el.textContent = 'Expirado';
                el.style.color = '#ef4444';
                // Recarregar sinais quando expirar
                setTimeout(() => carregarTudo(), 1000);
            } else {
                const mins = Math.floor(diff / 60000);
                const secs = Math.floor((diff % 60000) / 1000);
                el.textContent = `${mins}min ${secs}s`;
            }
        }
    });
}

// Atualizar a cada segundo
setInterval(atualizarTemporizadores, 1000);
</script>
"""

# ============================================================
# ENDPOINT PARA LIMPAR SINAIS EXPIRADOS MANUALMENTE
# ============================================================

@app.post("/api/sinais/limpar-expirados")
async def limpar_sinais_expirados():
    """Remove todos os sinais expirados do histórico (opcional)"""
    historico = carregar_historico()
    historico = [s for s in historico if s.get("status") != "expirado" or 
                 datetime.now() - datetime.strptime(s.get("data_confirmacao", "01/01/2000 00:00:00"), "%d/%m/%Y %H:%M:%S") < timedelta(days=7)]
    salvar_historico(historico)
    return {"ok": True, "mensagem": "Sinais expirados antigos removidos"}

# ============================================================
# FUNÇÃO DE MONITORAMENTO (opcional - para logs)
# ============================================================

def monitorar_sinais():
    """Função de monitoramento para debug"""
    while True:
        if sinais_ativos:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sinais ativos: {len(sinais_ativos)}")
            for symbol, item in sinais_ativos.items():
                tempo_restante = 900 - (datetime.now() - item["timestamp"]).total_seconds()
                if tempo_restante > 0:
                    print(f"  - {symbol}: {item['dados']['sinal']} (expira em {int(tempo_restante//60)}min)")
        time.sleep(60)

# Iniciar monitoramento (opcional, descomente se quiser)
# threading.Thread(target=monitorar_sinais, daemon=True).start()
