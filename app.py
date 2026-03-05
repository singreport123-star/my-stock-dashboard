import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="專業股市戰情室 v4.0", layout="wide")
st.title("🏛️ 專業美股基本面：垂直與水平分析")

# --- 側邊欄 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("觀測代號", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("💼 持股監控")
default_portfolio = "HIMS:37.90:35\nNVDA:120.5:10"
portfolio_input = st.sidebar.text_area("格式：代號:成本:股數", default_portfolio, height=100)

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
        if curr > ma200: c3.success("✅ 多頭環境")
        else: c3.error("🚨 空頭環境")
except: pass

# --- 2. 核心分析表格 (包含垂直與水平比較) ---
@st.cache_data(ttl=1800)
def fetch_advanced_data(tickers):
    results = []
    # 用於計算行業平均的臨時存儲
    industry_pe = {}
    
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist_1y = tk.history(period="1y")
            
            # 垂直比較：目前的 PE 在過去一年的相對位置
            curr_pe = info.get('trailingPE')
            if curr_pe and not hist_1y.empty:
                pe_high = hist_1y['Close'].max() / (info.get('trailingEps') or 1)
                pe_low = hist_1y['Close'].min() / (info.get('trailingEps') or 1)
                pe_pos = (curr_pe - pe_low) / (pe_high - pe_low) if pe_high != pe_low else 0.5
                pe_status = "偏低" if pe_pos < 0.3 else ("過熱" if pe_pos > 0.7 else "合理")
            else:
                pe_status = "—"

            # 修復 PEG 跑掉的問題
            peg = info.get('pegRatio') or info.get('trailingPegRatio', '—')
            
            # 水平比較準備：記錄行業
            industry = info.get('industry', 'Other')
            
            results.append({
                "代號": s,
                "行業": industry,
                "PE (TTM)": round(curr_pe, 2) if curr_pe else "—",
                "歷史位階": pe_status,
                "PEG (修正)": round(peg, 2) if isinstance(peg, (int, float)) else "—",
                "ROE (%)": f"{round(info.get('returnOnEquity', 0)*100, 1)}%",
                "毛利率 (%)": f"{round(info.get('grossMargins', 0)*100, 1)}%",
                "營收成長 (%)": f"{round(info.get('revenueGrowth', 0)*100, 1)}%"
            })
        except: continue
    
    df = pd.DataFrame(results)
    return df

st.divider()
st.subheader("📊 專業版：垂直(歷史)與水平(行業)分析表")

with st.spinner('正在進行多維度分析...'):
    df_analyst = fetch_advanced_data(ticker_list)
    
    # 這裡顯示表格
    st.dataframe(df_analyst, use_container_width=True, hide_index=True)

# --- 3. 水平比較看板 (行業平均 PE) ---
st.divider()
st.subheader("⚖️ 行業水平對比 (Benchmark)")
if not df_analyst.empty:
    # 簡單計算表格內不同行業的平均 PE 作為 Benchmark
    temp_df = df_analyst[df_analyst['PE (TTM)'] != "—"].copy()
    temp_df['PE (TTM)'] = temp_df['PE (TTM)'].astype(float)
    industry_avg = temp_df.groupby('行業')['PE (TTM)'].mean().round(2)
    
    cols = st.columns(len(industry_avg))
    for i, (ind, avg) in enumerate(industry_avg.items()):
        cols[i].metric(f"{ind} 平均 PE", avg)

# --- 4. 投資組合損益 ---
st.divider()
st.subheader("💰 持股實時回報")
# (保留原有的持股損益計算邏輯...)
