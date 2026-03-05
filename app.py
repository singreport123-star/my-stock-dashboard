import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁基礎設定 ---
st.set_page_config(page_title="自定義美股觀測站", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄：動態輸入標的 ---
st.sidebar.header("控制面板")
# 預設標的字串
default_tickers = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("請輸入美股代號 (用逗號分隔)", default_tickers)
# 將字串轉為列表並去空格
tickers = [t.strip().upper() for t in user_input.split(",")]

# --- 1. TQQQ 輪動策略區 ---
def render_strategy():
    try:
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="1y")
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            diff = ((current_price - ma200) / ma200) * 100
            
            st.subheader("💡 交易策略警示 (TQQQ 輪動)")
            c1, c2, c3 = st.columns(3)
            c1.metric("QQQ 現價", f"${current_price:.2f}")
            c2.metric("QQQ 200MA", f"${ma200:.2f}", f"{diff:.2f}%")
            if current_price > ma200:
                c3.success("✅ 訊號：多頭")
            else:
                c3.error("🚨 訊號：空頭")
    except:
        st.error("策略數據更新中...")

render_strategy()
st.divider()

# --- 2. 核心數據抓取 ---
@st.cache_data(ttl=1800)
def get_stock_data(symbol_list):
    all_data = []
    for s in symbol_list:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else info.get('currentPrice', 0)
            
            is_etf = info.get('quoteType') in ['ETF', 'FUND']
            peg = info.get("pegRatio") if info.get("pegRatio") else info.get("trailingPegRatio", "—")
            
            all_data.append({
                "標的": s,
                "名稱": info.get("shortName", "N/A"),
                "現價": price,
                "PE": info.get("trailingPE", "—"),
                "Fwd PE": info.get("forwardPE", "—"),
                "PEG": peg,
                "市值(B)": round(info.get('marketCap', 0)/1e9, 1) if info.get('marketCap') else "—"
            })
        except:
            continue
    return pd.DataFrame(all_data)

# --- 3. 顯示數據表 ---
st.subheader("📊 基本面概覽")
df = get_stock_data(tickers)
if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.warning("請在左側輸入正確的代號")

# --- 4. 個股新聞模組 (新增功能) ---
st.divider()
st.subheader("📰 最新個股相關新聞")
selected_stock = st.selectbox("選擇要查看新聞的標的", tickers)

if selected_stock:
    news_tk = yf.Ticker(selected_stock)
    news_list = news_tk.news[:5] # 抓取前 5 則新聞
    if news_list:
        for item in news_list:
            with st.expander(item['title']):
                st.write(f"來源: {item['publisher']}")
                st.write(f"時間: {datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d %H:%M')}")
                st.markdown(f"[閱讀全文]({item['link']})")
    else:
        st.write("目前暫無即時新聞。")

st.caption(f"最後更新: {datetime.now().strftime('%H:%M:%S')}")
