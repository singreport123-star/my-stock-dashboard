import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室 v7.0", layout="wide")
st.title("🏛️ 專業美股：多指標歷史趨勢繪圖 (3Y/5Y)")

# --- 側邊欄：控制面板 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, HIMS"
user_input = st.sidebar.text_area("觀測代號", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.subheader("📊 繪圖選項")
# 讓使用者勾選想要放進圖表的指標
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_pe = st.sidebar.checkbox("本益比 (PE)", value=True)
show_fwd_pe = st.sidebar.checkbox("預估本益比 (Forward PE)", value=False)
show_roe = st.sidebar.checkbox("股東權益報酬率 (ROE)", value=True)
show_gm = st.sidebar.checkbox("毛利率 (Gross Margin)", value=True)

period = st.sidebar.selectbox("時間跨度", ["3y", "5y", "max"], index=0)
ma_window = st.sidebar.slider("移動平均線天數 (MA)", 5, 60, 20)

# --- 1. TQQQ 輪動策略 ---
try:
    qqq = yf.Ticker("QQQ")
    hist_q = qqq.history(period="1y")
    if not hist_q.empty:
        curr, ma200 = hist_q['Close'].iloc[-1], hist_q['Close'].rolling(200).mean().iloc[-1]
        st.subheader("💡 核心策略：TQQQ 200MA 警示")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ 200MA", f"${ma200:.2f}")
        if curr > ma200: st.success("✅ 多頭環境")
        else: st.error("🚨 空頭環境")
except: pass

st.divider()

# --- 2. 動態繪圖邏輯 ---
st.subheader("📈 多指標歷史趨勢圖對照")
target = st.selectbox("選擇要分析的標的", ticker_list)

if target:
    with st.spinner(f'正在分析 {target} 的歷史長線數據...'):
        try:
            tk = yf.Ticker(target)
            # 抓取歷史價格數據
            hist = tk.history(period=period)
            # 抓取年度與季度財報
            fin = tk.quarterly_financials.T
            
            # --- 數據準備與對齊 ---
            df = hist[['Close']].copy()
            df.columns = ['Price']
            
            # 處理 PE 與指標 (透過 TTM 滾動計算)
            info = tk.info
            eps_ttm = fin['Basic EPS'].rolling(4).sum() if 'Basic EPS' in fin.columns else None
            roe_ttm = (fin['Net Income'] / tk.quarterly_balance_sheet.T['Total Stockholders Equity']).rolling(4).mean() if 'Net Income' in fin.columns else None
            gm_ttm = (fin['Gross Profit'] / fin['Total Revenue']).rolling(4).mean() if 'Gross Profit' in fin.columns else None

            # 將季報數據擴展至每日數據並對齊
            if eps_ttm is not None:
                df['PE'] = df['Price'] / eps_ttm.reindex(df.index, method='ffill')
            if roe_ttm is not None:
                df['ROE'] = roe_ttm.reindex(df.index, method='ffill') * 100
            if gm_ttm is not None:
                df['GM'] = gm_ttm.reindex(df.index, method='ffill') * 100
            
            # --- 繪圖 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 股價 (左軸)
            if show_price:
                fig.add_trace(go.Scatter(x=df.index, y=df['Price'], name="Price (左軸)", line=dict(color='black', width=2)), secondary_y=False)
            
            # PE (左軸 - 數值較大)
            if show_pe and 'PE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'].rolling(ma_window).mean(), name=f"PE {ma_window}MA (左軸)", line=dict(dash='dash')), secondary_y=False)

            # ROE / GM (右軸 - 百分比)
            if show_roe and 'ROE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['ROE'].rolling(ma_window).mean(), name=f"ROE {ma_window}MA (右軸 %)", line=dict(color='blue', width=1.5)), secondary_y=True)
            if show_gm and 'GM' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['GM'].rolling(ma_window).mean(), name=f"毛利 {ma_window}MA (右軸 %)", line=dict(color='green', width=1.5)), secondary_y=True)

            fig.update_layout(title=f"{target} 長線財務趨勢對照", hovermode="x unified", height=600)
            fig.update_yaxes(title_text="價格 / PE", secondary_y=False)
            fig.update_yaxes(title_text="百分比 (%)", secondary_y=True)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.warning(f"圖表繪製失敗：部分歷史財務數據不足。錯誤代碼: {e}")

st.caption(f"數據更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
