import requests

def fetch_bitcoin_price():
    url = 'https://api.coindesk.com/v1/bpi/currentprice.json'
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        bitcoin_price = data['bpi']['USD']['rate_float']
        print(f"Current Bitcoin price in USD: {bitcoin_price}")
    else:
        print("Failed to fetch data")

if __name__ == "__main__":
    fetch_bitcoin_price()