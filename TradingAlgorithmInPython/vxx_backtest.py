#!/usr/bin/env python3
"""
Generates a backtest for the weekly
VXX diagonal trade.
"""
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import load_trades
import datetime
import csv
from dateutil import parser
from statistics import mean, stdev
from math import log, sqrt
from Transaction import Transaction
from Trade import Trade

START_DATE = '2015-01-01'
END_DATE = '2017-10-31'
WIDTH = 2.5
RESULTS_FILE = 'results/vxx_backtest.csv'

# Set up the log.
fieldnames = ['Open_Date',
              'Close_Date',
              'VXX',
              'SMA30',
              'SMA60',
              'SMA90',
              'VXX_Change',
              'Short_Leg',
              'Long_Leg',
              'IV',
              'Delta',
              'Historic_Vol30',
              'Rel_Value',
              'Return']

with open(RESULTS_FILE, 'w') as f:
    csv_writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=',', quotechar='"')
    csv_writer.writeheader()

start_date = parser.parse(START_DATE).date()
end_date = parser.parse(END_DATE).date()
num_days = (end_date - start_date).days
for date in (start_date + datetime.timedelta(days=n) for n in range(num_days)):

    # If this isn't a Friday, continue.
    if date.weekday() != 4:
        continue

    # Pull the options for this date.
    candidates = load_trades.get_transaction_candidates_by_date_and_symbol(
        'VXX', date, date, 0)

    # Filter.
    short_legs = []
    long_legs = []
    for candidate in candidates:

        # Only puts.
        if candidate.option_type == 'call':
            continue

        # Only the near 2 weeks.
        rel_expiration = (candidate.expiration - date).days
        strike_delta = candidate.strike - candidate.underlying_price
        if rel_expiration > 5 and rel_expiration < 9:
            if strike_delta < 0:
                short_legs.append((candidate, strike_delta))
        if rel_expiration  > 12 and rel_expiration < 16:
            if strike_delta > 0:
                long_legs.append(candidate)

    # If we didn't find any, continue.
    if len(short_legs) == 0 or len(long_legs) == 0:
        print("Couldn't find any trades for " + str(date))
        continue

    # Sort by strike delta of the short leg.
    short_legs.sort(key=lambda leg: leg[1], reverse=True)

    # Pick the next-to-smallest one.
    short_leg = short_legs[1][0]

    # Pick the long leg using its strike.
    long_leg = None
    for leg in long_legs:
        if leg.strike == (short_leg.strike + WIDTH):
            long_leg = leg
            break

    # Create a trade from these legs.
    short_leg_transaction = Transaction()
    long_leg_transaction = Transaction()
    short_leg_transaction.stats = short_leg
    long_leg_transaction.stats = long_leg
    short_leg_transaction.buy_or_sell = 'sell'
    long_leg_transaction.buy_or_sell = 'buy'
    short_leg_transaction.stats.calculate_derived_values()
    long_leg_transaction.stats.calculate_derived_values()
    trade = Trade()
    trade.opening_transactions = [short_leg_transaction, long_leg_transaction]
    trade.open_date = date
    trade.close_date = date + datetime.timedelta(days=7)

    # Pull the closing transactions.
    closing_candidates = load_trades.get_transaction_candidates_by_date_and_symbol(
        'VXX', trade.close_date, trade.close_date, 0)
    closing_candidates_by_date = dict()
    closing_candidates_by_date[trade.close_date] = closing_candidates
    closing_transactions = trade._get_closing_transactions(closing_candidates_by_date)
    if closing_transactions == None or len(closing_transactions) == 0:
        continue
    trade.closing_transactions = closing_transactions
    trade.calculate_derived_data()

    # Calculate some derived data.
    underlying_price = trade.opening_transactions[0].stats.underlying_price
    actual_rv = float(trade.open_value/underlying_price)
    underlying_prices = load_trades.get_underlying_prices(
        'VXX', trade.open_date, 90)
    SMA30 = mean(underlying_prices[40:])
    SMA60 = mean(underlying_prices[20:])
    SMA90 = mean(underlying_prices)
    daily_returns = []
    previous_price = underlying_prices[0]
    for price in underlying_prices[1:]:
        daily_return = log(price/previous_price)
        daily_returns.append(daily_return)
        previous_price = price
    historic_vol30 = stdev(daily_returns)*sqrt(252)
    vxx_change = (
        trade.closing_transactions[0].stats.underlying_price - underlying_price)/underlying_price

    short_leg_string = "Sell " + \
                       str(short_leg.expiration) + \
                       " VXX " + \
                       str(short_leg.strike) + \
                       " for $" + \
                       str(short_leg.mid)

    long_leg_string = "Buy " + \
                       str(long_leg.expiration) + \
                       " VXX " + \
                       str(long_leg.strike) + \
                       " for $" + \
                       str(long_leg.mid)
    
    # Record.
    csvrow = dict()
    csvrow['Open_Date']       = str(trade.open_date)
    csvrow['Close_Date']      = str(trade.close_date)
    csvrow['VXX']             = "$" + str(underlying_price)
    csvrow['SMA30']           = "$" + str(round(SMA30, 2))
    csvrow['SMA60']           = "$" + str(round(SMA60, 2))
    csvrow['SMA90']           = "$" + str(round(SMA90, 2))
    csvrow['VXX_Change']      = str(round(100*vxx_change, 2)) + "%"
    csvrow['Short_Leg']       = short_leg_string
    csvrow['Long_Leg']        = long_leg_string
    csvrow['IV']              = str(round(100*trade.position_iv, 2))
    csvrow['Delta']           = str(round(trade.position_delta, 2))
    csvrow['Historic_Vol30']  = str(round(historic_vol30, 2))
    csvrow['Rel_Value']       = str(round(100*actual_rv, 2)) + "%"
    csvrow['Return']          = str(round(100*trade.profit_percent, 2)) + "%"

    with open(RESULTS_FILE, 'a') as f:
        csv_writer = csv.DictWriter(f, fieldnames, delimiter=',', quotechar='"')
        csv_writer.writerow(csvrow)

    print("Writing trade for " + str(date))
    
