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

def fmt(n):
    n = int(n)
    if n >= 100000000: return f"{n/100000000:.2f}億株"
    if n >= 10000: return f"{n/10000:.1f}万株"
    return f"{n:,}株"

def parse_num(t):
    t = re.sub(r'[^\d]', '', str(t))
    return int(t) if t else 0

@st.cache_data(ttl=3600)
def fetch_data(code):
    # IRBankから取得
    try:
        url = f"https://irbank.net/{code}/credit"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept-Language': 'ja',
            'Referer': 'https://irbank.net/',
        }
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        records = []
        current_year = datetime.datetime.now().year

        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td','th'])
                if not cells: continue
                texts = [c.get_text(strip=True) for c in cells]
                first = texts[0]
                if re.match(r'^\d{4}$', first):
                    current_year = int(first)
                    continue
                m = re.match(r'^(\d{1,2})/(\d{1,2})$', first)
                if not m: continue
                month, day = int(m.group(1)), int(m.group(2))
                try:
                    date = pd.Timestamp(year=current_year, month=month, day=day)
                except: continue
                nums = [parse_num(t) for t in texts[1:]]
                if len(nums) >= 3 and nums[0] > 100:
                    records.append({
                        'date': date,
                        'buy': nums[0], 'sell': nums[1],
                        'lending': nums[2],
                        'combined': nums[1] + nums[2]
                    })

        if records:
            df = pd.DataFrame(records).drop_duplicates('date').sort_values('date')
            src = 'IRBank（貸付残含む）' if df['lending'].sum() > 0 else 'IRBank'
            return df, src
    except: pass

    # Yahoo Finance Japanから取得
    try:
        url2 = f"https://finance.yahoo.co.jp/quote/{code}.T/margin"
        res = requests.get(url2,
            headers={'User-Agent':'Mozilla/5.0','Accept-Language':'ja'}, timeout=15)
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
                    buy = parse_num(cells[1])
                    sell = parse_num(cells[3] if len(cells)>3 else cells[2])
                    if buy > 0:
                        records.append({'date':date,'buy':buy,'sell':sell,
                                        'lending':0,'combined':sell})
                except: continue
        if records:
            return pd.DataFrame(records).sort_values('date'), 'Yahoo Finance Japan'
    except: pass

    return None, None

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
st.subheader(f"📊 {stock_code} {name} 信用残チャート")

with st.spinner("データ取得中..."):
    df, source = fetch_data(stock_code)

if df is not None and len(df) > 0:
    df = df.tail(26)
    has_lending = df['lending'].sum() > 0

    if len(df) >= 2:
        l, p = df.iloc[-1], df.iloc[-2]
        ncols = 4 if has_lending else 3
        cols = st.columns(ncols)
        cols[0].metric("最新日付", l['date'].strftime('%Y/%m/%d'))
        cols[1].metric("買い残", fmt(l['buy']),
            delta=f"{int(l['buy']-p['buy']):+,}", delta_color="inverse")
        cols[2].metric("売り残", fmt(l['sell']),
            delta=f"{int(l['sell']-p['sell']):+,}")
        if has_lending:
            cols[3].metric("貸付残", fmt(l['lending']),
                delta=f"{int(l['lending']-p['lending']):+,}")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['date'], y=df['buy'],
        name='買い残', marker_color='rgba(220,50,50,0.8)'))
    fig.add_trace(go.Bar(x=df['date'], y=df['sell'],
        name='売り残', marker_color='rgba(50,100,220,0.8)'))
    if has_lending:
        fig.add_trace(go.Bar(x=df['date'], y=df['lending'],
            name='貸付残', marker_color='rgba(50,180,80,0.8)'))
        fig.add_trace(go.Scatter(x=df['date'], y=df['combined'],
            name='売残+貸付残', mode='lines+markers',
            line=dict(color='orange', width=2, dash='dot')))

    fig.update_layout(
        barmode='group', height=320,
        xaxis_title=None, yaxis_title="株数",
        legend=dict(orientation="h", y=1.1, font=dict(size=10)),
        template="plotly_dark",
        margin=dict(l=40, r=10, t=10, b=30)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"📡 出典: {source}　週次更新（1時間キャッシュ）")
else:
    st.error(f"「{stock_code}」のデータを取得できませんでした。しばらく待ってから再試行してください。")
