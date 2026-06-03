import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import streamlit.components.v1 as components

STOCK_NAMES = {
    "7203": "トヨタ自動車", "9984": "ソフトバンクG",
    "6758": "ソニーグループ", "6861": "キーエンス",
    "8306": "三菱UFJ", "9432": "NTT",
    "6098": "リクルートHD", "7974": "任天堂",
    "4063": "信越化学", "8058": "三菱商事",
}

st.set_page_config(page_title="信用残チャート", page_icon="📊", layout="wide")
st.title("📊 信用残チャートビューア")

with st.sidebar:
    st.header("⚙️ 設定")
    stock_code = st.text_input("銘柄コード（4桁）", value="7203", max_chars=4).strip()
    st.markdown("---")
    st.markdown("**データのある銘柄**")
    if os.path.exists("data"):
        for f in sorted(os.listdir("data")):
            if f.endswith(".csv"):
                code = f.replace(".csv","")
                name = STOCK_NAMES.get(code, "")
                st.text(f"{code} {name}")

if not stock_code.isdigit() or len(stock_code) != 4:
    st.error("4桁の銘柄コードを入力してください")
    st.stop()

name = STOCK_NAMES.get(stock_code, "")
st.subheader(f"📈 {stock_code} {name} 価格チャート")

components.html(f"""
<div style="height:600px">
<script src="https://s3.tradingview.com/tv.js"></script>
<div id="tv" style="height:600px"></div>
<script>
new TradingView.widget({{
  container_id:"tv", autosize:true,
  symbol:"TSE:{stock_code}", interval:"W",
  timezone:"Asia/Tokyo", theme:"dark",
  style:"1", locale:"ja", height:600
}});
</script></div>""", height=620)

st.subheader(f"📉 {stock_code} {name} 信用残推移")
path = f"data/{stock_code}.csv"

if os.path.exists(path):
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.sort_values('date').tail(52)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['date'], y=df['buy_balance'],
        name='信用買い残', marker_color='rgba(220,50,50,0.75)'))
    fig.add_trace(go.Bar(x=df['date'], y=df['sell_balance'],
        name='信用売り残', marker_color='rgba(50,100,220,0.75)'))
    fig.update_layout(barmode='group', height=400,
        xaxis_title="日付", yaxis_title="残高（株）",
        legend=dict(orientation="h", y=1.1),
        template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    if len(df) >= 2:
        l, p = df.iloc[-1], df.iloc[-2]
        c1,c2,c3 = st.columns(3)
        c1.metric("最新日付", l['date'].strftime('%Y/%m/%d'))
        c2.metric("信用買い残", f"{int(l['buy_balance']):,}株",
            delta=f"{int(l['buy_balance']-p['buy_balance']):+,}", delta_color="inverse")
        c3.metric("信用売り残", f"{int(l['sell_balance']):,}株",
            delta=f"{int(l['sell_balance']-p['sell_balance']):+,}")
else:
    st.info(f"銘柄 {stock_code} のデータがまだありません。")
