import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁基礎配置 ---
st.set_page_config(page_title="專業股市戰情室 v13.0", layout="wide")
st.title("🏛️ 專業美股：精準財報對照與產業估值")

# --- 側邊欄：控制與勾選 ---
st.sidebar.header("⚙️ 觀測清單")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS, ORCL, AMD, SMCI"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("🎨 繪圖指標勾選")
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_pe = st.sidebar.checkbox("本益比 (每日真實 + MA趨勢)", value=True)
show_eps = st.sidebar.checkbox("每股盈餘 (EPS TTM)", value=True)
show_roe = st.sidebar.checkbox("ROE (%)", value=True)
show_gm = st.sidebar.checkbox("毛利率 (Gross Margin %)", value=True)

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

# --- 2. 核心分析表格 (新增產業分類) ---
@st.cache_data(ttl=1800)
def fetch_accurate_data(tickers):
    results = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist_1d = tk.history(period="1d")
            price = hist_1d['Close'].iloc[-1] if not hist_1d.empty else 0
            
            trailing_pe = info.get('trailingPE')
            fwd_pe = info.get('forwardPE')
            industry = info.get('industry', 'Other')
            
            results.append({
                "標的": s,
                "行業": industry,
                "現價": f"${price:.2f}" if price else "—",
                "PE (即時)": round(trailing_pe, 2) if trailing_pe else "—",
                "Fwd PE": round(fwd_pe, 2) if fwd_pe else "—",
                "ROE (財報)": f"{round(info.get('returnOnEquity', 0) * 100, 2)}%" if info.get('returnOnEquity') else "—",
                "毛利率 (財報)": f"{round(info.get('grossMargins', 0) * 100, 2)}%" if info.get('grossMargins') else "—"
            })
        except: continue
    return pd.DataFrame(results)

st.subheader("📋 核心基本面快照")
with st.spinner('獲取最新官方財務數據...'):
    df_snapshot = fetch_accurate_data(ticker_list)
    st.dataframe(df_snapshot, use_container_width=True, hide_index=True)

st.divider()

# --- 3. 動態繪圖邏輯 (嚴格時序校準) ---
st.subheader("📈 長線財務與估值趨勢對照")
target = st.selectbox("選擇深度分析標的", ticker_list)

if target:
    with st.spinner('進行嚴格的時序校準與資料對齊...'):
        try:
            tk = yf.Ticker(target)
            target_info = tk.info
            target_industry = target_info.get('industry', 'Other')
            
            # 從表格數據中計算同業平均 PE
            pe_series = df_snapshot[df_snapshot['行業'] == target_industry]['PE (即時)']
            pe_series = pd.to_numeric(pe_series, errors='coerce').dropna()
            ind_avg_pe = pe_series.mean() if not pe_series.empty else None

            # 取得移除時區的每日股價
            hist = tk.history(period=history_range)
            hist.index = hist.index.tz_localize(None)
            
            # 取得財報並移除時區，最重要的是：強制按時間正序排列！
            q_fin = tk.quarterly_financials.T
            if not q_fin.empty:
                q_fin.index = q_fin.index.tz_localize(None)
                q_fin = q_fin.sort_index()  # 💡 修正 BUG：確保從最舊排到最新
            
            df = pd.DataFrame(index=hist.index)
            df['Price'] = hist['Close']
            
            def align_fin(series):
                if series is not None and not series.empty:
                    # 向前填充：確保過去的股價只能用到當時已公布的財報數字
                    return series.reindex(df.index, method='ffill')
                return None

            # 重新計算 EPS TTM 與 PE
            if 'Diluted EPS' in q_fin.columns or 'Basic EPS' in q_fin.columns:
                eps_col = 'Diluted EPS' if 'Diluted EPS' in q_fin.columns else 'Basic EPS'
                eps_ttm = q_fin[eps_col].rolling(4).sum()
                df['EPS'] = align_fin(eps_ttm)
                
                raw_pe = df['Price'] / df['EPS']
                df['PE'] = raw_pe.where((raw_pe > 0) & (raw_pe < 500)) 

            if 'Gross Profit' in q_fin.columns and 'Total Revenue' in q_fin.columns:
                df['GM'] = align_fin((q_fin['Gross Profit'] / q_fin['Total Revenue']) * 100)

            official_roe = target_info.get('returnOnEquity', 0) * 100

            # --- 繪圖 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 股價
            if show_price:
                fig.add_trace(go.Scatter(x=df.index, y=df['Price'], name="股價", line=dict(color='black', width=1.5)), secondary_y=False)
            
            # 歷史 PE 走勢與產業平均
            if show_pe and 'PE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'], name="PE (每日真實)", line=dict(color='orange', width=1), opacity=0.4), secondary_y=False)
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'].rolling(ma_window).mean(), name=f"PE ({ma_window}MA 趨勢)", line=dict(color='darkorange', width=2.5)), secondary_y=False)
                
                # 💡 新增：同業平均 PE 參考線
                if ind_avg_pe and not pd.isna(ind_avg_pe):
                    fig.add_hline(y=ind_avg_pe, line_dash="dashdot", line_color="purple", annotation_text=f"{target_industry} 同業平均 PE: {ind_avg_pe:.1f}", secondary_y=False)
            
            # 財報比例 (右軸)
            if show_eps and 'EPS' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['EPS'], name="EPS (TTM)", line=dict(color='brown')), secondary_y=True)
            if show_gm and 'GM' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['GM'], name="毛利率 %", line=dict(color='green')), secondary_y=True)
            if show_roe and official_roe != 0:
                fig.add_hline(y=official_roe, line_dash="dot", line_color="blue", annotation_text=f"官方當前 ROE: {official_roe:.1f}%", secondary_y=True)

            fig.update_layout(title=f"{target} 真實歷史估值與產業對照", hovermode="x unified", height=600)
            fig.update_yaxes(title_text="價格 (USD) / 本益比 (倍)", secondary_y=False)
            fig.update_yaxes(title_text="毛利率 (%) / EPS (USD)", secondary_y=True)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"分析繪圖異常：請確認該標的具有完整的財報歷史紀錄。({e})")

st.caption(f"數據最後校準: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
