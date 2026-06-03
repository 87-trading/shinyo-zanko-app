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

available = []
if os.path.exists("data"):
    for f in sorted(os.listdir("data")):
        if f.endswith(".csv"):
            available.append(f.replace(".csv", ""))

if "code" not in st.session_state:
    st.session_state.code = available[0] if available else "7203"

def set_code(c):
    st.session_state.code = c

with st.sidebar:
    st.header("📊 信用残チャート")
    typed = st.text_input("銘柄コードを入力", max_chars=4, placeholder="例: 7203").strip()
    if typed.isdigit() and len(typed) == 4:
        st.session_state.code = typed

    st.markdown("##### データのある銘柄")
    for code in available:
        label = f"{code}  {STOCK_NAMES.get(code,'')}"
        st.button(label, on_click=set_code, args=(code,), use_container_width=True)

    st.markdown("---")
    tv_url = f"https://www.tradingview.com/chart/?symbol=TSE%3A{st.session_state.code}"
    st.link_button("📈 TradingViewで開く →", tv_url, use_container_width=True)

stock_code = st.session_state.code
name = STOCK_NAMES.get(stock_code, "")
st.markdown(f"### 📊 {stock_code} {name} 信用残チャート")

path = f"data/{stock_code}.csv"
if os.path.exists(path):
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.sort_values('date').tail(52)
    if len(df) >= 2:
        l, p = df.iloc[-1], df.iloc[-2]
        c1, c2, c3 = st.columns(3)
        c1.metric("最新日付", l['date'].strftime('%Y/%m/%d'))
        c2.metric("買い残", f"{int(l['buy_balance']):,}株",
            delta=f"{int(l['buy_balance']-p['buy_balance']):+,}", delta_color="inverse")
        c3.metric("売り残", f"{int(l['sell_balance']):,}株",
            delta=f"{int(l['sell_balance']-p['sell_balance']):+,}")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['date'], y=df['buy_balance'],
        name='信用買い残', marker_color='rgba(220,50,50,0.75)'))
    fig.add_trace(go.Bar(x=df['date'], y=df['sell_balance'],
        name='信用売り残', marker_color='rgba(50,100,220,0.75)'))
    fig.update_layout(barmode='group', height=350,
        xaxis_title="日付", yaxis_title="残高（株）",
        legend=dict(orientation="h", y=1.08),
        template="plotly_dark",
        margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"**{stock_code}** のデータがありません。`fetch_data.py` の `STOCK_CODES` に追加してコミットしてください。")
