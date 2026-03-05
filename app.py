import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="專業美股儀表板", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄：自由輸入 ---
st.sidebar.header("⚙️ 控制面板")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("請輸入美股代號 (用逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# --- 1. TQQQ 輪動策略 (保持原狀，這是你的核心) ---
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
            c3.success("✅ 訊號：多頭")
        else:
            c3.error("🚨 訊號：空頭")
except:
    st.warning("策略數據更新中...")

st.divider()

# --- 2. 核心數據表 (強化 PEG 與財務指標) ---
@st.cache_data(ttl=1800)
def get_data(tickers):
    data = []
    for s in tickers:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            # 針對 PEG 做極致容錯
            peg = info.get('pegRatio') or info.get('trailingPegRatio') or "—"
            
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
df = get_data(ticker_list)
st.dataframe(df, use_container_width=True, hide_index=True)

# --- 3. 穩定版新聞 (只顯示最穩定的資訊) ---
st.divider()
st.subheader("📰 最新市場簡報")
target = st.selectbox("選擇標的", ticker_list)

if target:
    tk_news = yf.Ticker(target)
    try:
        raw_news = tk_news.news
        if raw_news:
            for n in raw_news[:5]:
                # 這次我們直接嘗試讀取，失敗就跳過該則，不讓網頁死掉
                try:
                    title = n['title']
                    link = n['link']
                    st.markdown(f"🔗 [{title}]({link})")
                except:
                    continue
        else:
            st.write("目前暫無格式化新聞。")
    except:
        st.write("新聞模組調整中...")
