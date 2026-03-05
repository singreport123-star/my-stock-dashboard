# --- 3. 本益比河流圖 (進化曲線版) ---
st.divider()
st.subheader("🌊 本益比河流圖 (PE Band) - 歷史趨勢版")
target = st.selectbox("選擇標的", [t for t in ticker_list if t not in ["VOO", "QQQM", "IBIT"]])

if target:
    try:
        tk = yf.Ticker(target)
        # 抓取 3 年歷史數據
        hist = tk.history(period="3y")
        
        # 抓取每季盈餘並轉為滾動年度 EPS (TTM)
        earnings = tk.quarterly_financials.loc['Basic EPS'].iloc[::-1] # 轉為時間正序
        eps_ttm = earnings.rolling(window=4).sum().dropna() # 計算過去四季總和
        
        if not eps_ttm.empty:
            # 將 EPS 數據與股價日期對齊
            eps_df = pd.DataFrame(eps_ttm).rename(columns={'Basic EPS': 'EPS'})
            plot_df = hist[['Close']].join(eps_df, how='ffill').fillna(method='ffill')
            
            multipliers = [15, 20, 25, 30, 35] if target != "NVDA" else [30, 50, 70, 90, 110]
            
            fig = go.Figure()
            # 畫出股價
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Close'], name='實際股價', line=dict(color='black', width=2)))
            
            # 畫出起伏的河流
            for m in multipliers:
                fig.add_trace(go.Scatter(
                    x=plot_df.index, 
                    y=plot_df['EPS'] * m, 
                    name=f'{m}x PE',
                    line=dict(dash='dash', width=1),
                    opacity=0.5
                ))
            
            fig.update_layout(title=f"{target} 盈餘成長河流圖", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("無法取得該標的歷史 EPS 趨勢，請嘗試其他個股（如 MSFT, AAPL）。")
    except Exception as e:
        st.error(f"河流圖計算失敗，可能是該公司財報格式特殊。")
