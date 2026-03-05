import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="專業美股儀表板 V2", layout="wide")

st.title("🚀 我的股市數據儀表板 (河流圖版)")

# --- 側邊欄控制 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("請輸入美股代號 (用逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 1. TQQQ 輪動策略 ---
try:
    qqq = yf.Ticker("QQQ")
    hist_qqq = qqq.history(period="1y")
    if not hist_qqq.empty:
        curr = hist_qqq['Close'].iloc[-1]
        ma200 = hist_qqq['Close'].rolling(window=200).mean().iloc[-1]
        st.subheader("💡 交易策略警示 (TQQQ 輪動)")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ MA200", f"${ma200:.2f}")
        if curr > ma200:
            c3.success("✅ 訊號：多頭")
        else:
            c3.error("🚨 訊號：空頭")
except:
    pass

st.divider()

# --- 2. 基本面數據表 ---
@st.cache_data(ttl=3600)
def get_table_data(tickers):
    data = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            price = tk.history(period="1d")['Close'].iloc[-1]
            data.append({
                "標的": s,
                "現價": f"${price:.2f}",
                "PE": round(info.get('trailingPE', 0), 1) if info.get('trailingPE') else "—",
                "Fwd PE": round(info.get('forwardPE', 0), 1) if info.get('forwardPE') else "—",
                "PEG": round(info.get('pegRatio', 0), 2) if info.get('pegRatio') else "—"
            })
        except: continue
    return pd.DataFrame(data)

st.subheader("📊 基本面概覽")
st.dataframe(get_table_data(ticker_list), use_container_width=True, hide_index=True)

# --- 3. 本益比河流圖 (核心新增功能) ---
st.divider()
st.subheader("🌊 本益比河流圖 (PE Band)")
target = st.selectbox("選擇要繪製河流圖的標的 (限個股)", [t for t in ticker_list if "VOO" not in t and "QQQ" not in t and "IBIT" not in t])

if target:
    try:
        tk = yf.Ticker(target)
        # 獲取 5 年歷史股價
        hist = tk.history(period="5y")
        # 獲取年度 EPS (這部分數據在 yfinance 有時較難抓，我們用目前 PE 與股價回推近似值)
        info = tk.info
        current_pe = info.get('trailingPE')
        
        if current_pe:
            eps = hist['Close'].iloc[-1] / current_pe
            
            # 定義 5 條河流的倍數 (可視個股屬性調整)
            multipliers = [15, 20, 25, 30, 35] if target != "NVDA" else [30, 45, 60, 75, 90]
            
            fig = go.Figure()
            # 畫出股價線
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='股價', line=dict(color='black', width=2)))
            
            # 畫出河流區間 (簡化版：以當前估計 EPS 畫出參考線)
            for m in multipliers:
                fig.add_trace(go.Scatter(x=hist.index, y=[eps * m] * len(hist), name=f'{m}x PE', line=dict(dash='dash')))
            
            fig.update_layout(title=f"{target} 本益比參考區間", xaxis_title="時間", yaxis_title="股價 (USD)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("該標的暫無足夠的 PE 資料可供繪圖。")
    except Exception as e:
        st.error(f"繪圖發生錯誤: {e}")
