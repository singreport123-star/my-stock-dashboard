import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pytz

# --- 網頁基礎配置 ---
st.set_page_config(page_title="專業股市戰情室 v11.0", layout="wide")
st.title("🏛️ 專業美股：長線財務趨勢全方位對照")

# --- 側邊欄：進階繪圖控制 ---
st.sidebar.header("🎨 繪圖指標勾選")
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_pe = st.sidebar.checkbox("本益比 (PE)", value=True)
show_eps = st.sidebar.checkbox("每股盈餘 (EPS TTM)", value=True)
show_roe = st.sidebar.checkbox("ROE (%)", value=True)
show_gm = st.sidebar.checkbox("毛利率 (Gross Margin %)", value=True)
show_rev = st.sidebar.checkbox("營收 (Revenue)", value=False)
show_debt = st.sidebar.checkbox("負債權益比 (D/E)", value=False)

st.sidebar.divider()
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
        if curr > ma200: st.success("✅ 多頭環境")
        else: st.error("🚨 空頭環境")
except: pass

st.divider()

# --- 2. 動態多指標繪圖邏輯 (解決時區報錯) ---
st.sidebar.header("⚙️ 觀測清單")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS, ORCL"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.subheader("📈 全方位長線趨勢對照圖")
target = st.selectbox("選擇分析標的", ticker_list)

if target:
    with st.spinner(f'正在進行深度數據對齊與時區轉換...'):
        try:
            tk = yf.Ticker(target)
            # 抓取股價並強制移除時區，避免與財報對齊時報錯
            hist = tk.history(period=history_range)
            hist.index = hist.index.tz_localize(None)
            
            # 獲取財報並轉置
            q_fin = tk.quarterly_financials.T
            q_bs = tk.quarterly_balance_sheet.T
            # 財報日期也強制移除時區
            if not q_fin.empty: q_fin.index = q_fin.index.tz_localize(None)
            if not q_bs.empty: q_bs.index = q_bs.index.tz_localize(None)

            # --- 數據準備 ---
            df = pd.DataFrame(index=hist.index)
            df['Price'] = hist['Close']
            
            def safe_align(series):
                if series is not None and not series.empty:
                    return series.reindex(df.index, method='ffill')
                return None

            # 指標計算
            # EPS & PE
            if 'Basic EPS' in q_fin.columns:
                df['EPS'] = safe_align(q_fin['Basic EPS'].rolling(4).sum())
                df['PE'] = df['Price'] / df['EPS']
            
            # ROE
            if 'Net Income' in q_fin.columns and 'Total Stockholders Equity' in q_bs.columns:
                roe = (q_fin['Net Income'].rolling(4).sum() / q_bs['Total Stockholders Equity'].rolling(4).mean()) * 100
                df['ROE'] = safe_align(roe)
            
            # 毛利
            if 'Gross Profit' in q_fin.columns and 'Total Revenue' in q_fin.columns:
                df['GM'] = safe_align((q_fin['Gross Profit'] / q_fin['Total Revenue']) * 100)
            
            # 營收與負債
            if 'Total Revenue' in q_fin.columns: df['Revenue'] = safe_align(q_fin['Total Revenue'])
            if 'Total Debt' in q_bs.columns and 'Total Stockholders Equity' in q_bs.columns:
                df['DE'] = safe_align(q_bs['Total Debt'] / q_bs['Total Stockholders Equity'])

            # --- 繪圖 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 左軸：數值較大的指標
            if show_price:
                fig.add_trace(go.Scatter(x=df.index, y=df['Price'], name="股價", line=dict(color='black', width=1.5)), secondary_y=False)
            if show_pe and 'PE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'].rolling(ma_window).mean(), name=f"PE ({ma_window}MA)", line=dict(color='orange', dash='dash')), secondary_y=False)
            if show_rev and 'Revenue' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['Revenue'], name="營收", line=dict(color='purple', opacity=0.3)), secondary_y=False)
            
            # 右軸：比例與倍數指標
            if show_roe and 'ROE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['ROE'], name="ROE %", line=dict(color='blue')), secondary_y=True)
            if show_gm and 'GM' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['GM'], name="毛利率 %", line=dict(color='green')), secondary_y=True)
            if show_debt and 'DE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['DE'], name="負債比 (D/E)", line=dict(color='red', dash='dot')), secondary_y=True)
            if show_eps and 'EPS' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['EPS'], name="EPS TTM", line=dict(color='brown')), secondary_y=True)

            fig.update_layout(title=f"{target} {history_range} 財務與估值趨勢全觀", hovermode="x unified", height=700)
            fig.update_yaxes(title_text="價格 / PE", secondary_y=False)
            fig.update_yaxes(title_text="百分比 / 倍數 / EPS", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"數據對齊異常：{e}。這通常是因為該標的在所選區間內財報欄位不完整。")

st.caption(f"數據最後更新 (Taipei): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
