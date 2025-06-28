import pandas as pd

df = pd.read_csv('T20-GL-gainers-allSec-25-Jun-2025.csv')

# Strip whitespace from all column names
df.columns = df.columns.str.strip()

# Lowercase all column names
df.columns = df.columns.str.lower()

# Now extract symbols using lowercase 'symbol'
symbols = df['symbol'].dropna().unique()

tickers_ns = [str(sym).strip() + '.NS' for sym in symbols]

with open('tickers_gainers_20.txt', 'w') as f:
    for ticker in tickers_ns:
        f.write(ticker + '\n')

print(f"Saved {len(tickers_ns)} tickers to tickers_from_csv.txt")
