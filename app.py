import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄控制 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("自定義觀測代號", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# 持股成本設定 (以 HIMS 為例)
st.sidebar.divider()
st.sidebar.subheader("💰 我的持股成本")
# 根據你的紀錄，買入成本約為 $37.90，持有 35 股
hims_cost = st.sidebar.number_input("HIMS 成本價", value=37.90)
hims_qty = st.sidebar.number_input("HIMS 股數", value=35)

# --- 1. TQQQ 輪動策略警示 ---
try:
    qqq = yf.Ticker("QQQ")
    hist_q = qqq.history(period="1y")
    if not hist_q.empty:
        curr = hist_q['Close'].iloc[-1]
        ma200 = hist_q['Close'].rolling(window=200).mean().iloc[-1]
        st.subheader("💡 策略警示 (TQQQ 輪動)")
        c1, c2, c3 = st.columns(3)
        c1.metric("QQQ 現價", f"${curr:.2f}")
        c2.metric("QQQ 200MA", f"${ma200:.2f}")
        if curr > ma200:
            c3.success("✅ 訊號：多頭 (站上 200MA)")
        else:
            c3.error("🚨 訊號：空頭 (跌破 200MA)")
except:
    st.warning("策略數據更新中...")

st.divider()

# --- 2. 持股損益計算 (New!) ---
if "HIMS" in ticker_list:
    st.subheader("📊 我的投資組合損益")
    try:
        h_tk = yf.Ticker("HIMS")
        h_price = h_tk.history(period="1d")['Close'].iloc[-1]
        profit = (h_price - hims_cost) * hims_qty
        p_percent = ((h_price / hims_cost) - 1) * 100
        
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("HIMS 目前市價", f"${h_price:.2f}")
        pc2.metric("預估損益 (USD)", f"${profit:.2f}", f"{p_percent:.2f}%")
        pc3.info(f"持有股數: {hims_qty}")
        st.divider()
    except:
        st.write("暫時無法取得 HIMS 即時報價。")

# --- 3. 本益比河流圖 (曲線進化版) ---
st.subheader("🌊 本益比河流圖 (PE Band)")
chart_target = st.selectbox("選擇要繪圖的標的", [t for t in ticker_list if t not in ["VOO", "QQQM", "IBIT"]])

if chart_target:
    try:
        tk = yf.Ticker(chart_target)
        # 抓取 3 年歷史價格
        hist = tk.history(period="3y")
        
        # 抓取財報中的每季 EPS 並計算 TTM
        fin = tk.quarterly_financials
        if 'Basic EPS' in fin.index:
            # 獲取歷史 EPS 序列並對齊股價日期
            eps_series = fin.loc['Basic EPS'].iloc[::-1].rolling(4).sum().dropna()
            
            if not eps_series.empty:
                # 重新採樣 EPS 以對齊每日股價
                eps_df = pd.DataFrame(eps_series).rename(columns={'Basic EPS': 'EPS'})
                plot_df = hist[['Close']].join(eps_df, how='ffill').fillna(method='ffill')
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Close'], name='股價', line=dict(color='black', width=2)))
                
                # 河流倍數：NVDA 高估值處理，其他標的採常用倍數
                multipliers = [30, 50, 70, 90, 110] if chart_target == "NVDA" else [15, 20, 25, 30, 35]
                
                for m in multipliers:
                    fig.add_trace(go.Scatter(
                        x=plot_df.index, 
                        y=plot_df['EPS'] * m, 
                        name=f'{m}x PE',
                        line=dict(dash='dash', width=1),
                        opacity=0.6
                    ))
                
                fig.update_layout(title=f"{chart_target} 估值河流圖 (TTM EPS 版)", hovermode="x unified")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("該標的歷史 EPS 數據不足，無法繪製河流曲線。")
        else:
            st.warning("該標的財報中缺乏 EPS 數據。")
    except Exception as e:
        st.error(f"河流圖繪製失敗，可能是財報格式不符。")

st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
