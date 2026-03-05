import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁設定 ---
st.set_page_config(page_title="我的美股戰情室", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄：自由輸入標單 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("請輸入美股代號 (用逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 1. QQQ 200MA 策略警示 ---
def render_strategy_light():
    try:
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="1y")
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            st.subheader("💡 交易策略警示 (TQQQ 輪動)")
            c1, c2, c3 = st.columns(3)
            c1.metric("QQQ 現價", f"${curr:.2f}")
            c2.metric("QQQ 200MA", f"${ma200:.2f}")
            if curr > ma200:
                c3.success("✅ 訊號：多頭 (站上 200MA)")
            else:
                c3.error("🚨 訊號：空頭 (跌破 200MA)")
    except:
        st.warning("策略數據更新中...")

render_strategy_light()
st.divider()

# --- 2. 抓取基本面數據 ---
@st.cache_data(ttl=1800)
def fetch_fundamental_data(tickers):
    data = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # PEG 多重備援
            peg = info.get('pegRatio') or info.get('trailingPegRatio', '—')
            
            data.append({
                "標的": s,
                "名稱": info.get('shortName', 'N/A'),
                "現價": f"${price:.2f}" if price > 0 else "N/A",
                "PE": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "Forward PE": round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "—",
                "PEG": round(peg, 2) if isinstance(peg, (int, float)) else peg,
                "市值 (B)": f"{round(info.get('marketCap', 0)/1e9, 2)}B" if info.get('marketCap') else "—"
            })
        except:
            continue
    return pd.DataFrame(data)

st.subheader("📊 個股基本面概覽")
df = fetch_fundamental_data(ticker_list)
st.dataframe(df, use_container_width=True, hide_index=True)

# --- 3. 新聞模組 (修復版本) ---
st.divider()
st.subheader("📰 最新個股相關新聞")
news_target = st.selectbox("選擇要看新聞的標的", ticker_list)

if news_target:
    try:
        target_tk = yf.Ticker(news_target)
        # 針對 yfinance 新版 news 格式進行安全抓取
        for news in target_tk.news[:5]:
            # 同時嘗試字典與物件兩種讀取方式
            title = getattr(news, 'title', news.get('title') if isinstance(news, dict) else "無標題")
            link = getattr(news, 'link', news.get('link') if isinstance(news, dict) else "#")
            publisher = getattr(news, 'publisher', news.get('publisher') if isinstance(news, dict) else "未知來源")
            
            with st.expander(title):
                st.write(f"來源: {publisher}")
                st.markdown(f"[點我查看新聞原文]({link})")
    except Exception as e:
        st.write("新聞加載中或暫無資料...")

st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
