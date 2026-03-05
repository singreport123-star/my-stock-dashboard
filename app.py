import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業美股戰情室 v3.0", layout="wide")

st.title("🏛️ 專業美股基本面與持股監控")

# --- 側邊欄：動態控制 ---
st.sidebar.header("⚙️ 觀測清單")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("自定義觀測代號", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("💼 持股管理 (格式：代號:成本:股數)")
default_portfolio = "HIMS:37.90:35" 
portfolio_input = st.sidebar.text_area("每行一筆持股", default_portfolio, height=120)

# --- 1. TQQQ 輪動策略警示 ---
try:
    qqq = yf.Ticker("QQQ")
    hist_q = qqq.history(period="1y")
    if not hist_q.empty:
        curr, ma200 = hist_q['Close'].iloc[-1], hist_q['Close'].rolling(200).mean().iloc[-1]
        diff = ((curr - ma200) / ma200) * 100
        st.subheader("💡 核心策略：TQQQ 輪動警示")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ 200MA", f"${ma200:.2f}", f"{diff:.2f}%")
        if curr > ma200: c3.success("✅ 訊號：多頭 (站上 200MA)")
        else: c3.error("🚨 訊號：空頭 (跌破 200MA)")
except: pass

st.divider()

# --- 2. 專業級投資組合回報 ---
st.subheader("📊 投資組合實時回報")
portfolio_data = []
for line in portfolio_input.split('\n'):
    if ':' in line:
        try:
            sym, cost, qty = line.split(':')
            tk = yf.Ticker(sym.strip().upper())
            cp = tk.history(period="1d")['Close'].iloc[-1]
            total_c, current_v = float(cost)*float(qty), cp*float(qty)
            pnl = current_v - total_c
            portfolio_data.append({
                "標的": sym.strip().upper(), "持有股數": float(qty), "成本價": f"${float(cost):.2f}",
                "目前市價": f"${cp:.2f}", "總損益": round(pnl, 2), "報酬率": f"{(pnl/total_c)*100:.2f}%"
            })
        except: continue

if portfolio_data:
    p_df = pd.DataFrame(portfolio_data)
    st.table(p_df)
else:
    st.info("請在側邊欄輸入持股明細以開啟監控。")

st.divider()

# --- 3. 專業分析師基本面表 (核心財務比率) ---
st.subheader("📈 專業基本面分析指標")

@st.cache_data(ttl=1800)
def fetch_analyst_data(tickers):
    results = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            
            # 判斷是否為 ETF 或基金 (跳過部分指標)
            is_etf = info.get('quoteType') in ['ETF', 'FUND']
            
            results.append({
                "代號": s,
                "PE (TTM)": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "Fwd PE": round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "—",
                "PEG": round(info.get('pegRatio', 0), 2) if info.get('pegRatio') else "—",
                "ROE (%)": f"{round(info.get('returnOnEquity', 0)*100, 1)}%" if not is_etf else "ETF",
                "毛利率 (%)": f"{round(info.get('grossMargins', 0)*100, 1)}%" if not is_etf else "—",
                "營收成長 (%)": f"{round(info.get('revenueGrowth', 0)*100, 1)}%" if not is_etf else "—",
                "負債權益比": round(info.get('debtToEquity', 0)/100, 2) if info.get('debtToEquity') else "—"
            })
        except: continue
    return pd.DataFrame(results)

with st.spinner('正在計算財務比率...'):
    analyst_df = fetch_analyst_data(ticker_list)
    st.dataframe(analyst_df, use_container_width=True, hide_index=True)

st.caption(f"數據更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
