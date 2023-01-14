import psycopg2
import datetime
from importlib import import_module
from TransactionCandidate import TransactionCandidate

"""Load all trades that meet our parameters
   around each earnings date that we have in 
   the DB for this security. Returns a list of tuples:
   (earnings_date, trade_candidates)"""
def load(underlying_symbol,
         earliest_data_date,
         latest_data_date,
         earliest_rel_open_date,
         latest_rel_close_date,
         min_open_interest,
         max_bid_ask_spread=None):

    # Upcase.
    underlying_symbol = underlying_symbol.upper()

    # Get the earnings dates associated with this symbol.
    earnings_dates = get_earnings_dates(underlying_symbol)

    # Keys: earnings_date, Value: transaction_candidates_tuple
    candidates_by_earnings_and_date = dict()

    # Collect candidate transactions.
    for earnings_date in earnings_dates:

        # Don't search earnings dates that are too early or too late.
        if earliest_data_date:
            if earnings_date < earliest_data_date:
                continue
        if latest_data_date:
            if earnings_date > latest_data_date:
                continue

        # Get the eligible transactions for this symbol and earnings date.
        candidates_by_date = get_transaction_candidates(earnings_date,
                                                        underlying_symbol,
                                                        earliest_data_date,
                                                        latest_data_date,
                                                        earliest_rel_open_date,
                                                        latest_rel_close_date,
                                                        min_open_interest,
                                                        max_bid_ask_spread)

        # Store.
        if len(candidates_by_date) > 0:
            candidates_by_earnings_and_date[str(earnings_date)] = candidates_by_date

    return candidates_by_earnings_and_date

"""Returns a list of earnings dates for this symbol."""
def get_earnings_dates(underlying_symbol):
    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("SELECT earnings_date FROM earnings_dates WHERE underlying_symbol=%s;", (underlying_symbol,))
        earnings_dates_tuples = cursor.fetchall()
        
    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        print(e.message)
        exit(1)

    finally:
        if connection:
            connection.close()

    # Convert the tuples to a plain list.
    earnings_dates = []
    for instance in earnings_dates_tuples:
        earnings_dates.append(instance[0])
    return earnings_dates

"""Returns a earnings data for this symbol."""
def get_earnings_data(underlying_symbol):
    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("SELECT earnings_date, earnings_estimate, reported_earnings, before_or_after FROM earnings_dates WHERE underlying_symbol=%s;", (underlying_symbol,))
        earnings_data_tuples = cursor.fetchall()
        
    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        print(e.message)
        exit(1)

    finally:
        if connection:
            connection.close()

    # Convert the tuples to a plain list.
    earnings_data = []
    for instance in earnings_data_tuples:
        row = dict()
        row['earnings_date'] = instance[0]
        row['earnings_estimate'] = instance[1]
        row['reported_earnings'] = instance[2]
        row['before_or_after'] = instance[3]
        earnings_data.append(row)
    return earnings_data

"""Pull the eligible transactions from the DB."""
def get_transaction_candidates(earnings_date,
                               underlying_symbol,
                               earliest_data_date,
                               latest_data_date,
                               earliest_rel_open_date,
                               latest_rel_close_date,
                               min_open_interest,
                               max_bid_ask_spread=None):

    # Set date limits for trading candidates.
    earliest_date = earnings_date + datetime.timedelta(days=earliest_rel_open_date)
    latest_date = earnings_date + datetime.timedelta(days=latest_rel_close_date)

    # Adjust for weekends.
    if earliest_date.weekday() == 6:
        earliest_date -= datetime.timedelta(days=2)
    if earliest_date.weekday() == 5:
        earliest_date -= datetime.timedelta(days=1)
    if latest_date.weekday() == 6:
        latest_date += datetime.timedelta(days=1)
    if latest_date.weekday() == 5:
        latest_date += datetime.timedelta(days=2)

    # Pull transaction candidates for each date in our range.
    candidates_by_date = dict()
    data_date = earliest_date
    while data_date <= latest_date:

        # Handle earliest/latest data dates.
        if earliest_data_date:
            if data_date < earliest_data_date:
                data_date += datetime.timedelta(days=1)
                continue
        if latest_data_date:
            if data_date > latest_data_date:
                break

        transaction_candidates = get_transaction_candidates_by_date_and_symbol(
            underlying_symbol, data_date, data_date, min_open_interest, earnings_date, max_bid_ask_spread)

        # If we found some, store.
        if len(transaction_candidates) > 0:
            candidates_by_date[data_date] = transaction_candidates
        data_date += datetime.timedelta(days=1)

    return candidates_by_date

