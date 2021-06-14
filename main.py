from argparse import ArgumentParser
import requests
import os
from datetime import datetime
import statistics
import csv
from math import trunc


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
    mean_oi = statistics.mean([c.get("openInterest") for c in contracts])
    contracts = [c for c in contracts if c.get("openInterest") >= mean_oi]
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
        contracts_by_dte[dte].sort(key=lambda c: c["strikePrice"])
    return contracts_by_dte


def get_profit_potential_pct(spread):
    spread_raw_profit = spread["spread_width"] - spread["est_spread_cost"]
    if spread["est_spread_cost"] == 0:
        return 0
    profit_potential = spread_raw_profit / spread["est_spread_cost"]
    # format to 3 decimal places
    profit_potential = trunc(profit_potential * 1000) / 1000
    return profit_potential

def get_mid_spread_cost(long_contract, short_contract):
    """
    computes the mid point cost of a spread to account for 
    wide bid/ask spreads
    """
    long_contract_mid = statistics.mean([long_contract["bid"], long_contract["ask"]])
    short_contract_mid = statistics.mean([short_contract["bid"], short_contract["ask"]])
    return long_contract_mid - short_contract_mid

def build_spread_basic_info(long_contract, short_contract):
    spread_details = {}
    spread_details["long_leg_desc"] = long_contract["description"]
    spread_details["short_leg_desc"] = short_contract["description"]
    spread_details["spread_width"] = (
        short_contract["strikePrice"] - long_contract["strikePrice"]
    )
    spread_details["est_spread_cost"] = get_mid_spread_cost(long_contract,short_contract)
    spread_details["long_leg_details"] = long_contract
    spread_details["short_leg_details"] = short_contract
    spread_details["spread_DTE"] = long_contract["daysToExpiration"]
    return spread_details


def get_net_theta(long_contract, short_contract):
    theta_net = long_contract["theta"] - short_contract["theta"]
    return theta_net


def get_net_delta(long_contract, short_contract):
    delta_net = long_contract["delta"] - short_contract["delta"]
    return delta_net


def analyze_vertical_spreads(contracts):
    """
    computes reasonable vertical spreads
    such that they meet the following criteria:
        - expiration date is the same date
        - both contracts are ITM
        - the max profit is at least 50% of the width of the strikes
    """
    grouped_contracts = get_itm_contracts(contracts)
    spreads = []
    for dte, contracts in grouped_contracts.items():
        for i in range(len(contracts)):
            current_contract = contracts[i]
            for j in range(i+1, len(contracts)):
                compare_contract = contracts[j]
                spread_details = build_spread_basic_info(
                    current_contract, compare_contract
                )
                spread_details["est_profit_potential_pct"] = get_profit_potential_pct(
                    spread_details
                )
                spread_details["net_theta"] = get_net_theta(
                    current_contract, compare_contract
                )
                spread_details["net_delta"] = get_net_delta(
                    current_contract, compare_contract
                )
                if spread_details["est_profit_potential_pct"] > 0.5:
                    spreads.append(spread_details)
    return spreads


def write_results_file(symbol, dt, fieldnames, results):
    filenm = f"{symbol}_{dt.strftime('%Y_%m_%d')}.csv"
    with open(filenm, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

def read_data_from_td(host, input_params):
    data = requests.get(host, params=input_params)
    if data.status_code != 200:
        print(f"Got error code {data.status_code} from TD")
        os.exit(1)
    else:
        data = data.json()
    return data 

def run_vertical_call_spreads(symbol, apikey):
    host = "https://api.tdameritrade.com/v1/marketdata/chains"
    input_params = {"apikey": apikey, "symbol": symbol}
    data = read_data_from_td(host, input_params)
    calls = get_contracts(data.get("callExpDateMap"))
    calls = filter_mean_open_interest(calls)
    vertical_call_spreads = analyze_vertical_spreads(calls)
    fieldnames = [
        "spread_DTE",
        "est_profit_potential_pct",
        "est_spread_cost",
        "long_leg_desc",
        "short_leg_desc",
        "spread_width",
        "net_delta",
        "net_theta",
        "long_leg_details",
        "short_leg_details",
    ]
    write_results_file(symbol, datetime.now(), fieldnames, vertical_call_spreads)

if __name__ == "__main__":
    start = datetime.now()
    p = ArgumentParser()
    p.add_argument("--symbols", default="SPY", help="Symbol to analyze")
    args = p.parse_args()
    apikey = os.environ["tdapikey"]
    if apikey is None:
        print("Missing tdapikey environment variable")
        os.exit(1)
    
    symbols_list = args.symbols.split(",")
    for symbol in symbols_list:
        run_vertical_call_spreads(symbol, apikey)
