import pandas as pd
import numpy as np
from nsepython import nse_eq, nsefetch
from pytz import timezone
import concurrent.futures
from vonage import Client, Sms
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('VONAGE_API_KEY')
api_secret = os.getenv('VONAGE_API_SECRET')
to_phone_number = os.getenv('TO_PHONE_NUMBER')
from_phone_number = os.getenv('FROM_PHONE_NUMBER')

client = Client(key=api_key, secret=api_secret)
sms = Sms(client)

def send_sms(recipient_phone_number, body):
    response = sms.send_message({
        "from": from_phone_number,
        "to": recipient_phone_number,
        "text": body,
    })
    if response["messages"][0]["status"] != "0":
        raise Exception("SMS failed to send")

def fetch_stock_data(symbol):
    try:
        url = f"https://www.nseindia.com/api/chart-databyindex?index={symbol}EQN"
        response = nsefetch(url)
        
        if 'grapthData' not in response:
            print(f"No 'grapthData' found for {symbol}")
            return None
        
        data = response['grapthData']
        df = pd.DataFrame(data)
        df.rename(columns={0: 'timestamp', 1: 'price'}, inplace=True)
        
        # Convert timestamp from milliseconds to datetime and localize to 'Asia/Kolkata' timezone
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        df.set_index('datetime', inplace=True)
        
        # Filter data between market open (9:15 AM) and close (3:00 PM)
        market_open = df.between_time('09:15', '15:00')
        
        # Debug output
        print(f"{symbol} - Data after conversion and filtering:\n{market_open.head()}\n")
        
        # Resample data to hourly intervals within market hours
        hourly_data = market_open.resample('1H').agg({'price': 'ohlc'})
        hourly_data.columns = hourly_data.columns.droplevel()
        hourly_data.reset_index(inplace=True)
        hourly_data.rename(columns={"open": "o", "close": "c", "high": "h", "low": "l"}, inplace=True)
        
        # Debug output
        print(f"{symbol} - Hourly data:\n{hourly_data.head()}\n")
        
        # Fetch additional stock information
        response_eq = nse_eq(symbol)
        open_price = hourly_data.iloc[0]['o']
        low_price = hourly_data['l'].min()
        high_price = hourly_data['h'].max()
        close_price = hourly_data.iloc[-1]['c']
        last_update_time = response_eq['preOpenMarket']['lastUpdateTime']
        center = (open_price + close_price) / 2
        info_list = [symbol, open_price, close_price, low_price, high_price, center, last_update_time]

        # Determine pattern type
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

print(pattern_dict)

message_lines = ["Stock patterns detected:"]
for symbol, info_list in pattern_dict.items():
    name = info_list[0]
    pattern_type = info_list[-1]
    message_lines.append(f"{name}: {pattern_type} candle")

if pattern_dict:
    message = "\n".join(message_lines)
    send_sms(to_phone_number, message)
    print("SMS sent.")
else:
    print("No patterns detected.")