"""Converts a raw database result to a TransactionCandidate."""
def _convert_to_transaction_candidates(transaction_candidates_tuple, earnings_date, max_bid_ask_spread=None, calculate_greeks=True):

    transaction_candidates = []
    # Convert to CandidateTransaction object and add derived data.
    for transaction_candidate_tuple in transaction_candidates_tuple:

        # Create the object.
        transaction_candidate = TransactionCandidate(transaction_candidate_tuple)

        # Error check.
        if transaction_candidate.underlying_price == 0:
            continue

        # Calculate derived data.
        transaction_candidate.calculate_mid()
        transaction_candidate.calculate_derived_values(calculate_greeks)

        # Filter for bid-ask spread.
        if max_bid_ask_spread:
            if transaction_candidate.bid_ask_spread > max_bid_ask_spread:
                continue

        # Store
        transaction_candidates.append(transaction_candidate)
    return transaction_candidates

"""
Returns symbols for all companies releasing earnings on the indicated date.
Indicates whether the announcement is before or after market close (or neither).
"""
def get_upcoming_earnings(earnings_date):

    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("""SELECT underlying_symbol, before_or_after FROM earnings_dates WHERE
                          earnings_date=%s;""", (earnings_date,))
        symbols_tuple = cursor.fetchall()
        symbols = []
        for symbol_tuple in symbols_tuple:
            symbols.append((symbol_tuple[0], symbol_tuple[1]))
    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        print(e.message)
        exit(1)
    finally:
        if connection:
            connection.close()
    return symbols

"""Returns transaction candidates for a given date and symbol."""
def get_transaction_candidates_by_date_and_symbol(
        underlying_symbol, earliest_date, latest_date, min_open_interest, earnings_date=None, max_bid_ask_spread=None, calculate_greeks=True):

    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("""SELECT 
                          o.underlying_symbol, 
                          o.underlying_price, 
                          o.exchange, 
                          o.option_root, 
                          o.option_ext, 
                          o.option_type, 
                          o.expiration,     
                          o.data_date, 
                          o.strike, 
                          o.last, 
                          o.bid, 
                          o.ask, 
                          o.volume, 
                          o.open_interest, 
                          o.t1_open_interest, 
                          g.iv, 
                          g.delta, 
                          g.gamma, 
                          g.theta, 
                          g.vega 
                          FROM option_prices o
                          LEFT OUTER JOIN cached_greeks g ON
                          (o.data_date = g.data_date AND
                          o.option_root = g.option_root AND
                          o.underlying_symbol = g.underlying_symbol)
                          WHERE
                          o.underlying_symbol=%s AND 
                          o.data_date>=%s AND
                          o.data_date<=%s AND
                          o.open_interest>=%s;""",
                       (underlying_symbol,
                        earliest_date,
                        latest_date,
                        min_open_interest))

        transaction_candidates_tuple = cursor.fetchall()

    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        print(e.message)
        exit(1)
    finally:
        if connection:
            connection.close()

    return _convert_to_transaction_candidates(transaction_candidates_tuple, earnings_date, max_bid_ask_spread, calculate_greeks)

