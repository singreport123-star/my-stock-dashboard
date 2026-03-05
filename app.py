import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="專業美股觀測站", layout="wide")

st.title("🚀 我的股市數據儀表板")

# 你的觀測清單 + TQQQ/QQQ 用於計算策略
tickers = ["NVDA", "MSFT", "META", "TSLA", "AAPL", "ORCL", "VOO", "QQQM", "IBIT", "DXYZ"]
strategy_tickers = ["TQQQ", "QQQ"]

@st.cache_data(ttl=3600)
def get_stock_data(symbol_list):
    all_data = []
    for s in symbol_list:
        try:
            tk = yf.Ticker(s)
            # 使用 fast_info 或 history 確保抓得到價格
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else "N/A"
            
            info = tk.info
            is_etf = info.get('quoteType') == 'ETF'
            
            all_data.append({
                "標的": s,
                "名稱": info.get("shortName", "N/A"),
                "現價": f"${price:.2f}" if isinstance(price, float) else "N/A",
                "PE (本益比)": round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else "—",
                "Forward PE": round(info.get("forwardPE", 0), 2) if info.get("forwardPE") else "—",
                "PEG": info.get("pegRatio", "—"),
                "市值 (B)": round(info.get("marketCap", 0) / 1e9, 2) if info.get("marketCap") else "N/A"
            })
        except:
            all_data.append({"標的": s, "名稱": "連線逾時", "現價": "N/A"})
    return pd.DataFrame(all_data)

# --- 核心功能：TQQQ 200MA 策略判斷 ---
def check_strategy():
    st.subheader("💡 交易策略警示 (TQQQ 輪動)")
    try:
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="1y") # 抓一年數據算 200MA
        current_price = hist['Close'].iloc[-1]
        ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("QQQ 現價", f"${current_price:.2f}")
        col2.metric("QQQ 200MA", f"${ma200:.2f}")
        
        if current_price > ma200:
            col3.success("✅ 訊號：多頭 (站上 200MA)")
        else:
            col3.error("🚨 訊號：空頭 (跌破 200MA)")
    except:
        st.warning("暫時無法取得策略數據")

# --- 執行介面 ---
check_strategy()

st.divider()

with st.spinner('更新基本面數據中...'):
    df = get_stock_data(tickers)
    st.subheader("📊 個股基本面概覽")
    st.dataframe(df, use_container_width=True, hide_index=True)

st.info("註：若數據顯示為 — 或 N/A，可能是該標的（如 ETF 或 DXYZ）暫無該項財務指標。")
