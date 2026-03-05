import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室 v4.5", layout="wide")
st.title("🏛️ 專業美股：個股與同業/歷史一體化對照")

# --- 側邊欄 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("觀測代號 (以逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

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

# --- 2. 核心分析邏輯：一體化對照 ---
@st.cache_data(ttl=1800)
def fetch_integrated_data(tickers):
    raw_results = []
    industry_pe_map = {}
    
    # 第一輪：抓取數據並計算行業平均
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            is_etf = info.get('quoteType') in ['ETF', 'FUND']
            
            # 抓取 PEG (多重備援)
            peg = info.get('pegRatio') or info.get('trailingPegRatio', None)
            
            # 垂直比較：計算歷史位階 (過去一年 PE 區間)
            curr_pe = info.get('trailingPE')
            pe_rank = "—"
            if curr_pe and not is_etf:
                hist_1y = tk.history(period="1y")
                eps = info.get('trailingEps') or 1
                pe_high = hist_1y['Close'].max() / eps
                pe_low = hist_1y['Close'].min() / eps
                # 計算百分位
                rank_val = (curr_pe - pe_low) / (pe_high - pe_low) if pe_high != pe_low else 0.5
                pe_rank = f"{int(rank_val * 100)}%" # 0% 為最便宜，100% 為最貴

            industry = info.get('industry', 'ETF/Other')
            
            raw_results.append({
                "標的": s,
                "行業": industry,
                "PE (TTM)": curr_pe,
                "歷史位階 (0%=最便宜)": pe_rank,
                "PEG": peg,
                "ROE (%)": info.get('returnOnEquity'),
                "毛利率 (%)": info.get('grossMargins')
            })
            
            # 累計行業 PE 用於水平比較
            if curr_pe and not is_etf:
                if industry not in industry_pe_map: industry_pe_map[industry] = []
                industry_pe_map[industry].append(curr_pe)
        except: continue
    
    # 計算行業平均 PE
    industry_avg = {k: sum(v)/len(v) for k, v in industry_pe_map.items()}
    
    # 第二輪：格式化最終表格
    final_data = []
    for item in raw_results:
        ind = item["行業"]
        avg_pe = industry_avg.get(ind, None)
        
        # 計算與行業平均的偏離度
        if item["PE (TTM)"] and avg_pe:
            diff = ((item["PE (TTM)"] / avg_pe) - 1) * 100
            peer_compare = f"{'+' if diff > 0 else ''}{int(diff)}% (vs同業)"
        else:
            peer_compare = "—"

        final_data.append({
            "標的": item["標的"],
            "現價PE": f"{item['PE (TTM)']:.1f}" if item['PE (TTM)'] else "—",
            "歷史位階": item["歷史位階 (0%=最便宜)"],
            "水平比較": peer_compare,
            "PEG": round(item["PEG"], 2) if isinstance(item["PEG"], (int, float)) else "—",
            "ROE": f"{round(item['ROE (%)']*100, 1)}%" if item['ROE (%)'] else "—",
            "毛利": f"{round(item['毛利率 (%)']*100, 1)}%" if item['毛利率 (%)'] else "—",
            "行業": ind
        })
    
    return pd.DataFrame(final_data)

st.subheader("📊 專業分析師對照表 (個股 vs 歷史 vs 行業)")
with st.spinner('正在進行垂直與水平交叉分析...'):
    df = fetch_integrated_data(ticker_list)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.info("💡 **如何閱讀此表？**\n"
        "- **歷史位階**：靠近 0% 代表目前處於年度低估區；靠近 100% 代表相對歷史較貴。\n"
        "- **水平比較**：顯示該股比同業平均貴(正數)或便宜(負數)多少。")

st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
