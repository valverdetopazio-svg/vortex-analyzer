# ============================================================
# IMPORTAÇÕES ADICIONAIS
# ============================================================
from tradingview_ta import TA_Handler, Interval, Exchange

# ============================================================
# FONTES DE DADOS COM TRADINGVIEW COMO PRINCIPAL
# ============================================================

def fetch_tradingview(symbol, interval):
    """Busca dados do TradingView"""
    try:
        # Mapeamento de símbolos para TradingView
        tv_symbols = {
            "EURUSD=X": {"symbol": "EURUSD", "exchange": "FX_IDC", "screener": "forex"},
            "USDJPY=X": {"symbol": "USDJPY", "exchange": "FX_IDC", "screener": "forex"},
            "GBPUSD=X": {"symbol": "GBPUSD", "exchange": "FX_IDC", "screener": "forex"},
            "USDCHF=X": {"symbol": "USDCHF", "exchange": "FX_IDC", "screener": "forex"},
            "AUDUSD=X": {"symbol": "AUDUSD", "exchange": "FX_IDC", "screener": "forex"},
            "USDCAD=X": {"symbol": "USDCAD", "exchange": "FX_IDC", "screener": "forex"},
            "NZDUSD=X": {"symbol": "NZDUSD", "exchange": "FX_IDC", "screener": "forex"},
            "GC=F": {"symbol": "GOLD", "exchange": "TVC", "screener": "commodity"},
            "SI=F": {"symbol": "SILVER", "exchange": "TVC", "screener": "commodity"},
            "CL=F": {"symbol": "WTI", "exchange": "TVC", "screener": "commodity"},
            "BZ=F": {"symbol": "BRENT", "exchange": "TVC", "screener": "commodity"},
            "NG=F": {"symbol": "NATGAS", "exchange": "TVC", "screener": "commodity"},
            "BTC-USD": {"symbol": "BTCUSDT", "exchange": "BINANCE", "screener": "crypto"},
            "ETH-USD": {"symbol": "ETHUSDT", "exchange": "BINANCE", "screener": "crypto"},
            "^GDAXI": {"symbol": "DAX", "exchange": "INDEX", "screener": "cfd"},
            "^FTSE": {"symbol": "UK100", "exchange": "INDEX", "screener": "cfd"},
            "^N225": {"symbol": "NIKKEI", "exchange": "INDEX", "screener": "cfd"},
            "^GSPC": {"symbol": "SPX", "exchange": "INDEX", "screener": "cfd"},
            "^IXIC": {"symbol": "IXIC", "exchange": "INDEX", "screener": "cfd"},
            "^DJI": {"symbol": "DJI", "exchange": "INDEX", "screener": "cfd"},
            "AAPL": {"symbol": "AAPL", "exchange": "NASDAQ", "screener": "america"},
            "NVDA": {"symbol": "NVDA", "exchange": "NASDAQ", "screener": "america"},
        }
        
        tv_config = tv_symbols.get(symbol)
        if not tv_config:
            return None
            
        # Mapeamento de intervalos
        interval_map = {
            "5m": Interval.INTERVAL_5_MINUTES,
            "15m": Interval.INTERVAL_15_MINUTES,
            "30m": Interval.INTERVAL_30_MINUTES,
            "1h": Interval.INTERVAL_1_HOUR,
            "4h": Interval.INTERVAL_4_HOURS,
            "1d": Interval.INTERVAL_1_DAY,
        }
        
        tv_interval = interval_map.get(interval, Interval.INTERVAL_15_MINUTES)
        
        handler = TA_Handler(
            symbol=tv_config["symbol"],
            exchange=tv_config["exchange"],
            screener=tv_config["screener"],
            interval=tv_interval,
            timeout=10
        )
        
        # Buscar análise técnica
        analysis = handler.get_analysis()
        
        if analysis and analysis.indicators:
            # Tentar buscar dados de candle via scraping ou usar indicadores
            # Para dados completos, ainda vamos usar Yahoo como complemento
            return {
                "fonte": "tradingview",
                "indicators": analysis.indicators,
                "summary": analysis.summary
            }
    except Exception as e:
        print(f"TradingView error for {symbol}: {e}")
    return None

