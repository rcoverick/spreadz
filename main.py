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

def filter_mean_open_interest(contracts):
    mean_oi = statistics.mean([c.get('openInterest') for c in contracts])
    contracts = [c for c in contracts if c.get('openInterest') >= mean_oi]
    return contracts

def get_itm_contracts(contracts):
    """
    returns ITM contracts grouped by days to expiration
    """
    contracts_by_dte = {}
    for c in contracts:
        if not c["inTheMoney"]:
            continue 
        dte = c["daysToExpiration"]
        if dte in contracts_by_dte:
            contracts_by_dte[dte].append(c)
        else:
            contracts_by_dte[dte] = [c]
        contracts_by_dte[dte].sort(key = lambda c: c["strikePrice"])
    return contracts_by_dte

def is_good_vertical_spread(a,b):
    """
    a = long leg 
    b = short leg
    """
    strike_width = b["strikePrice"] - a["strikePrice"]
    if strike_width == 0:
        return False
    debit_required = a["last"] - b["last"]
    return debit_required / strike_width <= 0.5


def compute_vertical_spreads(contracts):
    """
    computes reasonable vertical spreads 
    such that they meet the following criteria:
        - expiration date is the same date 
        - both contracts are ITM
        - the max profit is at least 50% of the width of the strikes 
    """
    grouped_contracts = get_itm_contracts(contracts)
    spreads = {}
    for dte, contracts in grouped_contracts.items():
        for i in range(len(contracts)):
            current_contract = contracts[i]
            for j in range(i,len(contracts)):
                compare_contract = contracts[j]
                if is_good_vertical_spread(current_contract, compare_contract):
                    key =  f"{current_contract.get('description')} / {compare_contract.get('description')}"
                    spreads[key] = [current_contract, compare_contract]

    return spreads

if __name__ == "__main__":
    start = datetime.now()
    p = ArgumentParser()
    p.add_argument("--symbol", default="SPY", help="Symbol to analyze")
    args = p.parse_args()
    apikey = os.environ["tdapikey"]
    if apikey is None:
        print("Missing tdapikey environment variable")
        os.exit(1)
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
    
    puts = filter_mean_open_interest(puts)
    calls = filter_mean_open_interest(calls)

    calls = compute_vertical_spreads(calls)
    print(json.dumps(calls))
    print(f"{datetime.now()-start}")

