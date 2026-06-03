import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="信用残チャート", page_icon="📊", layout="wide")

STOCK_NAMES = {
    "7203":"トヨタ自動車","9984":"ソフトバンクG","6758":"ソニーグループ",
    "6861":"キーエンス","8306":"三菱UFJ","9432":"NTT","6098":"リクルートHD",
    "7974":"任天堂","4063":"信越化学","8058":"三菱商事",
}

@st.cache_data(ttl=7200)
def fetch_margin(code):
    url = f"https://finance.yahoo.co.jp/quote/{code}.T/margin"
    headers = {'User-Agent':'Mozilla/5.0','Accept-Language':'ja'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        records = []
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) < 3: continue
            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(['td','th'])]
                if len(cells) < 3: continue
                try:
                    date = pd.to_datetime(cells[0])
                    buy = int(re.sub(r'[^\d]','',cells[1]) or 0)
                    sell = int(re.sub(r'[^\d]','',cells[3] if len(cells)>3 else cells[2]) or 0)
                    if buy > 0 or sell > 0:
                        records.append({'date':date,'buy_balance':buy,'sell_balance':sell})
                except: continue
        return pd.DataFrame(records).sort_values('date') if records else None
    except:
        return None

with st.sidebar:
    st.markdown("### 📊 信用残チャート")
    stock_code = st.text_input("銘柄コードを入力", placeholder="例: 7203", max_chars=4).strip()
    if stock_code.isdigit() and len(stock_code)==4:
        tv_url = f"https://www.tradingview.com/chart/?symbol=TSE%3A{stock_code}"
        st.link_button("📈 TradingViewで開く →", tv_url, use_container_width=True)

if not stock_code:
    st.info("👈 左に銘柄コードを入力してください（例: 7203）")
    st.stop()
if not stock_code.isdigit() or len(stock_code) != 4:
    st.error("4桁の数字を入力してください")
    st.stop()

name = STOCK_NAMES.get(stock_code, "")
st.markdown(f"### 📊 {stock_code} {name} 信用残チャート")

with st.spinner("データ取得中..."):
    df = fetch_margin(stock_code)

if df is not None and len(df) > 0:
    df = df.tail(26)
    if len(df) >= 2:
        l, p = df.iloc[-1], df.iloc[-2]
        c1,c2,c3 = st.columns(3)
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
    fig.update_layout(barmode='group', height=300,
        xaxis_title="日付", yaxis_title="残高（株）",
        legend=dict(orientation="h", y=1.1),
        template="plotly_dark",
        margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"「{stock_code}」のデータを取得できませんでした。コードを確認してください。")
