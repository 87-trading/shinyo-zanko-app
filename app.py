import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
import re, datetime

st.set_page_config(page_title="信用残チャート", page_icon="📊", layout="wide")

STOCK_NAMES = {
    "7203":"トヨタ自動車","9984":"ソフトバンクG","6758":"ソニーグループ",
    "6861":"キーエンス","8306":"三菱UFJ","9432":"NTT","6098":"リクルートHD",
    "7974":"任天堂","4063":"信越化学","8058":"三菱商事",
}

def parse_num(text):
    t = re.sub(r'[^\d]', '', str(text))
    return int(t) if t else 0

@st.cache_data(ttl=3600)
def fetch_irbank(code):
    url = f"https://irbank.net/{code}/credit"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept-Language': 'ja,en-US;q=0.9',
        'Referer': 'https://irbank.net/',
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        records = []
        now = datetime.datetime.now()

        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td','th'])
                if len(cells) < 4: continue
                texts = [c.get_text(strip=True) for c in cells]

                # MM/DD形式の日付を解析
                m = re.match(r'^(\d{1,2})/(\d{2})$', texts[0])
                if m:
                    month, day = int(m.group(1)), int(m.group(2))
                    year = now.year if month <= now.month else now.year - 1
                    try:
                        date = pd.Timestamp(year=year, month=month, day=day)
                    except: continue
                else:
                    try: date = pd.to_datetime(texts[0])
                    except: continue

                vals = [parse_num(t) for t in texts[1:5]]
                if len(vals) >= 3 and vals[0] > 1000:
                    records.append({
                        'date': date,
                        'buy': vals[0],
                        'sell': vals[1],
                        'lending': vals[2],
                        'combined': vals[1] + vals[2],
                    })

        if records:
            df = pd.DataFrame(records).drop_duplicates('date').sort_values('date')
            return df, True
    except: pass
    return fetch_yahoo(code), False

@st.cache_data(ttl=3600)
def fetch_yahoo(code):
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
                        records.append({'date':date,'buy':buy,'sell':sell,'lending':0,'combined':sell})
                except: continue
        return pd.DataFrame(records).sort_values('date') if records else None
    except: return None

# サイドバー
with st.sidebar:
    st.markdown("### 📊 信用残チャート")
    stock_code = st.text_input("銘柄コードを入力", placeholder="例: 7203", max_chars=4).strip()
    if stock_code.isdigit() and len(stock_code)==4:
        tv_url = f"https://www.tradingview.com/chart/?symbol=TSE%3A{stock_code}"
        st.link_button("📈 TradingViewで開く →", tv_url, use_container_width=True)

if not stock_code:
    st.info("👈 左に銘柄コードを入力してください（例: 7203）")
    st.stop()
if not stock_code.isdigit() or len(stock_code)!=4:
    st.error("4桁の数字を入力してください")
    st.stop()

name = STOCK_NAMES.get(stock_code, "")
st.markdown(f"### 📊 {stock_code} {name} 信用残チャート")

with st.spinner("データ取得中..."):
    df, from_irbank = fetch_irbank(stock_code)

if df is not None and len(df) > 0:
    df = df.tail(26)
    has_lending = from_irbank and df['lending'].sum() > 0

    # 最新データの指標
    if len(df) >= 2:
        l, p = df.iloc[-1], df.iloc[-2]
        cols = st.columns(4 if has_lending else 3)
        cols[0].metric("最新日付", l['date'].strftime('%Y/%m/%d'))
        cols[1].metric("買い残", f"{int(l['buy']):,}株",
            delta=f"{int(l['buy']-p['buy']):+,}", delta_color="inverse")
        cols[2].metric("売り残", f"{int(l['sell']):,}株",
            delta=f"{int(l['sell']-p['sell']):+,}")
        if has_lending:
            cols[3].metric("貸付残", f"{int(l['lending']):,}株",
                delta=f"{int(l['lending']-p['lending']):+,}")

    # グラフ
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['date'], y=df['buy'],
        name='📈 買い残', marker_color='rgba(220,50,50,0.8)'))
    fig.add_trace(go.Bar(x=df['date'], y=df['sell'],
        name='📉 売り残', marker_color='rgba(50,100,220,0.8)'))
    if has_lending:
        fig.add_trace(go.Bar(x=df['date'], y=df['lending'],
            name='🏦 貸付残', marker_color='rgba(50,180,80,0.8)'))
        fig.add_trace(go.Scatter(x=df['date'], y=df['combined'],
            name='売り残＋貸付残', mode='lines+markers',
            line=dict(color='orange', width=2, dash='dot')))

    fig.update_layout(barmode='group', height=350,
        xaxis_title="日付", yaxis_title="残高（株）",
        legend=dict(orientation="h", y=1.12),
        template="plotly_dark",
        margin=dict(l=0,r=0,t=10,b=0))
    st.plotly_chart(fig, use_container_width=True)

    src = "IRBank" if from_irbank else "Yahoo Finance Japan"
    st.caption(f"データソース: {src}　※毎週金曜更新（1時間キャッシュ）")
else:
    st.warning(f"「{stock_code}」のデータを取得できませんでした。")
