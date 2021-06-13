from argparse import ArgumentParser
import requests
import os
import json 

if __name__ == "__main__":
    p = ArgumentParser()
    p.add_argument("--symbol", default="SPY", help="Symbol to analyze")
    args = p.parse_args()
    apikey = os.environ["tdapikey"]
    if apikey is not None:
        print("Found API Key")
    host = "https://api.tdameritrade.com/v1/marketdata/chains"
    input_params = {"apikey": apikey, "symbol": args.symbol}

    data = requests.get(host, params=input_params)
    if data.status_code != 200:
        print(f"Got error code {data.status_code} from TD")
        os.exit(1)
    # filter low open interest
    
    print(f"{json.dumps(data.json())}")
