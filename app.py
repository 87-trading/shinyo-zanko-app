import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

STOCK_NAMES = {
    "7203": "トヨタ自動車", "9984": "ソフトバンクG",
    "6758": "ソニーグループ", "6861": "キーエンス",
    "8306": "三菱UFJ", "9432": "NTT",
    "6098": "リクルートHD", "7974": "任天堂",
    "4063": "信越化学", "8058": "三菱商事",
}

st.set_page_config(page_title="信用残チャート", page_icon="📊", layout="wide")

with st.sidebar:
    st.header("⚙️ 設定")
    stock_code = st.text_input("銘柄コード（4桁）", value="7203", max_chars=4).strip()
    if stock_code.isdigit() and len(stock_code) == 4:
        tv_url = f"https://www.tradingview.com/chart/?symbol=TSE%3A{stock_code}"
        st.link_button("📈 TradingViewで開く →", tv_url, use_container_width=True)
    st.markdown("---")
    st.markdown("**データのある銘柄**")
    if os.path.exists("data"):
        for f in sorted(os.listdir("data")):
            if f.endswith(".csv"):
                code = f.replace(".csv","")
                st.text(f"{code} {STOCK_NAMES.get(code,'')}")

if not stock_code.isdigit() or len(stock_code) != 4:
    st.error("4桁の銘柄コードを入力してください")
    st.stop()

name = STOCK_NAMES.get(stock_code, "")
st.markdown(f"### 📊 {stock_code} {name} 信用残チャート")

path = f"data/{stock_code}.csv"
if os.path.exists(path):
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.sort_values('date').tail(52)
    if len(df) >= 2:
        l, p = df.iloc[-1], df.iloc[-2]
        c1,c2,c3 = st.columns(3)
        c1.metric("最新日付", l['date'].strftime('%Y/%m/%d'))
        c2.metric("信用買い残", f"{int(l['buy_balance']):,}株",
            delta=f"{int(l['buy_balance']-p['buy_balance']):+,}", delta_color="inverse")
        c3.metric("信用売り残", f"{int(l['sell_balance']):,}株",
            delta=f"{int(l['sell_balance']-p['sell_balance']):+,}")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['date'], y=df['buy_balance'],
        name='信用買い残', marker_color='rgba(220,50,50,0.75)'))
    fig.add_trace(go.Bar(x=df['date'], y=df['sell_balance'],
        name='信用売り残', marker_color='rgba(50,100,220,0.75)'))
    fig.update_layout(barmode='group', height=450,
        xaxis_title="日付", yaxis_title="残高（株）",
        legend=dict(orientation="h", y=1.05),
        template="plotly_dark",
        margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"銘柄 **{stock_code}** のデータがまだありません。\nGitHubの `fetch_data.py` の `STOCK_CODES` に `\"{stock_code}\"` を追加してコミットしてください。")