def fetch_yahoo_with_tv_fallback(symbol, interval):
    """Busca dados do Yahoo mas usa TradingView para indicadores se possível"""
    try:
        yi = "1h" if interval == "4h" else interval
        rng = {"5m":"5d","15m":"5d","30m":"5d","1h":"30d","4h":"60d","1d":"6mo"}.get(interval, "5d")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={yi}&range={rng}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        if r.status_code == 200:
            res = r.json().get("chart", {}).get("result", [])
            if res:
                q = res[0].get("indicators", {}).get("quote", [{}])[0]
                closes = [c for c in q.get("close", []) if c is not None]
                volumes = [v for v in q.get("volume", []) if v is not None]
                if closes:
                    if not volumes or max(volumes) == 0:
                        volumes = [1000000.0] * len(closes)
                    
                    # Tentar obter indicadores do TradingView para complementar
                    tv_data = fetch_tradingview(symbol, interval)
                    
                    return {
                        "closes": closes, 
                        "volumes": volumes, 
                        "fonte": "yahoo",
                        "tv_indicators": tv_data.get("indicators") if tv_data else None,
                        "tv_summary": tv_data.get("summary") if tv_data else None
                    }
    except Exception as e:
        print(f"Yahoo error: {e}")
    return None

def fetch_candles(symbol, interval):
    """Busca candles com prioridade para TradingView via Yahoo + indicadores"""
    # Primeiro tenta Yahoo (dados de preço) + TradingView (indicadores)
    d = fetch_yahoo_with_tv_fallback(symbol, interval)
    if d and d.get("closes"):
        return d
    
    # Fallback para Binance se aplicável
    if SYMBOL_CONFIG.get(symbol, {}).get("binance"):
        d = fetch_binance(symbol, interval)
        if d: 
            d["fonte"] = "binance"
            return d
    
    # Fallback final simulado
    return fetch_fallback(symbol, interval)

# ============================================================
# FUNÇÃO DE ANÁLISE MODIFICADA PARA USAR TRADINGVIEW
# ============================================================

