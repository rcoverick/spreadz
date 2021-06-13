from argparse import ArgumentParser
import requests
import os
import json 
from datetime import datetime 
import statistics

def get_contracts(exp_map):
    """
    extracts options contracts from expiration map
    """
    results = []
    for expDate, expStrikesMap in exp_map.items():
        for strikePrice, contracts in expStrikesMap.items():
            for contract in contracts:
                results.append(contract)
    return results

def filter_meean_open_interest(contracts):
    median_oi = statistics.mean([c.get('openInterest') for c in contracts])
    contracts = [c for c in contracts if c.get('openInterest') >= median_oi]
    return contracts

if __name__ == "__main__":
    start = datetime.now()
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
    else:
        data = data.json()
    
    puts = get_contracts(data.get('putExpDateMap'))
    calls = get_contracts(data.get('callExpDateMap'))
    
    print(f"{len(puts)} puts, {len(calls)} calls")
    puts = filter_median_open_interest(puts)
    calls = filter_median_open_interest(calls)
    
    print(f"{len(puts)} puts, {len(calls)} calls")

    print(f"{datetime.now()-start}")