"""Decide if this underlying has weekly or just monthly options."""
def only_monthly_options(underlying_symbol, data_date):

    underlying_symbol = underlying_symbol.upper()
    connection = None

    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("""SELECT DISTINCT option_root FROM option_prices WHERE
                          underlying_symbol=%s AND
                          data_date=%s;""",
                       (underlying_symbol, data_date))
        option_roots = cursor.fetchall()

    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        exit(1)
    finally:
        if connection:
            connection.close()

    expirations = set()
    for option_root in option_roots:

        # Cut the string at the first substring of numbers.
        expiration = option_root[0].replace(underlying_symbol, '')
        expiration = expiration[0:6]
        expirations.add(expiration)

    # If there are more than one expiration per month, we have weeklies.
    expiration_yymm = []
    for expiration in expirations:
        expiration_yymm.append(expiration[0:4])

    if len(set(expiration_yymm)) != len(expiration_yymm):
        print("Using weekly options.")
        return False # Weeklies.
    print("Using monthly options.")
    return True # Monthlies

"""Stores a new entry in the cached_greeks table."""
def store_greeks(data_date,
                 option_root,
                 underlying_symbol,
                 iv,
                 delta,
                 gamma,
                 theta,
                 vega):

    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("""INSERT INTO cached_greeks (
                          data_date, 
                          option_root, 
                          underlying_symbol, 
                          iv, 
                          delta, 
                          gamma, 
                          theta, 
                          vega) VALUES (
                          %s,
                          %s,
                          %s,
                          %s,
                          %s,
                          %s,
                          %s,
                          %s);""",
                       (data_date,
                        option_root,
                        underlying_symbol,
                        iv,
                        delta,
                        gamma,
                        theta,
                        vega))
        connection.commit()
    except psycopg2.IntegrityError as ie:
        if connection:
            connection.rollback()
    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        exit(1)
    finally:
        if connection:
            connection.close()

"""Returns n calendar days' worth of underlying prices."""
def get_underlying_prices(underlying_symbol, date, num_days, return_dates=False):

    end_date = date
    start_date = end_date - datetime.timedelta(days=num_days)

    # Load market holidays file.
    market_holidays_file = import_module('market_holidays.py'.replace('.py', ''))
    market_holidays = market_holidays_file.market_holidays

    # Make a list of trading dates.
    trading_dates = set()
    date = start_date
    while date <= end_date:
        if date.weekday() < 5 and \
           date not in market_holidays:
            trading_dates.add(date)
        date += datetime.timedelta(days=1)

    # Set up the DB.
    connection = None
    connection = psycopg2.connect(database='backtest_data')
    cursor = connection.cursor()
    
    try:
        # Check the cache.
        cursor.execute("""SELECT DISTINCT underlying_price, data_date FROM 
                          cached_prices WHERE data_date>=%s AND data_date<=%s
                          AND underlying_symbol=%s;""",
                       (start_date, end_date, underlying_symbol))
        price_tuples = cursor.fetchall()
        prices_by_date = dict()
        for price, date in price_tuples:
            if price == None:
                continue
            prices_by_date[date] = float(price.replace('$', '').replace(',', ''))

        # Get the missing dates.
        missing_dates = trading_dates.difference(prices_by_date.keys())
        for date in missing_dates:
            cursor.execute("""SELECT DISTINCT underlying_price, data_date FROM 
                              option_prices WHERE data_date=%s
                              AND underlying_symbol=%s;""",
                           (date, underlying_symbol))
            price_tuples = cursor.fetchall()

            # Error check.
            if len(price_tuples) > 1:
                print("ERROR: multiple prices in option_prices: " + str(date) + " " + underlying_symbol)
            for price, date in price_tuples:
                if price == None:
                    continue
                prices_by_date[date] = float(price.replace('$', '').replace(',', ''))

            # If we are missing a price for a trading date, something is wrong.
            if len(price_tuples) == 0:
                print("********************")
                print("WARNING: no price data for trading date: " + str(date) + " " + underlying_symbol)
                print("********************")
            else:
                # Insert into the cache.
                cursor.execute("""INSERT INTO cached_prices (
                              data_date,
                              underlying_symbol,
                              underlying_price) VALUES (
                              %s,
                              %s,
                              %s);""", (date, underlying_symbol, price))
                connection.commit()

    except psycopg2.DatabaseError as e:
        if connection:
            connection.rollback()
        exit(1)
    finally:
        if connection:
            connection.close()

    # Only return a list of prices.
    if not return_dates:
        prices = []
        date = start_date
        while date <= end_date:
            if date in prices_by_date.keys():
                prices.append(prices_by_date[date])
            date += datetime.timedelta(days=1)
        return prices
    else:
        return prices_by_date

