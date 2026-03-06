import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁基礎配置 ---
st.set_page_config(page_title="專業股市戰情室 v12.0", layout="wide")
st.title("🏛️ 專業美股：精準財報對照與估值追蹤")

# --- 側邊欄：控制與勾選 ---
st.sidebar.header("⚙️ 觀測清單")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS, ORCL"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("🎨 繪圖指標勾選")
st.sidebar.info("💡 財報數據以官方公佈為準，估值數據為每日即時推算。")
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_pe = st.sidebar.checkbox("本益比 (PE - 每日推算)", value=True)
show_eps = st.sidebar.checkbox("每股盈餘 (EPS TTM - 財報)", value=True)
show_roe = st.sidebar.checkbox("ROE (% - 官方數據)", value=True)
show_gm = st.sidebar.checkbox("毛利率 (Gross Margin % - 財報)", value=True)

history_range = st.sidebar.selectbox("歷史數據跨度", ["3y", "5y", "10y"], index=1)
ma_window = st.sidebar.slider("趨勢平滑化 (MA天數)", 5, 120, 20)

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

st.divider()

# --- 2. 核心分析表格 (嚴格分離資料源) ---
@st.cache_data(ttl=1800)
def fetch_accurate_data(tickers):
    results = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist_1d = tk.history(period="1d")
            price = hist_1d['Close'].iloc[-1] if not hist_1d.empty else 0
            
            # 即時估值指標 (來自即時推算或官方 info)
            trailing_pe = info.get('trailingPE')
            fwd_pe = info.get('forwardPE')
            peg = info.get('pegRatio') or info.get('trailingPegRatio')
            
            # 財報靜態指標 (官方計算好的準確數字)
            roe = info.get('returnOnEquity')
            gm = info.get('grossMargins')
            
            results.append({
                "標的": s,
                "現價": f"${price:.2f}" if price else "—",
                "PE (即時)": round(trailing_pe, 2) if trailing_pe else "—",
                "Fwd PE": round(fwd_pe, 2) if fwd_pe else "—",
                "PEG": round(peg, 2) if isinstance(peg, (int, float)) else "—",
                "ROE (財報)": f"{round(roe * 100, 2)}%" if roe else "—",
                "毛利率 (財報)": f"{round(gm * 100, 2)}%" if gm else "—"
            })
        except: continue
    return pd.DataFrame(results)

st.subheader("📋 核心基本面快照 (官方數據校準)")
with st.spinner('獲取最新官方財務數據...'):
    df_snapshot = fetch_accurate_data(ticker_list)
    st.dataframe(df_snapshot, use_container_width=True, hide_index=True)

st.divider()

# --- 3. 動態繪圖邏輯 (防呆與極端值過濾) ---
st.subheader("📈 長線財務與估值趨勢對照")
target = st.selectbox("選擇深度分析標的", ticker_list)

if target:
    with st.spinner('整合歷史財報與每日股價...'):
        try:
            tk = yf.Ticker(target)
            # 取得移除時區的每日股價
            hist = tk.history(period=history_range)
            hist.index = hist.index.tz_localize(None)
            
            # 取得財報並移除時區
            q_fin = tk.quarterly_financials.T
            if not q_fin.empty: q_fin.index = q_fin.index.tz_localize(None)
            
            df = pd.DataFrame(index=hist.index)
            df['Price'] = hist['Close']
            
            def align_fin(series):
                if series is not None and not series.empty:
                    # 使用向前填充將每季公佈的財報數字對齊到每一天的股價上
                    return series.reindex(df.index, method='ffill')
                return None

            # 1. 直接取財報公佈的 EPS 計算真實 PE
            if 'Diluted EPS' in q_fin.columns or 'Basic EPS' in q_fin.columns:
                eps_col = 'Diluted EPS' if 'Diluted EPS' in q_fin.columns else 'Basic EPS'
                eps_ttm = q_fin[eps_col].rolling(4).sum()
                df['EPS'] = align_fin(eps_ttm)
                # 過濾極端 PE (排除 EPS 為負或極微小導致 PE 飆破天際的雜訊)
                raw_pe = df['Price'] / df['EPS']
                df['PE'] = raw_pe.where((raw_pe > 0) & (raw_pe < 500)) 

            # 2. 直接取財報計算毛利
            if 'Gross Profit' in q_fin.columns and 'Total Revenue' in q_fin.columns:
                df['GM'] = align_fin((q_fin['Gross Profit'] / q_fin['Total Revenue']) * 100)

            # 3. ROE 改抓 Yahoo 官方預算好的靜態值畫基準線，或直接從財報取淨利與總資產推算
            # 這裡為了保證數字合理，我們直接採用該公司當前的官方 ROE 畫一條基準線供參考
            info = tk.info
            official_roe = info.get('returnOnEquity', 0) * 100

            # --- 繪圖 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 左軸：股價與估值
            if show_price:
                fig.add_trace(go.Scatter(x=df.index, y=df['Price'], name="股價", line=dict(color='black', width=1.5)), secondary_y=False)
            if show_pe and 'PE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'].rolling(ma_window).mean(), name=f"PE ({ma_window}MA)", line=dict(color='orange', dash='dash')), secondary_y=False)
            
            # 右軸：財報比例
            if show_eps and 'EPS' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['EPS'], name="EPS (TTM)", line=dict(color='brown')), secondary_y=True)
            if show_gm and 'GM' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['GM'], name="毛利率 %", line=dict(color='green')), secondary_y=True)
            if show_roe and official_roe != 0:
                fig.add_hline(y=official_roe, line_dash="dot", line_color="blue", annotation_text=f"官方當前 ROE: {official_roe:.1f}%", secondary_y=True)

            fig.update_layout(title=f"{target} {history_range} 真實數據對照", hovermode="x unified", height=600)
            fig.update_yaxes(title_text="價格 (USD) / 本益比 (倍)", secondary_y=False)
            fig.update_yaxes(title_text="毛利率 (%) / EPS (USD)", secondary_y=True)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"分析繪圖異常：請確認該標的具有完整的財報歷史紀錄。")

st.caption(f"數據最後校準: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
