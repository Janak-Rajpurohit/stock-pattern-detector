import pandas as pd
import numpy as np
from nsepython import nse_eq, nsefetch
from pprint import pprint
from pytz import timezone 
import concurrent.futures
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
to_phone_number = os.getenv('TO_PHONE_NUMBER')
from_phone_number = os.getenv('FROM_PHONE_NUMBER')

# account_sid = 'AC2eeae76a443e2e16d83b3b180498bde0'
# auth_token = 'f3e7fec75747e095617827b0c81f17b3'
client = Client(account_sid, auth_token)

def send_sms(recipient_phone_number,body):
    message = client.messages.create(
        from_=from_phone_number,
        body=body,
        to=recipient_phone_number
    )
   



def fetch_stock_data(symbol):
    try:
        url = f"https://www.nseindia.com/api/chart-databyindex?index={symbol}EQN"
        response = nsefetch(url)
        data = response['grapthData']
        df = pd.DataFrame(data)
        df.rename(columns={0: 'timestamp', 1: 'price'}, inplace=True)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        hourly_data = df.resample('1h').agg({'price': 'ohlc'})
        hourly_data.columns = hourly_data.columns.droplevel()
        hourly_data.reset_index(inplace=True)
        hourly_data.rename(columns={"open": "o", "close": "c", "high": "h", "low": "l"}, inplace=True)

        response = nse_eq(symbol)
        name = symbol
        open_price = hourly_data.iloc[0]['o']
        low_price = min(hourly_data['l'])
        high_price = max(hourly_data['h'])
        close_price = hourly_data.iloc[6]['c']
        last_update_time = response['preOpenMarket']['lastUpdateTime']
        center = (open_price + close_price) / 2
        info_list = [name, open_price, close_price, low_price, high_price, center, last_update_time]

        green_formula1 = (abs(close_price - open_price) * 2.5) <= (high_price - center)
        green_formula2 = (abs(close_price - open_price) * 2.5) <= (center - low_price)
        red_formula1 = (abs(open_price - close_price) * 2.5) <= (high_price - center)
        red_formula2 = (abs(open_price - close_price) * 2.5) <= (center - low_price)

        if green_formula1 or green_formula2:
            pattern_type = "Both" if green_formula1 and green_formula2 else "Single"
        elif red_formula1 or red_formula2:
            pattern_type = "Both" if red_formula1 and red_formula2 else "Single"
        else:
            return None

        info_list.append(pattern_type)
        return symbol, info_list
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

symbols = [
    'ACC', 'ADANIGREEN', 'ADANIPORTS', 'AMBUJACEM', 'APOLLOHOSP', 'ASHOKLEY',
    'ASIANPAINT', 'AUROPHARMA', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJFINANCE',
    'BANDHANBNK', 'BANKBARODA', 'BERGEPAINT', 'BHARTIARTL', 'BIOCON', 'BOSCHLTD',
    'BPCL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'COFORGE', 'COLPAL', 'CONCOR', 'DLF',
    'DABUR', 'DIVISLAB', 'EICHERMOT', 'GAIL', 'GLAND', 'GMRINFRA', 'GODREJCP',
    'GRASIM', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO',
    'HINDUNILVR', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA', 'IDFCFIRSTB', 'IGL',
    'INDHOTEL', 'INDIGO', 'INDUSINDBK', 'INFY', 'IOC', 'IRCTC', 'ITC', 'JSWSTEEL',
    'JUBLFOOD', 'KOTAKBANK', 'LT', 'LICI', 'LUPIN', 'MARICO', 'MARUTI', 'MFSL', 'MGL',
    'MPHASIS', 'MRF', 'MUTHOOTFIN', 'NAUKRI', 'NAVINFLUOR', 'NESTLEIND', 'NMDC', 'NTPC',
    'ONGC', 'PAGEIND', 'PEL', 'PETRONET', 'PFC', 'PIDILITIND', 'PIIND', 'PNB',
    'POWERGRID', 'RAIN', 'RECLTD', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN', 'SHREECEM',
    'SIEMENS', 'SRF', 'SUNPHARMA', 'TATACHEM', 'TATACONSUM', 'TATAMOTORS', 'TATAPOWER',
    'TATASTEEL', 'TCS', 'TECHM', 'TITAN', 'TORNTPHARM', 'TORNTPOWER', 'TVSMOTOR', 'UBL',
    'ULTRACEMCO', 'UPL', 'VEDL', 'VOLTAS', 'WIPRO', 'ZEEL', 'ABB', 'ADANIENSOL',
    'ADANIPOWER', 'ATGL', 'DMART', 'BAJAJHLDNG', 'BEL', 'CANBK', 'CHOLAFIN', 'DRREDDY',
    'HAL', 'IRFC', 'JINDALSTEL', 'JIOFIN', 'LTIM', 'MOTHERSON', 'SHRIRAMFIN',
    'TATAMTRDVR', 'TRENT', 'UNITDSPR', 'VBL', 'ZOMATO', 'ZYDUSLIFE'
]

pattern_dict = {}

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = executor.map(fetch_stock_data, symbols)
    
    for result in results:
        if result:
            symbol, info_list = result
            pattern_dict[symbol] = info_list

message_lines = ["Stock patterns detected:"]
for symbol, info_list in pattern_dict.items():
    name = info_list[0]
    pattern_type = info_list[-1]
    message_lines.append(f"{name}: {pattern_type} candle")


if len(pattern_dict) > 0:
    message = "\n".join(message_lines)
    send_sms(to_phone_number, message)

