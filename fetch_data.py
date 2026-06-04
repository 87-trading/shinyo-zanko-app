import requests
from bs4 import BeautifulSoup
import pandas as pd
import os, time, re, datetime

STOCK_CODES = [
    "7203","9984","6758","6861","8306",
    "9432","6098","7974","4063","8058",
]

def parse_num(t):
    t = re.sub(r'[^\d]', '', str(t))
    return int(t) if t else 0

def fetch_irbank(code):
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'ja,en-US;q=0.9',
        'Referer': 'https://irbank.net/',
    })
    try:
        s.get('https://irbank.net/', timeout=10)
        res = s.get(f'https://irbank.net/{code}/credit', timeout=15)
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
                        'date': date.strftime('%Y-%m-%d'),
                        'buy_balance': nums[0],
                        'sell_balance': nums[1],
                        'lending_balance': nums[2],
                    })
        return records if records else None
    except Exception as e:
        print(f"  エラー: {e}")
        return None

def save_data(code, records):
    os.makedirs('data', exist_ok=True)
    path = f"data/{code}.csv"
    new_df = pd.DataFrame(records)
    if os.path.exists(path):
        existing = pd.read_csv(path)
        if 'lending_balance' not in existing.columns:
            existing['lending_balance'] = 0
        df = pd.concat([existing, new_df]).drop_duplicates(subset=['date'])
    else:
        df = new_df
    df.sort_values('date').to_csv(path, index=False)
    print(f"  保存: {len(df)}件")

def main():
    print("=== 開始 ===")
    for code in STOCK_CODES:
        print(f"[{code}] 取得中...")
        records = fetch_irbank(code)
        if records:
            save_data(code, records)
        else:
            print("  スキップ")
        time.sleep(3)
    print("=== 完了 ===")

if __name__ == "__main__":
    main()
