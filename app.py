import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁設定 ---
st.set_page_config(page_title="專業美股儀表板", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄：自由輸入標的 ---
st.sidebar.header("⚙️ 控制面板")
# 這裡可以自由修改預設清單
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("請輸入美股代號 (用逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 1. TQQQ 輪動策略警示 ---
def render_strategy_light():
    try:
        # 抓取 QQQ 過去一年數據計算 200MA
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="1y")
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            diff = ((curr - ma200) / ma200) * 100
            
            st.subheader("💡 交易策略警示 (TQQQ 輪動)")
            c1, c2, c3 = st.columns(3)
            c1.metric("QQQ 現價", f"${curr:.2f}")
            c2.metric("QQQ 200MA", f"${ma200:.2f}", f"{diff:.2f}%")
            if curr > ma200:
                c3.success("✅ 訊號：多頭 (站上 200MA)")
            else:
                c3.error("🚨 訊號：空頭 (跌破 200MA)")
    except:
        st.warning("策略數據讀取中...")

render_strategy_light()
st.divider()

# --- 2. 抓取基本面數據 ---
@st.cache_data(ttl=1800)
def fetch_fundamental_data(tickers):
    data = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            # 優先從 history 抓最新價格，確保準確性
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else info.get('currentPrice', 0)
            
            # PEG 多重備援邏輯
            peg = info.get('pegRatio') or info.get('trailingPegRatio', '—')
            
            data.append({
                "標的": s,
                "名稱": info.get('shortName', 'N/A'),
                "現價": f"${price:.2f}" if price > 0 else "N/A",
                "PE (本益比)": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "Forward PE": round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "—",
                "PEG (增長比)": round(peg, 2) if isinstance(peg, (int, float)) else peg,
                "市值 (B)": f"{round(info.get('marketCap', 0)/1e9, 2)}B" if info.get('marketCap') else "—"
            })
        except:
            continue
    return pd.DataFrame(data)

# --- 3. 顯示數據表 ---
st.subheader("📊 個股基本面概覽")
with st.spinner('正在更新市場數據...'):
    df = fetch_fundamental_data(ticker_list)
    if not df.empty:
        # 使用表格顯示，並讓寬度自適應
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("請在左側輸入有效的代號。")

st.divider()
st.info("💡 提示：ETF (如 VOO/QQQM/IBIT) 通常不具備 PE 或 PEG 指標。")
st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
