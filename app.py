import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業股市戰情室", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄控制 ---
st.sidebar.header("⚙️ 控制面板")
# 你隨時可以在這裡修改預設清單，或在網頁上直接增減
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("自定義觀測代號 (以逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# 個人持股設定
st.sidebar.divider()
st.sidebar.subheader("💰 個人持股設定")
hims_cost = st.sidebar.number_input("HIMS 買入單價 (USD)", value=37.90)
hims_qty = st.sidebar.number_input("HIMS 持有股數", value=35)

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

# --- 2. HIMS 持股損益區 (針對你的持倉) ---
if "HIMS" in ticker_list:
    st.subheader("📊 HIMS 投資回報監控")
    try:
        h_tk = yf.Ticker("HIMS")
        h_hist = h_tk.history(period="1d")
        if not h_hist.empty:
            h_price = h_hist['Close'].iloc[-1]
            total_cost = hims_cost * hims_qty
            current_value = h_price * hims_qty
            total_profit = current_value - total_cost
            profit_percent = (total_profit / total_cost) * 100
            
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("HIMS 目前市價", f"${h_price:.2f}")
            # 根據損益正負顯示顏色
            pc2.metric("預估總損益 (USD)", f"${total_profit:.2f}", f"{profit_percent:.2f}%")
            pc3.info(f"持有股數: {hims_qty} | 總成本: ${total_cost:.2f}")
            st.divider()
    except:
        st.write("暫時無法取得 HIMS 即時數據。")

# --- 3. 基本面數據列表 ---
@st.cache_data(ttl=1800)
def fetch_basic_data(tickers):
    data = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # PEG 抓取邏輯
            peg = info.get('pegRatio') or info.get('trailingPegRatio', '—')
            
            data.append({
                "標的": s,
                "名稱": info.get('shortName', 'N/A'),
                "現價": f"${price:.2f}" if price > 0 else "N/A",
                "PE (本益比)": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "Forward PE": round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "—",
                "PEG": round(peg, 2) if isinstance(peg, (int, float)) else peg,
                "市值 (B)": f"{round(info.get('marketCap', 0)/1e9, 2)}B" if info.get('marketCap') else "—"
            })
        except:
            continue
    return pd.DataFrame(data)

st.subheader("📊 個股基本面概覽")
with st.spinner('正在同步市場最新數據...'):
    df = fetch_basic_data(ticker_list)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
