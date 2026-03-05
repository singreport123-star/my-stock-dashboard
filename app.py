import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄控制 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("自定義觀測代號", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# 持股成本設定 (以 HIMS 為例)
st.sidebar.divider()
st.sidebar.subheader("💰 我的持股成本")
hims_cost = st.sidebar.number_input("HIMS 成本價", value=37.90)
hims_qty = st.sidebar.number_input("HIMS 股數", value=35)

# --- 1. TQQQ 輪動策略 ---
try:
    qqq = yf.Ticker("QQQ")
    hist_q = qqq.history(period="1y")
    if not hist_q.empty:
        curr, ma200 = hist_q['Close'].iloc[-1], hist_q['Close'].rolling(200).mean().iloc[-1]
        st.subheader("💡 策略警示 (TQQQ 輪動)")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ 200MA", f"${ma200:.2f}")
        if curr > ma200: c3.success("✅ 訊號：多頭")
        else: c3.error("🚨 訊號：空頭")
except: pass

st.divider()

# --- 2. 持股損益計算 (New!) ---
if "HIMS" in ticker_list:
    st.subheader("📊 我的投資組合損益")
    h_tk = yf.Ticker("HIMS")
    h_price = h_tk.history(period="1d")['Close'].iloc[-1]
    profit = (h_price - hims_cost) * hims_qty
    p_percent = ((h_price / hims_cost) - 1) * 100
    
    pc1, pc2, pc3 = st.columns(3)
    pc1.metric("HIMS 目前市價", f"${h_price:.2f}")
    pc2.metric("預估損益 (USD)", f"${profit:.2f}", f"{p_percent:.2f}%")
    pc3.info(f"持有股數: {hims_qty}")
    st.divider()

# --- 3. 歷史河流圖 (進化曲線版) ---
st.subheader("🌊 本益比河流圖 (PE Band)")
target = st.selectbox("選擇標的", [t for t in ticker_list if t not in ["VOO", "QQQM", "IBIT"]])

if target:
    try:
        tk = yf.Ticker(target)
        hist = tk.history(period="3y")
        # 抓取每季 EPS 並計算滾動 TTM
        fin = tk.quarterly_financials
        if 'Basic EPS' in fin.index:
            eps_data = fin.loc['Basic EPS'].iloc[::-1].rolling(4).sum().dropna()
            if not eps_data.empty:
                # 對齊日期並繪圖
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='股價', line=dict(color='black')))
                
                # 河流倍數：NVDA 設較高，一般股設 15-35
                multi = [15, 20, 25, 30, 35] if target != "NVDA" else [30, 50, 70, 90, 110]
                latest_eps = eps_data.iloc[-1]
                
                for m in multi:
                    fig.add_trace(go.Scatter(x=hist.index, y=[latest_eps * m] * len(hist), name=f'{m}x PE', line=dict(dash='dash')))
                
                fig.update_layout(title=f"{target} 估值河流圖", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
    except: st.warning("該標的財報數據格式不支援繪製曲線河流圖。")

st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
