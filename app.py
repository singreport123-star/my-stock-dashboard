import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁基礎配置 ---
st.set_page_config(page_title="專業股市戰情室 v14.0", layout="wide")
st.title("🏛️ 專業美股：歷史盈餘與動態產業估值對照")

# --- 側邊欄：控制與勾選 ---
st.sidebar.header("⚙️ 觀測清單 (建議多放同業)")
st.sidebar.caption("💡 系統會根據此清單計算產業歷史平均，請盡量放入同業競爭者。")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS, ORCL, AMD, SMCI, INTC, TSM"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("🎨 繪圖指標勾選")
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_pe = st.sidebar.checkbox("個股 PE 趨勢 (含MA)", value=True)
show_ind_pe = st.sidebar.checkbox("產業歷史平均 PE走勢", value=True)
show_eps = st.sidebar.checkbox("歷史 EPS TTM (柱狀圖)", value=True)

history_range = st.sidebar.selectbox("歷史數據跨度", ["3y", "5y", "10y"], index=1)
ma_window = st.sidebar.slider("趨勢平滑化 (MA天數)", 5, 120, 20)

# --- 1. 核心基本面與產業分類快照 ---
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

# --- 2. 歷史 PE 與 EPS 提取引擎 ---
@st.cache_data(ttl=3600)
def get_historical_pe_eps(ticker, period):
    """ 強效提取單一股票的歷史 PE 序列與 EPS 序列 """
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=period)
        if hist.empty: return None, None
        hist.index = hist.index.tz_localize(None)
        
        q_fin = tk.quarterly_financials.T
        if q_fin.empty: return None, None
        q_fin.index = q_fin.index.tz_localize(None)
        q_fin = q_fin.sort_index() # 確保時間正序
        
        # 抓取 EPS
        eps_col = 'Diluted EPS' if 'Diluted EPS' in q_fin.columns else ('Basic EPS' if 'Basic EPS' in q_fin.columns else None)
        if not eps_col: return None, None
        
        eps_ttm = q_fin[eps_col].rolling(4).sum()
        
        # 對齊到每日股價
        df = pd.DataFrame(index=hist.index)
        df['Price'] = hist['Close']
        df['EPS'] = eps_ttm.reindex(df.index, method='ffill')
        
        # 計算 PE 並過濾雜訊
        pe = df['Price'] / df['EPS']
        pe = pe.where((pe > 0) & (pe < 500)) 
        
        return pe, df['EPS']
    except:
        return None, None

# --- 3. 動態繪圖邏輯 ---
st.subheader("📈 歷史盈餘與產業估值深度解析")
target = st.selectbox("選擇深度分析標的", ticker_list)

if target:
    with st.spinner(f'正在運算 {target} 及同業的歷史估值模型...'):
        try:
            # 1. 獲取目標個股的歷史資料
            target_tk = yf.Ticker(target)
            target_hist = target_tk.history(period=history_range)
            target_hist.index = target_hist.index.tz_localize(None)
            
            target_pe, target_eps = get_historical_pe_eps(target, history_range)
            
            # 2. 計算「動態產業平均 PE」
            target_industry = df_snapshot[df_snapshot['標的'] == target]['行業'].iloc[0] if not df_snapshot.empty else "Other"
            peer_tickers = df_snapshot[df_snapshot['行業'] == target_industry]['標的'].tolist()
            
            peer_pe_list = []
            for peer in peer_tickers:
                p_pe, _ = get_historical_pe_eps(peer, history_range)
                if p_pe is not None:
                    peer_pe_list.append(p_pe.rename(peer))
            
            # 將同業每天的 PE 結合成 DataFrame 並算平均
            ind_historical_pe = None
            if peer_pe_list:
                ind_pe_df = pd.concat(peer_pe_list, axis=1)
                ind_historical_pe = ind_pe_df.mean(axis=1)

            # --- 繪圖區 ---
            # 建立雙 Y 軸：左邊放股價與 PE，右邊放 EPS 柱狀圖
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # A. 股價 (左軸)
            if show_price:
                fig.add_trace(go.Scatter(x=target_hist.index, y=target_hist['Close'], name="股價", line=dict(color='black', width=1.5)), secondary_y=False)
            
            # B. 個股 PE (左軸)
            if show_pe and target_pe is not None:
                fig.add_trace(go.Scatter(x=target_pe.index, y=target_pe, name="個股 PE (每日真實)", line=dict(color='orange', width=1), opacity=0.3), secondary_y=False)
                fig.add_trace(go.Scatter(x=target_pe.index, y=target_pe.rolling(ma_window).mean(), name=f"個股 PE ({ma_window}MA)", line=dict(color='darkorange', width=2.5)), secondary_y=False)
            
            # C. 產業歷史平均 PE (左軸)
            if show_ind_pe and ind_historical_pe is not None:
                fig.add_trace(go.Scatter(x=ind_historical_pe.index, y=ind_historical_pe.rolling(ma_window).mean(), name=f"【{target_industry}】產業平均 PE走勢", line=dict(color='purple', width=2, dash='dashdot')), secondary_y=False)

            # D. 歷史 EPS TTM (右軸 - 柱狀圖 Bar Chart)
            if show_eps and target_eps is not None:
                fig.add_trace(go.Bar(x=target_eps.index, y=target_eps, name="EPS TTM (每股盈餘)", marker_color='rgba(50, 171, 96, 0.4)'), secondary_y=True)

            # 視覺優化
            fig.update_layout(title=f"{target} 歷史盈餘成長 vs 產業估值變遷", hovermode="x unified", height=650, barmode='overlay')
            fig.update_yaxes(title_text="價格 (USD) / 本益比 (倍)", secondary_y=False)
            fig.update_yaxes(title_text="EPS TTM (USD)", secondary_y=True, showgrid=False)
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"模型運算異常，可能是該公司早期歷史財報缺失。({e})")

st.caption(f"數據最後校準: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
