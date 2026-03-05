import streamlit as st
import yfinance as yf
import pandas as pd

# 設定網頁標題與寬度
st.set_page_config(page_title="專業美股觀測站", layout="wide")

st.title("🚀 我的股市數據儀表板")
st.caption("即時抓取基本面指標：PE, Forward PE, PEG")

# 你的觀測清單
tickers = ["NVDA", "MSFT", "META", "TSLA", "AAPL", "ORCL", "VOO", "QQQM", "IBIT", "DXYZ"]

@st.cache_data(ttl=3600)
def get_stock_data(symbol_list):
    all_data = []
    for s in symbol_list:
        try:
            tk = yf.Ticker(s)
            info = tk.info
            
            # 判斷是否為 ETF (ETF 通常沒有 PE/Forward PE)
            is_etf = info.get('quoteType') == 'ETF'
            
            all_data.append({
                "標的": s,
                "名稱": info.get("shortName", "N/A"),
                "現價": f"${info.get('currentPrice', 'N/A')}",
                "PE (本益比)": info.get("trailingPE", "—") if not is_etf else "ETF",
                "Forward PE (預估)": info.get("forwardPE", "—") if not is_etf else "ETF",
                "PEG (增長比)": info.get("pegRatio", "—"),
                "市值 (B)": round(info.get("marketCap", 0) / 1e9, 2) if info.get("marketCap") else "N/A",
                "52週高點": info.get("fiftyTwoWeekHigh", "N/A")
            })
        except:
            all_data.append({"標的": s, "名稱": "Error", "現價": "N/A"})
    return pd.DataFrame(all_data)

# 介面佈局：點擊按鈕可強制更新
if st.button('🔄 重新整理數據'):
    st.cache_data.clear()

with st.spinner('正在從 Yahoo Finance 抓取最新財報數據...'):
    df = get_stock_data(tickers)

# 顯示表格
st.subheader("📊 基本面概覽")
st.dataframe(df, use_container_width=True, hide_index=True)

# 針對你特別關注的標的提供小筆記
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("💡 投資筆記")
    st.write("- **DXYZ**: 封閉型基金，記得觀察折溢價。")
    st.write("- **NVDA/MSFT**: 重點在於 AI 帶來的 Forward PE 變化。")

with col2:
    st.subheader("📈 外部鏈結")
    st.markdown("[TradingView 圖表](https://www.tradingview.com/chart/)")
    st.markdown("[SEC EDGAR 財報原文](https://www.sec.gov/edgar/searchedgar/companysearch.html)")
