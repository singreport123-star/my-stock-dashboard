import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="專業股市戰情室 v18.0", layout="wide")
st.title("🏛️ 專業美股：量價合一與精準估值矩陣")

# --- 側邊欄：控制與勾選 ---
st.sidebar.header("⚙️ 觀測清單")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS, ORCL, AMD, SMCI, TSM"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("🎨 繪圖指標勾選")
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_eps = st.sidebar.checkbox("歷史 EPS (年度基礎)", value=True)
show_turnover = st.sidebar.checkbox("籌碼動能：成交金額 (Turnover)", value=True)
show_pe = st.sidebar.checkbox("個股 PE 趨勢 (含MA)", value=True)
show_ind_pe = st.sidebar.checkbox("產業歷史平均 PE 走勢", value=True)
show_fwd_pe = st.sidebar.checkbox("顯示 Forward PE (預估線)", value=True)

history_range = st.sidebar.selectbox("歷史數據跨度", ["3y", "5y", "10y"], index=1)
ma_window = st.sidebar.slider("趨勢平滑化 (MA天數)", 5, 120, 20)

# --- 1. 核心基本面快照 ---
@st.cache_data(ttl=1800)
def fetch_accurate_data(tickers):
    results = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist_1d = tk.history(period="1d")
            price = hist_1d['Close'].iloc[-1] if not hist_1d.empty else 0
            
            results.append({
                "標的": s,
                "行業": info.get('industry', 'Other'),
                "現價": f"${price:.2f}" if price else "—",
                "PE (即時)": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "Fwd PE": round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "—",
                "ROE": f"{round(info.get('returnOnEquity', 0) * 100, 2)}%" if info.get('returnOnEquity') else "—"
            })
        except: continue
    return pd.DataFrame(results)

st.subheader("📋 觀測清單與產業矩陣")
with st.spinner('獲取最新官方財務數據...'):
    df_snapshot = fetch_accurate_data(ticker_list)
    st.dataframe(df_snapshot, use_container_width=True, hide_index=True)

st.divider()

# --- 2. 歷史 PE 與 EPS 提取引擎 (💡 移除雙重分割校準，還原真實數據) ---
@st.cache_data(ttl=3600)
def get_historical_pe_eps(ticker, period):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period)
        if hist.empty: return None, None
        hist.index = hist.index.tz_localize(None).normalize()
        
        a_fin = tk.financials.T
        eps_series = pd.Series(dtype=float)
        
        if not a_fin.empty:
            a_fin.index = a_fin.index.tz_localize(None).normalize()
            a_fin = a_fin.sort_index()
            # 優先抓取 Diluted EPS (稀釋後每股盈餘最準確)
            eps_col = 'Diluted EPS' if 'Diluted EPS' in a_fin.columns else ('Basic EPS' if 'Basic EPS' in a_fin.columns else None)
            if eps_col:
                eps_series = a_fin[eps_col].dropna()

        current_eps = tk.info.get('trailingEps')
        if current_eps:
            eps_series.loc[pd.Timestamp.today().normalize()] = current_eps

        if eps_series.empty: return None, None
        eps_series = eps_series.sort_index()

        # 💡 將 EPS 對齊到每一天的歷史股價
        df = pd.DataFrame(index=hist.index)
        df['Price'] = hist['Close']
        
        combined_index = df.index.union(eps_series.index).sort_values()
        temp_df = pd.DataFrame(index=combined_index)
        temp_df['EPS'] = eps_series
        temp_df['EPS'] = temp_df['EPS'].ffill().bfill() # bfill 僅用於填補最前段的空窗期
        
        df['EPS'] = temp_df['EPS'].loc[df.index]
        
        # 💡 計算 PE 並放寬過濾條件 (1 到 1000倍，容納科技股高估值)
        pe = df['Price'] / df['EPS']
        pe = pe.where((pe > 0) & (pe < 1000)) 
        
        return pe, df['EPS']
    except:
        return None, None

# --- 3. 動態三視窗繪圖邏輯 (💡 調整 Layout 順序：價 -> 量 -> 估值) ---
st.subheader("📈 量價動能與估值解析")
target = st.selectbox("選擇深度分析標的", ticker_list)

if target:
    with st.spinner(f'正在執行 {target} 的量價與估值重構...'):
        try:
            target_tk = yf.Ticker(target)
            target_hist = target_tk.history(period
