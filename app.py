import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室 v10.0", layout="wide")
st.title("🏛️ 專業美股：全指標長線財務趨勢對照")

# --- 側邊欄：進階繪圖勾選 ---
st.sidebar.header("🎨 繪圖指標勾選")
# 價格與估值
show_price = st.sidebar.checkbox("股價 (Price)", value=True)
show_pe = st.sidebar.checkbox("本益比 (PE)", value=True)
show_eps = st.sidebar.checkbox("每股盈餘 (EPS TTM)", value=False)
# 獲利與競爭力
show_roe = st.sidebar.checkbox("ROE (%)", value=True)
show_gm = st.sidebar.checkbox("毛利率 (Gross Margin %)", value=True)
show_rev = st.sidebar.checkbox("營收 (Revenue)", value=False)
# 財務穩健度
show_debt = st.sidebar.checkbox("負債權益比 (D/E)", value=False)

st.sidebar.divider()
history_range = st.sidebar.selectbox("歷史數據跨度", ["3y", "5y", "10y"], index=1)
ma_window = st.sidebar.slider("移動平均天數 (MA)", 5, 120, 20)

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

# --- 2. 動態多指標繪圖邏輯 ---
st.sidebar.header("⚙️ 觀測清單")
default_list = "NVDA, MSFT, TSLA, AAPL, HIMS"
user_input = st.sidebar.text_area("代號輸入", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.subheader("📈 全方位長線趨勢對照圖")
target = st.selectbox("選擇分析標的", ticker_list)

if target:
    with st.spinner(f'正在深度掃描 {target} 的全球財報數據...'):
        try:
            tk = yf.Ticker(target)
            hist = tk.history(period=history_range)
            # 獲取年度與季度財報
            q_fin = tk.quarterly_financials.T
            q_bs = tk.quarterly_balance_sheet.T
            
            # --- 數據安全抓取與對齊 ---
            df = hist[['Close']].copy()
            df.columns = ['Price']
            
            # 輔助函數：將季報數據對齊至每日股價
            def align_data(series):
                if series is not None and not series.empty:
                    return series.reindex(df.index, method='ffill')
                return None

            # 計算各項指標 (TTM 滾動概念)
            # EPS & PE
            eps_ttm = align_data(q_fin['Basic EPS'].rolling(4).sum()) if 'Basic EPS' in q_fin.columns else None
            if eps_ttm is not None:
                df['EPS'] = eps_ttm
                df['PE'] = df['Price'] / eps_ttm
            
            # ROE
            if 'Net Income' in q_fin.columns and 'Total Stockholders Equity' in q_bs.columns:
                roe = (q_fin['Net Income'].rolling(4).sum() / q_bs['Total Stockholders Equity'].rolling(4).mean()) * 100
                df['ROE'] = align_data(roe)
            
            # Gross Margin
            if 'Gross Profit' in q_fin.columns and 'Total Revenue' in q_fin.columns:
                gm = (q_fin['Gross Profit'] / q_fin['Total Revenue']) * 100
                df['GM'] = align_data(gm)
                
            # Revenue
            if 'Total Revenue' in q_fin.columns:
                df['Revenue'] = align_data(q_fin['Total Revenue'])
                
            # Debt/Equity
            if 'Total Debt' in q_bs.columns and 'Total Stockholders Equity' in q_bs.columns:
                de = q_bs['Total Debt'] / q_bs['Total Stockholders Equity']
                df['DE'] = align_data(de)

            # --- 繪圖實作 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 股價與 PE 屬於數值較大的指標，放在左軸
            if show_price:
                fig.add_trace(go.Scatter(x=df.index, y=df['Price'], name="股價", line=dict(color='black', width=1.5)), secondary_y=False)
            if show_pe and 'PE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['PE'].rolling(ma_window).mean(), name=f"PE ({ma_window}MA)", line=dict(color='orange', dash='dash')), secondary_y=False)
            if show_rev and 'Revenue' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['Revenue'], name="營收 (左軸)", line=dict(color='purple', opacity=0.3)), secondary_y=False)
            
            # 百分比與倍數指標，放在右軸
            if show_roe and 'ROE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['ROE'], name="ROE % (右軸)", line=dict(color='blue')), secondary_y=True)
            if show_gm and 'GM' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['GM'], name="毛利率 % (右軸)", line=dict(color='green')), secondary_y=True)
            if show_debt and 'DE' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['DE'], name="負債比 (右軸)", line=dict(color='red', dash='dot')), secondary_y=True)
            if show_eps and 'EPS' in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df['EPS'], name="EPS TTM (右軸)", line=dict(color='brown')), secondary_y=True)

            fig.update_layout(title=f"{target} 長線財務趨勢全觀", hovermode="x unified", height=700)
            fig.update_yaxes(title_text="價格 / PE / 營收", secondary_y=False)
            fig.update_yaxes(title_text="百分比 / 倍數 / EPS", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"該標的數據處理異常：{e}。部分指標可能因財報格式特殊無法顯示。")

st.caption(f"數據最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
