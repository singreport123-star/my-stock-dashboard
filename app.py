import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 網頁配置 ---
st.set_page_config(page_title="專業美股戰情室", layout="wide")

st.title("🚀 我的股市數據儀表板")

# --- 側邊欄：控制面板 ---
st.sidebar.header("⚙️ 觀測清單設定")
default_list = "NVDA, MSFT, META, TSLA, AAPL, ORCL, VOO, QQQM, IBIT, DXYZ, HIMS"
user_input = st.sidebar.text_area("自定義觀測代號 (以逗號分隔)", default_list)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.header("💰 多重持股管理")
st.sidebar.info("格式：代號:成本:股數 (每行一支)")
# 這裡預設放你的 HIMS，你可以隨時在網頁側邊欄自行增加，例如 NVDA:120.5:10
default_portfolio = "HIMS:37.90:35" 
portfolio_input = st.sidebar.text_area("輸入持股明細", default_portfolio, height=150)

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

# --- 2. 多重持股損益計算區 ---
st.subheader("📊 投資組合損益回報監控")

portfolio_data = []
lines = portfolio_input.split('\n')
for line in lines:
    if ':' in line:
        try:
            parts = line.split(':')
            symbol = parts[0].strip().upper()
            cost = float(parts[1])
            qty = float(parts[2])
            
            tk = yf.Ticker(symbol)
            current_p = tk.history(period="1d")['Close'].iloc[-1]
            
            total_cost = cost * qty
            current_value = current_p * qty
            pnl = current_value - total_cost
            pnl_pct = (pnl / total_cost) * 100 if total_cost != 0 else 0
            
            portfolio_data.append({
                "標的": symbol,
                "持有股數": qty,
                "平均成本": f"${cost:.2f}",
                "目前市價": f"${current_p:.2f}",
                "總成本": total_cost,
                "目前市值": current_value,
                "總損益 (USD)": round(pnl, 2),
                "報酬率 (%)": f"{pnl_pct:.2f}%"
            })
        except:
            continue

if portfolio_data:
    p_df = pd.DataFrame(portfolio_data)
    
    # 顯示總計指標
    total_c = p_df['總成本'].sum()
    total_v = p_df['目前市值'].sum()
    total_pnl = total_v - total_c
    total_pct = (total_pnl / total_c) * 100 if total_c != 0 else 0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("投資組合總市值", f"${total_v:,.2f}")
    m2.metric("組合總損益 (USD)", f"${total_pnl:,.2f}", f"{total_pct:.2f}%")
    m3.info(f"總投入成本: ${total_c:,.2f}")
    
    # 顯示詳細列表
    st.table(p_df[["標的", "持有股數", "平均成本", "目前市價", "總損益 (USD)", "報酬率 (%)"]])
else:
    st.write("請在側邊欄輸入正確的持股資訊。")

st.divider()

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
            peg = info.get('pegRatio') or info.get('trailingPegRatio', '—')
            
            data.append({
                "標的": s,
                "現價": f"${price:.2f}" if price > 0 else "N/A",
                "PE (本益比)": round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "—",
                "Forward PE": round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "—",
                "PEG": round(peg, 2) if isinstance(peg, (int, float)) else peg,
                "市值 (B)": f"{round(info.get('marketCap', 0)/1e9, 2)}B" if info.get('marketCap') else "—"
            })
        except:
            continue
    return pd.DataFrame(data)

st.subheader("📊 觀測清單基本面概覽")
st.dataframe(fetch_basic_data(ticker_list), use_container_width=True, hide_index=True)

st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
