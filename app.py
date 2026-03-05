import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁基礎設定 ---
st.set_page_config(page_title="專業美股觀測站", layout="wide")

# 加入 CSS 讓表格更好看
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 我的股市數據儀表板")

# 你的觀測清單
tickers = ["NVDA", "MSFT", "META", "TSLA", "AAPL", "ORCL", "VOO", "QQQM", "IBIT", "DXYZ"]

# --- 1. TQQQ 輪動策略區 (置頂) ---
def render_strategy():
    st.subheader("💡 交易策略警示 (TQQQ 輪動策略)")
    try:
        # 抓取 QQQ 過去一年的數據來算 200MA
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="1y")
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            diff = ((current_price - ma200) / ma200) * 100
            
            c1, c2, c3 = st.columns(3)
            c1.metric("QQQ 現價", f"${current_price:.2f}")
            c2.metric("QQQ 200MA", f"${ma200:.2f}", f"{diff:.2f}%")
            
            if current_price > ma200:
                c3.success(f"✅ 訊號：多頭 (站上 200MA)")
                st.toast("目前處於安全作多區間", icon="✅")
            else:
                c3.error(f"🚨 訊號：空頭 (跌破 200MA)")
                st.toast("警訊：目前低於 200MA，請注意風險", icon="🚨")
    except Exception as e:
        st.error(f"策略數據抓取失敗: {e}")

render_strategy()
st.divider()

# --- 2. 數據抓取邏輯 (核心優化) ---
@st.cache_data(ttl=1800) # 每 30 分鐘自動更新
def get_clean_data(symbol_list):
    all_data = []
    for s in symbol_list:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            
            # 價格抓取備援機制
            hist = tk.history(period="1d")
            price = hist['Close'].iloc[-1] if not hist.empty else info.get('currentPrice', 'N/A')
            
            # PEG 多重抓取邏輯 (修復核心)
            peg = info.get("pegRatio")
            if peg is None or peg == 0:
                peg = info.get("trailingPegRatio", "—")
            
            is_etf = info.get('quoteType') in ['ETF', 'FUND']
            
            all_data.append({
                "標的": s,
                "名稱": info.get("shortName", "N/A"),
                "現價": f"${price:.2f}" if isinstance(price, (int, float)) else "N/A",
                "PE (本益比)": round(info.get("trailingPE"), 2) if info.get("trailingPE") else "—",
                "Forward PE": round(info.get("forwardPE"), 2) if info.get("forwardPE") else "—",
                "PEG (增長比)": round(peg, 2) if isinstance(peg, (int, float)) else peg,
                "市值 (B)": f"{round(info.get('marketCap', 0)/1e9, 1)}B" if info.get('marketCap') else "—",
                "52W 高點相差": f"{round(((price/info.get('fiftyTwoWeekHigh',1))-1)*100, 1)}%" if info.get('fiftyTwoWeekHigh') else "—"
            })
        except:
            all_data.append({"標的": s, "名稱": "數據連線中...", "現價": "N/A"})
    return pd.DataFrame(all_data)

# --- 3. 介面顯示 ---
st.subheader("📊 個股基本面概覽 (財報狗風格)")

with st.spinner('正在分析最新財報指標...'):
    df = get_clean_data(tickers)
    # 使用 Styled Dataframe 讓重點更明顯
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "現價": st.column_config.TextColumn("最新股價"),
            "PEG (增長比)": st.column_config.TextColumn("PEG (越低越好)")
        }
    )

# --- 4. 針對你清單的專屬分析筆記 ---
st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.info("📌 **觀測重點**\n"
            "- **PEG < 1**: 代表股價可能被低估（考慮到增長率）。\n"
            "- **DXYZ**: 觀察其市值與溢價，這類私募基金通常波動極大。")

with col_b:
    st.warning("⚠️ **提醒**\n"
               "- ETF (VOO/QQQM/IBIT) 不會有 PE 或 PEG 指標。\n"
               "- 數據每 30 分鐘自動快取，如需立即更新請重新整理網頁。")

st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
