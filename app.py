import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業美股戰情室 v8.0", layout="wide")
st.title("🏛️ 專業美股：長線財務趨勢對照 (分析師版)")

# --- 側邊欄控制 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, HIMS"
user_input = st.sidebar.text_area("觀測代號", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.subheader("📈 繪圖指標勾選")
show_pe = st.sidebar.checkbox("本益比 (PE)", value=True)
show_roe = st.sidebar.checkbox("ROE (%)", value=True)
show_gm = st.sidebar.checkbox("毛利率 (Gross Margin %)", value=True)
period = st.sidebar.selectbox("時間跨度", ["3y", "5y", "max"], index=1)

# --- 1. TQQQ 策略警示 (維持核心功能) ---
try:
    qqq = yf.Ticker("QQQ")
    hist_q = qqq.history(period="1y")
    if not hist_q.empty:
        curr, ma200 = hist_q['Close'].iloc[-1], hist_q['Close'].rolling(200).mean().iloc[-1]
        st.subheader("💡 策略警示：TQQQ 200MA 輪動")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ 200MA", f"${ma200:.2f}")
        if curr > ma200: st.success("✅ 訊號：多頭")
        else: st.error("🚨 訊號：空頭")
except: pass

st.divider()

# --- 2. 動態財務繪圖 (強效容錯版) ---
st.subheader("📈 歷史財務指標與股價對照圖")
target = st.selectbox("選擇分析標的", ticker_list)

def get_financial_value(df, keywords):
    """ 安全地從財報中搜尋可能的欄位名稱 """
    for k in keywords:
        matches = [c for c in df.index if k.lower() in c.lower()]
        if matches: return df.loc[matches[0]]
    return None

if target:
    with st.spinner(f'正在深度掃描 {target} 過去 5 年的財報數據...'):
        try:
            tk = yf.Ticker(target)
            hist = tk.history(period=period)
            q_fin = tk.quarterly_financials
            q_bs = tk.quarterly_balance_sheet
            
            # --- 抓取關鍵數據 (使用關鍵字偵測) ---
            rev = get_financial_value(q_fin, ["Revenue", "Total Revenue"])
            net_inc = get_financial_value(q_fin, ["Net Income", "Net Income Common"])
            gp = get_financial_value(q_fin, ["Gross Profit"])
            equity = get_financial_value(q_bs, ["Stockholders Equity", "Total Equity"])
            eps = tk.info.get('trailingEps') or 1

            # --- 數據處理 ---
            df = hist[['Close']].copy()
            df.columns = ['Price']
            
            # 計算 ROE & 毛利 (採 TTM 滾動)
            if net_inc is not None and equity is not None:
                roe = (net_inc.rolling(4).sum() / equity.rolling(4).mean()).reindex(df.index, method='ffill') * 100
                df['ROE'] = roe
            if gp is not None and rev is not None:
                gm = (gp.rolling(4).sum() / rev.rolling(4).sum()).reindex(df.index, method='ffill') * 100
                df['GM'] = gm
            
            df['PE'] = df['Price'] / eps

            # --- 繪圖邏輯 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=df.index, y=df['Price'], name="股價 (Price)", line=dict(color='black', width=2)), secondary_y=False)
            
            if show_pe:
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'], name="PE (左軸)", line=dict(dash='dash', color='orange')), secondary_y=False)
            if show_roe and 'ROE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['ROE'], name="ROE % (右軸)", line=dict(color='blue')), secondary_y=True)
            if show_gm and 'GM' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['GM'], name="毛利率 % (右軸)", line=dict(color='green')), secondary_y=True)

            fig.update_layout(title=f"{target} 長線財務趨勢", hovermode="x unified", height=600)
            fig.update_yaxes(title_text="USD / PE", secondary_y=False)
            fig.update_yaxes(title_text="百分比 (%)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"該標的財務數據不完整，無法繪製完整圖表。")

st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
