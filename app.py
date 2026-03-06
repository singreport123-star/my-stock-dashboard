import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁基礎配置 ---
st.set_page_config(page_title="專業股市戰情室 v15.0", layout="wide")
st.title("🏛️ 專業美股：歷史盈餘與產業估值全解析")

# --- 側邊欄：控制與勾選 ---
st.sidebar.header("⚙️ 觀測清單 (建議多放同業)")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS, ORCL, AMD, SMCI, INTC, TSM"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("🎨 繪圖指標勾選")
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_eps = st.sidebar.checkbox("歷史 EPS (柱狀圖)", value=True)
show_pe = st.sidebar.checkbox("個股 PE 趨勢 (含MA)", value=True)
show_ind_pe = st.sidebar.checkbox("產業歷史平均 PE 走勢", value=True)

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
            
            industry = info.get('industry', 'Other')
            results.append({
                "標的": s,
                "行業": industry,
                "現價": f"${price:.2f}" if price else "—",
                "PE (即時)": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "ROE": f"{round(info.get('returnOnEquity', 0) * 100, 2)}%" if info.get('returnOnEquity') else "—"
            })
        except: continue
    return pd.DataFrame(results)

st.subheader("📋 觀測清單與產業矩陣")
with st.spinner('獲取最新官方財務數據...'):
    df_snapshot = fetch_accurate_data(ticker_list)
    st.dataframe(df_snapshot, use_container_width=True, hide_index=True)

st.divider()

# --- 2. 歷史 PE 與 EPS 提取引擎 (修復資料缺失問題) ---
@st.cache_data(ttl=3600)
def get_historical_pe_eps(ticker, period):
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period)
        if hist.empty: return None, None
        hist.index = hist.index.tz_localize(None).normalize()
        
        # 💡 修正 1：改用年度財報抓取長期歷史 EPS
        a_fin = tk.financials.T
        eps_series = pd.Series(dtype=float)
        
        if not a_fin.empty:
            a_fin.index = a_fin.index.tz_localize(None).normalize()
            a_fin = a_fin.sort_index()
            eps_col = 'Diluted EPS' if 'Diluted EPS' in a_fin.columns else ('Basic EPS' if 'Basic EPS' in a_fin.columns else None)
            if eps_col:
                eps_series = a_fin[eps_col].dropna()

        # 💡 修正 2：補上當下最新的 TTM EPS，完美接合
        current_eps = tk.info.get('trailingEps')
        if current_eps:
            eps_series.loc[pd.Timestamp.today().normalize()] = current_eps

        if eps_series.empty: return None, None
        eps_series = eps_series.sort_index()

        # 💡 修正 3：安全地將財報數據對齊到每個交易日
        df = pd.DataFrame(index=hist.index)
        df['Price'] = hist['Close']
        
        combined_index = df.index.union(eps_series.index).sort_values()
        temp_df = pd.DataFrame(index=combined_index)
        temp_df['EPS'] = eps_series
        temp_df['EPS'] = temp_df['EPS'].ffill().bfill()
        
        df['EPS'] = temp_df['EPS'].loc[df.index]
        
        # 計算 PE 並過濾異常雜訊
        pe = df['Price'] / df['EPS']
        pe = pe.where((pe > 0) & (pe < 500)) 
        
        return pe, df['EPS']
    except Exception as e:
        return None, None

# --- 3. 動態雙視窗繪圖邏輯 ---
st.subheader("📈 股價盈餘與估值背離分析")
target = st.selectbox("選擇深度分析標的", ticker_list)

if target:
    with st.spinner(f'正在重建 {target} 及同業的歷史估值模型...'):
        try:
            target_tk = yf.Ticker(target)
            target_hist = target_tk.history(period=history_range)
            target_hist.index = target_hist.index.tz_localize(None).normalize()
            
            target_pe, target_eps = get_historical_pe_eps(target, history_range)
            
            # 計算動態產業平均 PE
            target_industry = df_snapshot[df_snapshot['標的'] == target]['行業'].iloc[0] if not df_snapshot.empty else "Other"
            peer_tickers = df_snapshot[df_snapshot['行業'] == target_industry]['標的'].tolist()
            
            peer_pe_list = []
            for peer in peer_tickers:
                p_pe, _ = get_historical_pe_eps(peer, history_range)
                if p_pe is not None:
                    peer_pe_list.append(p_pe.rename(peer))
            
            ind_historical_pe = None
            if peer_pe_list:
                ind_pe_df = pd.concat(peer_pe_list, axis=1)
                ind_historical_pe = ind_pe_df.mean(axis=1)

            # --- 💡 繪圖區：切割上下兩層 (Subplots) ---
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True,           # 上下共用 X 軸 (時間)
                vertical_spacing=0.08,       # 上下圖間距
                row_heights=[0.6, 0.4],      # 上圖佔 60%，下圖佔 40%
                specs=[[{"secondary_y": True}], # 上圖可有雙 Y 軸 (股價與 EPS)
                       [{"secondary_y": False}]] # 下圖單 Y 軸 (專看 PE)
            )
            
            # 【上層圖表】：股價 vs EPS 柱狀圖
            if show_price:
                fig.add_trace(go.Scatter(x=target_hist.index, y=target_hist['Close'], name="股價", line=dict(color='black', width=1.5)), row=1, col=1, secondary_y=False)
            if show_eps and target_eps is not None:
                fig.add_trace(go.Bar(x=target_eps.index, y=target_eps, name="歷史 EPS", marker_color='rgba(50, 171, 96, 0.3)'), row=1, col=1, secondary_y=True)

            # 【下層圖表】：個股 PE vs 產業 PE
            if show_pe and target_pe is not None:
                fig.add_trace(go.Scatter(x=target_pe.index, y=target_pe, name="個股 PE (每日真實)", line=dict(color='orange', width=1), opacity=0.3), row=2, col=1)
                fig.add_trace(go.Scatter(x=target_pe.index, y=target_pe.rolling(ma_window).mean(), name=f"個股 PE ({ma_window}MA)", line=dict(color='darkorange', width=2.5)), row=2, col=1)
            
            if show_ind_pe and ind_historical_pe is not None:
                fig.add_trace(go.Scatter(x=ind_historical_pe.index, y=ind_historical_pe.rolling(ma_window).mean(), name=f"【{target_industry}】產業平均 PE", line=dict(color='purple', width=2, dash='dashdot')), row=2, col=1)

            # 視覺與版面優化
            fig.update_layout(title=f"{target} 專業估值儀表板 (雙視窗分離)", hovermode="x unified", height=750, barmode='overlay')
            
            # Y 軸標籤設定
            fig.update_yaxes(title_text="價格 (USD)", row=1, col=1, secondary_y=False)
            fig.update_yaxes(title_text="EPS (USD)", row=1, col=1, secondary_y=True, showgrid=False)
            fig.update_yaxes(title_text="本益比 (倍)", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"模型運算異常，請稍後再試。({e})")

st.caption(f"數據最後校準: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