def get_analysis_with_tradingview(symbol, interval="15m"):
    """Análise usando TradingView como fonte primária de indicadores"""
    dados = fetch_candles(symbol, interval)
    closes = dados.get("closes", [])
    vols = dados.get("volumes", [])
    fonte = dados.get("fonte", "desconhecida")
    tv_indicators = dados.get("tv_indicators", {})
    tv_summary = dados.get("tv_summary", {})
    
    if len(closes) < 35:
        return None
    
    # Calcular indicadores técnicos locais
    a = analisar_closes(symbol, closes, vols)
    tipo = a["tipo"]
    p = a["preco"]
    
    # Se tiver dados do TradingView, usar para melhorar a análise
    if tv_indicators:
        # Atualizar RSI e MACD com valores do TradingView se disponíveis
        if "RSI" in tv_indicators:
            a["rsi"] = round(tv_indicators["RSI"], 1)
        if "MACD.macd" in tv_indicators and "MACD.signal" in tv_indicators:
            macd_line = tv_indicators["MACD.macd"]
            macd_signal = tv_indicators["MACD.signal"]
            a["macd_hist"] = round(macd_line - macd_signal, 6)
        
        # Adicionar informações do TradingView
        a["tv_recommendation"] = tv_summary.get("RECOMMENDATION", "NEUTRAL")
        a["tv_buy"] = tv_summary.get("BUY", 0)
        a["tv_sell"] = tv_summary.get("SELL", 0)
        a["tv_neutral"] = tv_summary.get("NEUTRAL", 0)
    
    # ── Multi-Timeframe ──
    tf_up = {"5m":"15m","15m":"1h","30m":"1h","1h":"4h","4h":"1d","1d":"1d"}.get(interval, "1h")
    mtf_ok = True
    tend_s = "LATERAL"
    if tf_up != interval:
        ds = fetch_candles(symbol, tf_up)
        if ds and len(ds.get("closes", [])) >= 35:
            as_ = analisar_closes(symbol, ds["closes"], ds.get("volumes", []))
            tend_s = as_["tendencia"]
            if a["sinal_bruto"] == "COMPRA" and tend_s == "BAIXA":
                mtf_ok = False
            if a["sinal_bruto"] == "VENDA" and tend_s == "ALTA":
                mtf_ok = False
    
    # Calcular score com possível ajuste do TradingView
    score = calcular_score(
        a["rsi"], a["macd_hist"], p, a["bb_upper"], a["bb_lower"],
        a["sinal_bruto"], a["volume_ratio"], mtf_ok
    )
    
    # Ajustar score baseado na recomendação do TradingView
    if tv_summary:
        if tv_summary.get("RECOMMENDATION") == "STRONG_BUY" and a["sinal_bruto"] == "COMPRA":
            score = min(100, score + 10)
        elif tv_summary.get("RECOMMENDATION") == "STRONG_SELL" and a["sinal_bruto"] == "VENDA":
            score = min(100, score + 10)
    
    sinal = a["sinal_bruto"] if (score >= SCORE_MINIMO and mtf_ok) else "NEUTRO"
    forca = calcular_forca(a["rsi"], a["macd_hist"], sinal)
    confianca = round(50 + score / 2, 1) if sinal != "NEUTRO" else round(score * 0.6, 1)
    
    mult = ATR_MULTIPLIER.get(tipo, ATR_MULTIPLIER["Ações"])
    atr = a["atr"]
    sl = round(p - mult["stop"] * atr, 6) if sinal == "COMPRA" else round(p + mult["stop"] * atr, 6)
    tp = round(p + mult["tp"] * atr, 6) if sinal == "COMPRA" else round(p - mult["tp"] * atr, 6)
    
    result = {
        "preco": p,
        "rsi": a["rsi"],
        "macd_hist": a["macd_hist"],
        "bb_upper": a["bb_upper"],
        "bb_lower": a["bb_lower"],
        "volume_ratio": a["volume_ratio"],
        "ema9": a["ema9"],
        "ema21": a["ema21"],
        "ema50": a["ema50"],
        "tendencia": a["tendencia"],
        "tendencia_sup": tend_s,
        "sinal": sinal,
        "score": score,
        "forca": forca,
        "confianca": confianca,
        "mtf_ok": mtf_ok,
        "stop_loss": sl,
        "take_profit": tp,
        "fonte": f"tradingview+{fonte}" if tv_indicators else fonte,
    }
    
    # Adicionar dados do TradingView se disponíveis
    if tv_indicators:
        result["tv_recommendation"] = a.get("tv_recommendation", "NEUTRAL")
        result["tv_buy"] = a.get("tv_buy", 0)
        result["tv_sell"] = a.get("tv_sell", 0)
    
    return result

# Atualizar a função de processamento para usar a nova análise
def processar_e_armazenar_sinais():
    """Processa todos os ativos usando TradingView como fonte principal"""
    for symbol, cfg in SYMBOL_CONFIG.items():
        analysis = get_analysis_with_tradingview(symbol, "15m")
        if not analysis or analysis["sinal"] == "NEUTRO":
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
        
        # Adicionar dados do TradingView se disponíveis
        if "tv_recommendation" in analysis:
            sinal_data["tv_recommendation"] = analysis["tv_recommendation"]
            sinal_data["tv_buy"] = analysis["tv_buy"]
            sinal_data["tv_sell"] = analysis["tv_sell"]
        
        if symbol in sinais_ativos:
            sinal_existente = sinais_ativos[symbol]["dados"]
            if sinal_existente["sinal"] != sinal_data["sinal"]:
                mover_sinal_para_historico(symbol, sinal_existente)
                sinais_ativos[symbol] = {"dados": sinal_data, "timestamp": agora}
        else:
            sinais_ativos[symbol] = {"dados": sinal_data, "timestamp": agora}
