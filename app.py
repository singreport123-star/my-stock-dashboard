import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室 v5.1", layout="wide")
st.title("🚀 專業美股基本面：長期歷史(3Y)與同業對照")

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

# --- 2. 核心分析邏輯：3年歷史與同業對照 ---
@st.cache_data(ttl=1800)
def fetch_longterm_compare_data(tickers):
    raw_results = []
    industry_pe_map = {}
    
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            # 將歷史區間拉長至 3 年
            hist_3y = tk.history(period="3y")
            
            # 股價與基本面
            price = hist_3y['Close'].iloc[-1] if not hist_3y.empty else 0
            curr_pe = info.get('trailingPE')
            eps = info.get('trailingEps') or 1
            
            # 計算 3 年內的 PE 最高與最低點
            if not hist_3y.empty:
                pe_3y_high = round(hist_3y['Close'].max() / eps, 1)
                pe_3y_low = round(hist_3y['Close'].min() / eps, 1)
            else:
                pe_3y_high, pe_3y_low = "—", "—"
            
            industry = info.get('industry', 'ETF/Other')
            
            raw_results.append({
                "標的": s,
                "現價": price,
                "PE (現)": curr_pe,
                "3年PE高點": pe_3y_high,
                "3年PE低點": pe_3y_low,
                "行業": industry,
                "PEG": info.get('pegRatio') or info.get('trailingPegRatio'),
                "ROE (%)": info.get('returnOnEquity'),
                "毛利 (%)": info.get('grossMargins'),
                "市值 (B)": info.get('marketCap', 0) / 1e9
            })
            
            # 累積同業數據用於水平比較
            if curr_pe and industry != 'ETF/Other':
                if industry not in industry_pe_map: industry_pe_map[industry] = []
                industry_pe_map[industry].append(curr_pe)
        except: continue
    
    # 計算同業平均 PE
    industry_avg = {k: sum(v)/len(v) for k, v in industry_pe_map.items()}
    
    final_data = []
    for item in raw_results:
        avg_pe = industry_avg.get(item["行業"], 0)
        
        final_data.append({
            "標的": item["標的"],
            "現價": f"${item['現價']:.2f}",
            "PE (現)": f"{item['PE (現)']:.1f}" if item['PE (現)'] else "—",
            "3年PE區間 (高/低)": f"{item['3年PE高點']} / {item['3年PE低點']}",
            "同業平均PE": f"{avg_pe:.1f}" if avg_pe > 0 else "—",
            "PEG": round(item["PEG"], 2) if isinstance(item["PEG"], (int, float)) else "—",
            "ROE": f"{round(item['ROE (%)']*100, 1)}%" if item['ROE (%)'] else "—",
            "毛利": f"{round(item['毛利 (%)']*100, 1)}%" if item['毛利 (%)'] else "—",
            "市值(B)": f"{item['市值 (B)']:.1f}B",
            "行業": item["行業"]
        })
    return pd.DataFrame(final_data)

st.subheader("📊 專業數據表：3年歷史位階與同業水平對照")
with st.spinner('正在分析長期估值數據...'):
    df = fetch_longterm_compare_data(ticker_list)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("""
> **📈 垂直分析（歷史）**：觀察『PE (現)』在 3 年高低區間的位置。若接近低點，代表估值處於近年低位。
> **📉 水平分析（同業）**：對比『同業平均PE』。大幅高於同業可能代表溢價過高，大幅低於則可能具備補漲潛力。
""")

st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
