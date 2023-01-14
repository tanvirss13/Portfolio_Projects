#!/usr/bin/env python3
"""
Generates a backtest for puts on a list of ETFs.
"""
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import load_trades
import datetime
import csv
import os
import params
from dateutil import parser
from Transaction import Transaction
from Trade import Trade

# Constants.
START_DATE = '2013-01-01'
END_DATE = '2017-12-31'
RESULTS_FILE = 'results/etf_puts_backtest.csv'
TRADE_FILE = 'results/etf_trades.txt'
WHITELIST = 'etf_puts_whitelist.txt'
PROFIT_TAKE_TRIGGER = 2

# Open a new trade for this symbol.
def open_trade(symbol, current_date):

    # Pull the options for this date.
    candidates = load_trades.get_transaction_candidates_by_date_and_symbol(
        symbol, current_date, current_date, 0)

    # Puts only
    puts = []
    for candidate in candidates:
        if candidate.option_type == 'put':
            puts.append(candidate)

    # Handle not having any.
    if len(puts) == 0:
        print(symbol + ": No qualifying options found.")
        return 

    # Sort by strike delta and farthest expiration.
    put_legs = []
    for put in puts:
        strike_delta = put.strike - put.underlying_price
        rel_expiration = (-1)*(put.expiration - current_date).days
        put_leg = (put, rel_expiration, strike_delta)
        put_legs.append(put_leg)
    put_legs.sort(key = lambda put_leg: (put_leg[1], abs(put_leg[2])))

    # Pick the first one. 
    put_leg = put_legs[0][0]

    # Create a trade.
    put_transaction = Transaction()
    put_transaction.stats = put_leg
    put_transaction.buy_or_sell = 'buy'
    put_transaction.stats.calculate_derived_values()
    trade = Trade()
    trade.opening_transactions = [put_transaction]
    trade.open_date = current_date
    trade.open_value = put_leg.mid

    # Filters.
    if trade.open_value == 0:
        return None
    
    return trade
    
# Close a trade and record.
def close_trade(trade, current_date):

    # Pull the closing transactions.
    trade.close_date = current_date
    symbol = trade.opening_transactions[0].stats.underlying_symbol
    closing_candidates = load_trades.get_transaction_candidates_by_date_and_symbol(
        symbol, current_date, current_date, 0)
    closing_candidates_by_date = dict()
    closing_candidates_by_date[current_date] = closing_candidates
    closing_transactions = trade._get_closing_transactions(closing_candidates_by_date)
    if closing_transactions == None or len(closing_transactions) == 0:
        print("Couldn't find any closing candidates for " + symbol + ".")
        return None
    trade.closing_transactions = closing_transactions
    trade.calculate_derived_data()
    put_leg = trade.opening_transactions[0].stats

    # Record
    put_leg_string = "Buy " + \
                     str(put_leg.expiration) + \
                     " " + \
                     str(symbol) + \
                     " " + \
                     str(put_leg.strike) + \
                     " for $" + \
                     str(put_leg.mid)

    close_leg1_string = "Sell " + \
                        str(trade.closing_transactions[0].stats.expiration) + \
                        " " + \
                        str(symbol) + \
                        " " + \
                        str(trade.closing_transactions[0].stats.strike) + \
                        " for $" + \
                        str(trade.closing_transactions[0].stats.mid)

    
    # Record.
    csvrow = dict()
    csvrow['Open_Date']               = str(trade.open_date)
    csvrow['Close_Date']              = str(trade.close_date)
    csvrow['Symbol']                  = str(symbol)
    csvrow['Underlying_Price_Open']   = "$" + str(trade.opening_transactions[0].stats.underlying_price)
    csvrow['Underlying_Price_Close']  = "$" + str(trade.closing_transactions[0].stats.underlying_price)
    csvrow['Open_Value']              = "$" + str(round(trade.open_value, 2))
    csvrow['Close_Value']             = "$" + str(round(trade.close_value, 2))
    csvrow['Put_Leg']                 = put_leg_string
    csvrow['Close_Leg1']              = close_leg1_string
    csvrow['Return']                  = str(round(100*trade.profit_percent, 2)) + "%"
    
    with open(RESULTS_FILE, 'a') as f:
        csv_writer = csv.DictWriter(f, fieldnames, delimiter=',', quotechar='"')
        csv_writer.writerow(csvrow)

    with open(TRADE_FILE, 'a') as f:
        f.write(symbol + "\n")
        f.write(trade.print_trade())
        f.write("\n===================\n")
        
    print("Recording trade for " + symbol)

# Set up the log.
fieldnames = ['Open_Date',
              'Close_Date',
              'Symbol',
              'Underlying_Price_Open',
              'Underlying_Price_Close',
              'Open_Value',
              'Close_Value',
              'Put_Leg',
              'Close_Leg1',
              'Return']

with open(RESULTS_FILE, 'w') as f:
    csv_writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=',', quotechar='"')
    csv_writer.writeheader()

# Delete old trade file.
if os.path.isfile(TRADE_FILE):
    os.remove(TRADE_FILE)

# Calculate dates.
start_date = parser.parse(START_DATE).date()
end_date = parser.parse(END_DATE).date()
num_days = (end_date - start_date).days

# Load the whitelist.
whitelist_symbols = set()
with open(WHITELIST, 'r') as f:
    whitelist_symbols = set(f.read().upper().splitlines())

# Main loop.
open_trades = set()
for current_date in (start_date + datetime.timedelta(days=n) for n in range(num_days)):

    # Handle weekends.
    if current_date.weekday() > 4:
        continue

    print(str(current_date))

    # Check each symbol.
    found_symbol_in_open_trades = False
    for symbol in whitelist_symbols:

        # If the trade is already open, handle...
        for open_symbol, trade in open_trades:

            if open_symbol == symbol:

                found_symbol_in_open_trades = True

                # Close if we hit our profit target.
                current_value = trade.get_current_value(current_date)
                if current_value != None:
                    current_profit = (current_value - trade.open_value)/abs(trade.open_value)

                    if current_profit >= PROFIT_TAKE_TRIGGER:
                        open_trades.remove((open_symbol, trade))
                        close_trade(trade, current_date)
                        break

                # Close if the option is expiring.
                expiration = trade.opening_transactions[0].stats.expiration
                if expiration <= current_date:
                    open_trades.remove((open_symbol, trade))
                    close_trade(trade, expiration - datetime.timedelta(days=1))
                break

        # If we don't currently have a position, open one.
        if not found_symbol_in_open_trades:
            trade = open_trade(symbol, current_date)
            if trade == None:
                print(symbol + ": Could not open trade.")
                continue
            open_trades.add((symbol, trade))


