import requests
from bs4 import BeautifulSoup
import pandas as pd
import os, time, re
from datetime import datetime

STOCK_CODES = ["7203","9984","6758","6861","8306","9432","6098","7974","4063","8058"]

def clean_number(text):
    text = str(text).replace(',','').replace('---','0').strip()
    m = re.search(r'\d+', text)
    return int(m.group()) if m else 0

def fetch_margin_data(code):
    url = f"https://finance.yahoo.co.jp/quote/{code}.T/margin"
    headers = {'User-Agent':'Mozilla/5.0','Accept-Language':'ja'}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        records = []
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            if len(rows) < 3:
                continue
            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(['td','th'])]
                if len(cells) < 3:
                    continue
                try:
                    date = pd.to_datetime(cells[0])
                    buy = clean_number(cells[1])
                    sell = clean_number(cells[3] if len(cells) > 3 else cells[2])
                    if buy > 0 or sell > 0:
                        records.append({'date':date.strftime('%Y-%m-%d'),'buy_balance':buy,'sell_balance':sell})
                except:
                    continue
        print(f"  {code}: {len(records)}件取得")
        return records if records else None
    except Exception as e:
        print(f"  {code} エラー: {e}")
        return None

def save_data(code, records):
    os.makedirs('data', exist_ok=True)
    path = f"data/{code}.csv"
    new_df = pd.DataFrame(records)
    if os.path.exists(path):
        df = pd.concat([pd.read_csv(path), new_df]).drop_duplicates(subset=['date'])
    else:
        df = new_df
    df.sort_values('date').to_csv(path, index=False)
    print(f"  保存完了: {path}")

def main():
    print(f"=== 開始 {datetime.now().strftime('%Y/%m/%d %H:%M')} ===")
    for code in STOCK_CODES:
        print(f"[{code}] 取得中...")
        records = fetch_margin_data(code)
        if records:
            save_data(code, records)
        time.sleep(3)
    print("=== 完了 ===")

if __name__ == "__main__":
    main()
