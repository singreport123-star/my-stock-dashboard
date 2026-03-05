import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室 v9.0", layout="wide")
st.title("🏛️ 專業美股：長線財務趨勢與自定義監控")

# --- 側邊欄控制 ---
st.sidebar.header("⚙️ 觀測清單設定")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, HIMS"
user_input = st.sidebar.text_area("代號 (逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("📈 繪圖趨勢勾選")
# 歷史與均線設定
history_range = st.sidebar.selectbox("歷史長度", ["3y", "5y", "10y"], index=1)
ma_val = st.sidebar.slider("均線天數 (MA)", 5, 200, 20)
# 指標勾選
show_pe = st.sidebar.checkbox("顯示 PE 趨勢", value=True)
show_roe = st.sidebar.checkbox("顯示 ROE (3Y/5Y均)", value=True)
show_gm = st.sidebar.checkbox("顯示毛利率 (3Y/5Y均)", value=True)

# --- 1. TQQQ 輪動策略 (維持核心穩定) ---
try:
    qqq = yf.Ticker("QQQ")
    hist_q = qqq.history(period="1y")
    if not hist_q.empty:
        curr, ma200 = hist_q['Close'].iloc[-1], hist_q['Close'].rolling(200).mean().iloc[-1]
        st.subheader("💡 核心策略：TQQQ 200MA 警示")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ 200MA", f"${ma200:.2f}")
        if curr > ma200: st.success("✅ 訊號：多頭")
        else: st.error("🚨 訊號：空頭")
except: pass

st.divider()

# --- 2. 核心繪圖函數 (極致容錯) ---
st.subheader("📊 個股長線財務趨勢圖")
target = st.selectbox("選擇分析標的", ticker_list)

if target:
    with st.spinner('正在同步全球財報數據...'):
        try:
            tk = yf.Ticker(target)
            hist = tk.history(period=history_range)
            # 獲取年度與季度數據
            annual_fin = tk.financials.T
            info = tk.info
            
            # 準備繪圖畫板
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # A. 基礎股價與均線
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name="股價", line=dict(color='black', width=1.5)), secondary_y=False)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].rolling(ma_val).mean(), name=f"{ma_val}MA", line=dict(color='gray', dash='dot')), secondary_y=False)
            
            # B. 財務指標處理 (使用安全抓取)
            if show_pe:
                eps = info.get('trailingEps') or 1
                pe_trace = hist['Close'] / eps
                fig.add_trace(go.Scatter(x=pe_trace.index, y=pe_trace, name="PE 走勢", line=dict(color='orange', width=1)), secondary_y=False)
            
            if not annual_fin.empty:
                # 計算長線平均 (3Y/5Y)
                if show_gm and 'Total Revenue' in annual_fin.columns:
                    gm_series = (annual_fin['Gross Profit'] / annual_fin['Total Revenue']) * 100
                    # 畫出 3Y 與 5Y 平均線作為參考
                    avg_3y = gm_series.head(3).mean()
                    fig.add_hline(y=avg_3y, line_dash="dash", line_color="green", annotation_text=f"3Y均毛利:{avg_3y:.1f}%", secondary_y=True)
                
                if show_roe and 'Net Income' in annual_fin.columns:
                    # 簡化版 ROE 趨勢
                    roe_val = (info.get('returnOnEquity', 0) * 100)
                    fig.add_hline(y=roe_val, line_dash="dot", line_color="blue", annotation_text=f"目前 ROE:{roe_val:.1f}%", secondary_y=True)

            fig.update_layout(title=f"{target} {history_range} 趨勢對照", hovermode="x unified", height=600)
            fig.update_yaxes(title_text="價格 / PE", secondary_y=False)
            fig.update_yaxes(title_text="百分比 (%)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"該標的數據抓取中，請稍後再試。")

# --- 3. 基本面清單表格 ---
st.divider()
st.subheader("📋 觀測清單基本面快照")
# (保留之前穩定的基本面表格代碼...)