"""Returns the underlying move for the last earnings date."""
def get_earnings_move(underlying_symbol, earnings_date, before_or_after=None):

    # If reporting after close...
    before_earnings_date = None
    if before_or_after == 'AC':
        before_earnings_date = earnings_date
    else: # Reporting before open or N/A.
        before_earnings_date = earnings_date - datetime.timedelta(days=1)
        if before_earnings_date.weekday() == 6:
            before_earnings_date -= datetime.timedelta(days=2)

    # If reporting before open...
    after_earnings_date = None
    if before_or_after == 'BO':
        after_earnings_date = earnings_date
    else: # Reporting after close or N/A.
        after_earnings_date = earnings_date + datetime.timedelta(days=1)
        if after_earnings_date.weekday() == 5:
            after_earnings_date += datetime.timedelta(days=2)    
 
    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()

        # Before earnings price.
        cursor.execute("""SELECT underlying_price FROM option_prices
                          WHERE underlying_symbol=%s AND 
                          data_date=%s;""",
                       (underlying_symbol, before_earnings_date))
        before_price_tuple = cursor.fetchone()

        # If we have no data, return 0.
        if before_price_tuple == None or len(before_price_tuple) == 0:
            return 0.0
        before_price = float(before_price_tuple[0].replace('$', '').replace(',', ''))
        
        # After earnings price.
        cursor.execute("""SELECT underlying_price FROM option_prices
                          WHERE underlying_symbol=%s AND
                          data_date=%s;""",
                       (underlying_symbol, after_earnings_date))
        after_price_tuple = cursor.fetchone()

        # If we have no data, return 0.
        if after_price_tuple == None or len(after_price_tuple) == 0:
            return 0.0
        after_price = float(after_price_tuple[0].replace('$', '').replace(',', ''))

    except psycopg2.DatabaseError:
        if connection:
            connection.rollback()
        exit(1)
    finally:
        if connection:
            connection.close()

    # Calculate the change and return.
    earnings_move = (after_price - before_price)/before_price
    return earnings_move
        
"""Returns the mid of a given option on a given date."""
def get_mid(option_root, date):

    connection = None
    try:
        connection = psycopg2.connect(database='backtest_data')
        cursor = connection.cursor()
        cursor.execute("""SELECT bid, ask FROM option_prices
                          WHERE option_root=%s AND
                          data_date=%s;""",
                       (option_root, date))
        bid_ask_tuple = cursor.fetchone()
        if bid_ask_tuple == None or len(bid_ask_tuple) == 0:
            return None
        bid = float(bid_ask_tuple[0].replace('$', '').replace(',', ''))
        ask = float(bid_ask_tuple[1].replace('$', '').replace(',', ''))
        mid = round((bid + ask)/2, 2)
    except psycopg2.DatabaseError:
        if connection:
            connection.rollback()
        exit(1)
    finally:
        if connection:
            connection.close()
    return mid

"""Returns the date of the next earnings, or None if there is none."""
def get_next_earnings(symbol, current_date):

    earnings_dates = get_earnings_dates(symbol)
    earnings_dates.sort()
    for earnings_date in earnings_dates:
        if earnings_date >= current_date:
            return earnings_date
    return None


