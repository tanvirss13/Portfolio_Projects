"""
This class represents a complete trade,
with opening and closing transactions.
"""
import datetime
import random
import itertools
import train_params
import load_trades
import math
from dateutil import parser
from statistics import mean
from Transaction import Transaction

class Trade:

    def __init__(self):
        self.opening_transactions = []
        self.closing_transactions = []
        self.open_date            = None
        self.open_rel_date        = None
        self.close_date           = None
        self.close_rel_date       = None
        self.open_value           = None # Actual amount is 100x.
        self.open_rel_value       = None
        self.close_value          = None # Actual amount is 100x.
        self.earnings_date        = None
        self.max_possible_loss    = None # Actual amount is 100x.
        self.premium2margin       = None
        self.profit_percent       = None 
        self.profit_dollars       = None # Actual amount is 100x.
        self.position_iv          = None
        self.position_delta       = None
        self.position_theta       = None
        self.position_gamma       = None
        self.position_vega        = None
        self.original_confidence  = None # Model confidence upon open.
        self.original_category    = None # Model category upon open.
        self.current_confidence   = None # Model confidence at a given time.
        self.current_category     = None # Model category at a given time.
        self.num_compliant_trades = None # Number of compliant trades found by model at open.
        self.weight               = None # Position weight as a % of portfolio.
        self.num_contracts        = None # Number of contracts for each leg.
        self.reason               = None # String explaining why the trade was closed.
        self.daily_returns        = []   # Record of daily % returns.
        self.daily_close_values   = []   # Record of daily close values.
        self.model_name           = None # Name of the model used to evaluate this trade.
        self.original_state       = None # Features used in the model to open this trade.

        
    """Generate a random trade for a list of possibilities
       and calculate the P/L."""        
    def generate_random_trade(self,
                              transaction_candidates_by_date,
                              num_legs,
                              earnings_date,
                              legs_have_same_strike,
                              long_straddles_only=False):

        # Record the earnings date associated with this trade, if recorded.
        if earnings_date == None:
            return None
        self.earnings_date = parser.parse(earnings_date).date()

        # Pick random opening and closing dates from the candidates.
        self.open_date, self.close_date = self._get_dates(transaction_candidates_by_date)

        # Check that we actually found them.
        if self.open_date == None or self.close_date == None:
            return None

        # Pick random opening transactions from the candidates on the open_date.
        opening_transactions = self._get_opening_transactions(transaction_candidates_by_date,
                                                              num_legs,
                                                              legs_have_same_strike)
        
        # Check if we found any.
        if opening_transactions == None:
            return None
        
        # Filter for straddles, if required.
        if long_straddles_only:

            # Check number of legs.
            if num_legs != 2:
                print("Straddle search only works for 2 leg transactions.")
                return None

            # Check long.
            if opening_transactions[0].buy_or_sell == 'sell' or \
               opening_transactions[1].buy_or_sell == 'sell':
                return None

            # Check we have one put and one call.
            if opening_transactions[0].stats.option_type == \
               opening_transactions[1].stats.option_type:
                return None

            # Check the expiration dates are the same.
            if opening_transactions[0].stats.expiration != \
               opening_transactions[1].stats.expiration:
                return None

        # Record our opening transactions.
        self.opening_transactions = opening_transactions
            
        # Get our closing trades.
        symbol = self.opening_transactions[0].stats.underlying_symbol
        closing_transactions = self._get_closing_transactions(symbol, self.close_date)

        # Check if we found any.
        if closing_transactions == None:
            return None
        else:
            self.closing_transactions = closing_transactions

        # Calculate the P/L and relative dates for the trade.
        self.calculate_derived_data()

        # Return the trade.
        return self

    """Returns price adjusted for slippage."""
    def get_slippage_adjusted_price(self, bid, ask, buy_or_sell):

        if buy_or_sell == "buy":
            price = (((bid+ask)/2)+ask)/2
            price = math.ceil(price*100)/100
        else:
            price = (((bid+ask)/2)+bid)/2
            price = math.floor(price*100)/100
        return price

    """Finds equivalent trades from a list of transaction candidates."""
    def get_equivalent_trades(
            trade,
            transaction_candidates_by_date,
            earnings_date,
            max_rel_expiration_delta,
            legs_have_same_strike,
            use_supplied_rel_value=False):

        # Get compliant trade dates.
        earnings_date = parser.parse(earnings_date).date()
        earliest_open_date  = earnings_date + \
                              datetime.timedelta(days=trade.open_rel_date) - \
                              datetime.timedelta(days=params.max_open_date_delta)
        # Handle weekends.
        if earliest_open_date.weekday() == 6:
            earliest_open_date -= datetime.timedelta(days=2)
        if earliest_open_date.weekday() == 5:
            earliest_open_date -= datetime.timedelta(days=1)
            
        latest_open_date    = earnings_date + \
                              datetime.timedelta(days=trade.open_rel_date) + \
                              datetime.timedelta(days=params.max_open_date_delta)
        # Handle weekends.
        if latest_open_date.weekday() == 5:
            latest_open_date += datetime.timedelta(days=2)
        if latest_open_date.weekday() == 6:
            latest_open_date += datetime.timedelta(days=1)
            
        earliest_close_date = earnings_date + \
                              datetime.timedelta(days=trade.close_rel_date) - \
                              datetime.timedelta(days=params.max_close_date_delta)
        # Handle weekends.
        if earliest_close_date.weekday() == 6:
            earliest_close_date -= datetime.timedelta(days=2)
        if earliest_close_date.weekday() == 5:
            earliest_close_date -= datetime.timedelta(days=1)
            
        latest_close_date   = earnings_date + \
                              datetime.timedelta(days=trade.close_rel_date) + \
                              datetime.timedelta(days=params.max_close_date_delta)
        # Handle weekends.
        if latest_close_date.weekday() == 5:
            latest_close_date += datetime.timedelta(days=2)
        if latest_close_date.weekday() == 6:
            latest_close_date += datetime.timedelta(days=1)

        # Correct for dates that put us on the other side of earnings.
        if trade.open_rel_date < 0:
            if latest_open_date >= earnings_date:
                latest_open_date = earnings_date - datetime.timedelta(days=1)

                # Handle Monday earnings dates.
                if latest_open_date.weekday() == 6:
                    latest_open_date -= datetime.timedelta(days=2)
                    
        if trade.open_rel_date > 0:
            if earliest_open_date <= earnings_date:
                earliest_open_date = earnings_date + datetime.timedelta(days=1)

                # Handle Friday earnings dates.
                if earliest_open_date.weekday() == 5:
                    earliest_open_date += datetime.timedelta(days=2)
        if trade.open_rel_date == 0:
            earliest_open_date = earnings_date
            latest_open_date = earnings_date
                    
        if trade.close_rel_date < 0:
            if latest_close_date >= earnings_date:
                latest_close_date = earnings_date - datetime.timedelta(days=1)

                # Handle Monday earnings dates.
                if latest_close_date.weekday() == 6:
                    latest_close_date -= datetime.timedelta(days=2)
                    
        if trade.close_rel_date > 0:
            if earliest_close_date <= earnings_date:
                earliest_close_date = earnings_date + datetime.timedelta(days=1)

                # Handle Friday earnings dates.
                if earliest_close_date.weekday() == 5:
                    earliest_close_date += datetime.timedelta(days=2)
                    
        if trade.close_rel_date == 0:
            earliest_close_date = earnings_date
            latest_close_date = earnings_date

        # This list a list of all the equivalent transactions
        # we've identified, grouped by leg.
        equivalent_opening_transactions = []

        # Gather possible transactions for our dates.
        possible_transactions = []
        for date, transactions in transaction_candidates_by_date.items():
            if date >= earliest_open_date and date <= latest_open_date:
                possible_transactions += transactions

        # Check that the expiration is not before earnings, if required.
        if params.require_expiration_after_earnings:
            filtered_transactions = []
            for possible_transaction in possible_transactions:
                if possible_transaction.expiration > earnings_date:
                    filtered_transactions.append(possible_transaction)
            possible_transactions = filtered_transactions

        # For each leg, find equivalent transaction candidates.
        for leg in trade.opening_transactions:

            equivalent_legs = []
            for transaction_candidate in possible_transactions:

                # Does the option type match?
                if transaction_candidate.option_type != leg.stats.option_type:
                    continue

                # Is the relative strike within bounds?
                rel_strike_delta = abs(transaction_candidate.rel_strike - leg.stats.rel_strike)
                if rel_strike_delta > params.max_rel_strike_delta:
                    continue

                # Create a transaction from this transaction candidate.
                transaction = Transaction()
                transaction.stats = transaction_candidate
                transaction.buy_or_sell = leg.buy_or_sell
                
                # Is the expiration date within bounds?
                transaction_candidate_days_to_exp = (transaction.stats.expiration - \
                                                    transaction.stats.data_date).days
                leg_days_to_exp = (leg.stats.expiration - \
                                  leg.stats.data_date).days
                rel_expiration_delta = abs(transaction_candidate_days_to_exp - leg_days_to_exp)
                if rel_expiration_delta > max_rel_expiration_delta:
                    continue

                # If requested, adjust the mid to the specified relative value.
                if use_supplied_rel_value:
                    transaction.stats.mid = transaction.stats.underlying_price * leg.stats.rel_value
                    transaction.stats.calculate_derived_values()

                # OK we found a transaction that is equivalent to this leg.
                # Record it, and the relative expiration and strike deltas.
                equivalent_legs.append((transaction, rel_expiration_delta, rel_strike_delta))

            # Save these legs.
            equivalent_opening_transactions.append(equivalent_legs)

        # Sanity check that the length of this list matches our legs.
        if len(equivalent_opening_transactions) != len(trade.opening_transactions):
            print("Error in get_equivalent_trades:") 
            print("Length of equivalent legs list does not match the number of legs in our trade.")
            exit(1)

        # Only keep the n closest matches to each leg.
        filtered_legs = []
        for equivalent_legs in equivalent_opening_transactions:

            # Find the closest expiration dates and strikes to the trade we're comparing.
            equivalent_legs.sort(key=lambda equivalent_leg: (
                equivalent_leg[1], abs(equivalent_leg[2])))

            # Keep at most max_equivalent_transactions of them.
            legs = []
            for filtered_leg in equivalent_legs[:params.max_equivalent_transactions]:
                legs.append(filtered_leg[0])
            filtered_legs.append(legs)

        # Create a trade for each possible combination of opening legs and each possible close date.
        potential_trades = []
        for opening_transactions in itertools.product(*filtered_legs):

            # Exclude situations where multiple legs are the same option.
            option_roots = []
            for leg in opening_transactions:
                option_roots.append(leg.stats.option_root)
            option_roots_set = set(option_roots)
            if len(option_roots_set) != len(option_roots):
                continue

            # The legs need to be on the same date.
            open_date = opening_transactions[0].stats.data_date
            date_mismatch = False
            for leg in opening_transactions:
                if leg.stats.data_date != open_date:
                    date_mismatch = True
                    break
            if date_mismatch:
                continue

            # If the legs need to have the same strike, enforce this.
            if legs_have_same_strike:
                strike = opening_transactions[0].stats.strike
                all_have_same_strike = True
                for opening_transaction in opening_transactions:
                    if opening_transaction.stats.strike != strike:
                        all_have_same_strike = False
                if not all_have_same_strike:
                    continue

            # Ensure the expiration dates are the same, if necessary.
            if train_params.long_straddles_only:
                expiration = opening_transactions[0].stats.expiration
                expiration_mismatch = False
                for opening_transaction in opening_transactions[1:]:
                    if opening_transaction.stats.expiration != expiration:
                        expiration_mismatch = True
                        break
                if expiration_mismatch:
                    continue

            # For each possible close date, create a trade.
            # Plus one since we can close on both the earliest and latest close dates.
            num_close_dates = (latest_close_date - earliest_close_date).days + 1
            for offset in range(0, num_close_dates):
                equivalent_trade = Trade()
                equivalent_trade.opening_transactions = opening_transactions
                equivalent_trade.open_date = opening_transactions[0].stats.data_date
                equivalent_trade.close_date = earliest_close_date + datetime.timedelta(days=offset)
                equivalent_trade.earnings_date = earnings_date

                # Sanity check that the open date is before (and not equal to) the close date.
                if equivalent_trade.open_date >= equivalent_trade.close_date:
                    continue

                # Add this newly created trade to our list.
                potential_trades.append(equivalent_trade)

        # For each trade, find the closing transactions, if possible, and get the P/L.
        equivalent_trades = []
        for equivalent_trade in potential_trades:

            symbol = equivalent_trade.opening_transactions[0].stats.underlying_symbol
            closing_transactions = equivalent_trade._get_closing_transactions(
                symbol, equivalent_trade.close_date)

            # See if we found any.
            if closing_transactions == None:
                continue

            # OK we're good. Finish creating the trade.
            equivalent_trade.closing_transactions = closing_transactions
            equivalent_trade.calculate_derived_data()

            # Append to our list.
            equivalent_trades.append(equivalent_trade)

        # Return a list of equivalent trades.
        return equivalent_trades
        
    """Picks a random open and close date from the candidates."""
    def _get_dates(self, transaction_candidates_by_date):

        # Calculate the actual dates.
        earliest_open_date  = self.earnings_date + datetime.timedelta(days=params.earliest_rel_open_date)
        latest_open_date    = self.earnings_date + datetime.timedelta(days=params.latest_rel_open_date)
        earliest_close_date = self.earnings_date + datetime.timedelta(days=params.earliest_rel_close_date)
        latest_close_date   = self.earnings_date + datetime.timedelta(days=params.latest_rel_close_date)
        days_in_open_period = (latest_open_date - earliest_open_date).days
        days_in_close_period =(latest_close_date - earliest_close_date).days
        
        # Check that we have at least one weekday in our range.
        if days_in_open_period <= 2:
            print("ERROR: need at least 3 possible opening dates.")
            exit(1)
        if days_in_close_period <= 2:
            print("ERROR: need at least 3 possible closing dates.")
            exit(1)
            
        # Only use weekdays.
        open_date = datetime.date(2010, 1, 2) # A Saturday.
        close_date = datetime.date(2010, 1, 2) # A Saturday.
        while open_date.weekday() > 4:
            offset = random.randint(0, days_in_open_period - 1)
            open_date = earliest_open_date + datetime.timedelta(days=offset)
        while close_date.weekday() > 4:
            offset = random.randint(0, days_in_close_period - 1)
            close_date = earliest_close_date + datetime.timedelta(days=offset)

        return open_date, close_date

    """Pick random opening transactions on the open_date."""
    def _get_opening_transactions(self,
                                  transaction_candidates_by_date,
                                  num_legs,
                                  legs_have_same_strike):

        # Check that we have some transactions for this date.
        if self.open_date not in transaction_candidates_by_date.keys():
            return None

        # Collect all the transactions on the opening date.
        possible_opening_transactions = transaction_candidates_by_date[self.open_date]

        # Speedup - eliminate far out expirations if we can.
        if params.long_straddles_only:
            filtered_possible_opening_transactions = []
            for transaction in possible_opening_transactions:
                rel_expiration = (transaction.expiration - self.earnings_date).days
                if rel_expiration <= params.max_straddle_rel_expiration:
                    filtered_possible_opening_transactions.append(transaction)
            possible_opening_transactions = filtered_possible_opening_transactions

        # Eliminate options that expire on the opening date.
        filtered_possible_opening_transactions = []
        for transaction in possible_opening_transactions:
            if transaction.data_date != transaction.expiration:
                filtered_possible_opening_transactions.append(transaction)
        possible_opening_transactions = filtered_possible_opening_transactions

        # Eliminate far OTM or ITM options.
        filtered_possible_opening_transactions = []
        for transaction in possible_opening_transactions:
            if abs(transaction.delta) < params.max_open_leg_delta and \
               abs(transaction.delta) > params.min_open_leg_delta:
                filtered_possible_opening_transactions.append(transaction)
        possible_opening_transactions = filtered_possible_opening_transactions

        # If required, elimiate options expiring before earnings.
        if params.require_expiration_after_earnings:
            filtered_possible_opening_transactions = []
            for transaction in possible_opening_transactions:
                if transaction.expiration > self.earnings_date:
                    filtered_possible_opening_transactions.append(transaction)
            possible_opening_transactions = filtered_possible_opening_transactions

        # Handle no data.
        if len(possible_opening_transactions) == 0:
            return None

        # Find our opening transactions.
        opening_transactions = []
        while len(opening_transactions) < num_legs:

            # If this is the first leg...
            if len(opening_transactions) == 0:
                opening_transaction = self._handle_first_leg(possible_opening_transactions)

                # If necessary, filter possible transactions by strike.
                if legs_have_same_strike:
                    strike = opening_transaction.stats.strike
                    possible_opening_transactions = self._filter_transactions_by_strike(possible_opening_transactions, strike)

                    # If we only have one, it must be the first leg itself. Start over...
                    if len(possible_opening_transactions) < num_legs:
                        return None
                    
            # If this is a middle leg...
            elif len(opening_transactions) > 0 and len(opening_transactions) < (num_legs - 1):

                opening_transaction = self._handle_middle_legs(
                    possible_opening_transactions, opening_transactions)

                # Handle not finding one.
                if opening_transaction == None:
                    return None

            # If this is the last leg...
            else:

                opening_transaction = self._handle_final_leg(
                    possible_opening_transactions, opening_transactions)

                # Handle not finding one.
                if opening_transaction == None:
                    return None

            # Handle not finding one.
            if opening_transaction == None:
                return None
                
            # Store transaction.
            if opening_transaction.buy_or_sell == None:
                print("ERROR opening_transaction missing buy/sell flag.")
            opening_transactions.append(opening_transaction)

        return opening_transactions

    """Find random closing trades that close the opening trades."""
    def _get_closing_transactions(self, symbol, date):

        # Find all transactions on the closing date.
        possible_closing_transactions = load_trades.get_transaction_candidates_by_date_and_symbol(symbol, date, date, 0)
        if len(possible_closing_transactions) == 0:
            return None

        # Pick the closing trades at random to close each leg.
        closing_transactions = []
        for opening_transaction in self.opening_transactions:

            closing_transaction = Transaction()
            found_closing_transaction = False
            # Find the closing transaction to match
            # the earlier opening one for this option.
            for possible_closing_transaction in possible_closing_transactions:
                if possible_closing_transaction.option_root == opening_transaction.stats.option_root:
                    closing_transaction.stats = possible_closing_transaction
                    found_closing_transaction = True
                    break

            # Handle not finding it.
            if not found_closing_transaction:
                self.closing_transactions = []
                return None
            
            # Indicate whether the closing transaction is a buy or sell.
            if opening_transaction.buy_or_sell == "buy":
                closing_transaction.buy_or_sell = "sell"
            else:
                closing_transaction.buy_or_sell = "buy"

            # Save.
            closing_transactions.append(closing_transaction)

        return closing_transactions

    """Get the first leg of the opening trade."""
    def _handle_first_leg(self, possible_opening_transactions):
        opening_transaction = Transaction()
        opening_transaction.stats = random.choice(possible_opening_transactions)

        # Handle long straddles.
        if params.long_straddles_only:
            opening_transaction.buy_or_sell = "buy"
        else:
            opening_transaction.assign_random_buy_sell()
        return opening_transaction

    """Get the middle legs, that comply with our requirements."""
    def _handle_middle_legs(self, possible_opening_transactions,
                           opening_transactions):
        opening_transaction = Transaction()

        # Remove existing legs from our possibilities.
        possible_opening_transactions = self._filter_existing_legs(
            possible_opening_transactions, opening_transactions)

        # If there are no possibilities left, start over.
        if len(possible_opening_transactions) == 0:
            return None
        else:
            opening_transaction.stats = random.choice(possible_opening_transactions)
            opening_transaction.assign_random_buy_sell()
        return opening_transaction

    def _handle_final_leg(self,
                          possible_opening_transactions,
                          opening_transactions):
        opening_transaction = Transaction()

        # Remove existing legs from our possibilities.
        possible_opening_transactions = self._filter_existing_legs(
            possible_opening_transactions, opening_transactions)

        # If there are no possibilities left, start over.
        if len(possible_opening_transactions) == 0:
            return None

        # Eliminate positions that are out of our delta bounds.
        greeks = self.get_position_greeks(opening_transactions)
        initial_delta = greeks['delta']

        # Shuffle the list.
        random.shuffle(possible_opening_transactions)

        # Pick the first transaction that gets us to delta neutral.
        found_compliant_transaction = False
        for transaction in possible_opening_transactions:

            if initial_delta + transaction.delta < params.max_position_delta and \
               initial_delta + transaction.delta > params.min_position_delta:
                opening_transaction.stats = transaction
                opening_transaction.buy_or_sell = "buy"
                found_compliant_transaction = True
                break
            if initial_delta - transaction.delta < params.max_position_delta and \
               initial_delta - transaction.delta > params.min_position_delta:

                opening_transaction.stats = transaction
                opening_transaction.buy_or_sell = "sell"
                found_compliant_transaction = True
                break
                
        # Handle not finding any.
        if not found_compliant_transaction:
            return None

        return opening_transaction

    """Return a list of transactions with the given strike."""
    def _filter_transactions_by_strike(self, possible_transactions, strike):
        filtered_transactions = []
        for transaction in possible_transactions:
            if transaction.strike == strike:
                filtered_transactions.append(transaction)
        return filtered_transactions

    """Remove existing legs from the possible transactions."""
    def _filter_existing_legs(self, possible_transactions, existing_transactions):
        filtered_transactions = []
        for possible_transaction in possible_transactions:
            transaction_is_present = False
            for existing_transaction in existing_transactions:
                if possible_transaction.option_root == existing_transaction.stats.option_root:
                    transaction_is_present = True
            if not transaction_is_present:
                filtered_transactions.append(possible_transaction)
        return filtered_transactions

    """Calculate the P/L and relative dates for the trade."""
    def calculate_derived_data(self):

        # Greeks for the entire position.
        greeks = self.get_position_greeks(self.opening_transactions)
        self.position_iv    = greeks['iv']
        self.position_delta = greeks['delta']
        self.position_gamma = greeks['gamma']
        self.position_theta = greeks['theta']
        self.position_vega  = greeks['vega']

        # Calculate relative earnings date.
        if self.earnings_date:
            self.open_rel_date = (self.open_date - self.earnings_date).days

        # Calculate the open date and close date relative to the earnings date.
        if self.earnings_date and self.close_date:
            self.close_rel_date = (self.close_date - self.earnings_date).days
            
        # Open Value
        self.open_value = 0
        for opening_transaction in self.opening_transactions:
            if opening_transaction.buy_or_sell == "buy":

                # Adjust for slippage if required.
                if train_params.use_avg_mid_market == True:
                    mid = self.get_slippage_adjusted_price(opening_transaction.stats.bid,
                                                           opening_transaction.stats.ask,
                                                           opening_transaction.buy_or_sell)
                else:
                    mid = opening_transaction.stats.mid
                self.open_value = self.open_value + mid
            else:

                # Adjust for slippage if required.
                if train_params.use_avg_mid_market == True:
                    mid = self.get_slippage_adjusted_price(opening_transaction.stats.bid,
                                                           opening_transaction.stats.ask,
                                                           opening_transaction.buy_or_sell)
                else:
                    mid = opening_transaction.stats.mid
                self.open_value = self.open_value - mid
                
        # Calculate the price relative to the underlying on the open date.
        self.open_rel_value = self.open_value/self.opening_transactions[0].stats.underlying_price

        # Set max possible loss for two legs.
        if len(self.opening_transactions) == 2:

            # If both long.
            if self.opening_transactions[0].buy_or_sell == 'buy' and \
               self.opening_transactions[1].buy_or_sell == 'buy':
                self.max_possible_loss = self.open_value

            # Both puts or both calls.
            if self.opening_transactions[0].stats.option_type == \
               self.opening_transactions[1].stats.option_type:
                
                # One short leg.
                if self.opening_transactions[0].buy_or_sell != \
                   self.opening_transactions[1].buy_or_sell:

                    self.max_possible_loss = abs(self.opening_transactions[0].stats.strike - \
                                                 self.opening_transactions[1].stats.strike)

        # Set max possible loss for one leg.
        if len(self.opening_transactions) == 1:

            # Long.
            if self.opening_transactions[0].buy_or_sell == 'buy':
                self.max_possible_loss = self.open_value
            else: # Short
                self.max_possible_loss = float("inf")

        # Error check.
        if self.max_possible_loss != None and self.max_possible_loss < 0:
            print("ERROR max_possible_loss < 0 in Trade.py")
            self.print_trade()
            exit(0)

        # Calculate premium2margin.
        if self.open_value < 0:
            if self.max_possible_loss == None or self.max_possible_loss == 0:
                self.premium2margin = None
            else:
                self.premium2margin = abs(self.open_value)/self.max_possible_loss

        else:
            self.premium2margin = 1
                            
        # Calculate closing stats, if applicable.
        if len(self.closing_transactions) > 0 and self.close_date:
            self.calculate_closing_stats()

    def calculate_closing_stats(self):

        # Avoid div by zero.
        if self.open_value == 0:
            self.open_value = .01

        # Close Value.
        self.close_value = 0
        for closing_transaction in self.closing_transactions:
            if closing_transaction.buy_or_sell == "buy":

                # Adjust for slippage if required.
                if train_params.use_avg_mid_market == True:
                    mid = self.get_slippage_adjusted_price(closing_transaction.stats.bid,
                                                           closing_transaction.stats.ask,
                                                           closing_transaction.buy_or_sell)
                else:
                    mid = closing_transaction.stats.mid
                self.close_value = self.close_value - mid
            else:

                # Adjust for slippage if required.
                if train_params.use_avg_mid_market == True:
                    mid = self.get_slippage_adjusted_price(closing_transaction.stats.bid,
                                                           closing_transaction.stats.ask,
                                                           closing_transaction.buy_or_sell)
                else:
                    mid = closing_transaction.stats.mid
                self.close_value = self.close_value + mid

        # Profit Calcluations.
        if self.open_value == None or self.close_value == None:
            print("ERROR: open_value or close_value is None in Trade.py")
            exit(1)
        self.profit_dollars = round(self.close_value - self.open_value - \
                                    (2 * len(self.opening_transactions) * train_params.commission), 2)
            
        # Calculate percentages (return-on-margin if short).
        self.profit_percent = self.profit_dollars/self.max_possible_loss

        # Sanity check.
        # Note that it is possible on a temporary basis for the loss
        # to be greater than max_possible_loss. It would be irrational
        # to close trades at such a point, so the profit_percent is
        # clamped to -1.
        if self.profit_percent < -1:
            self.profit_percent = -1

    """Returns the current value of this trade."""
    def get_current_value(self, current_date):
        current_value = 0.0
        for opening_transaction in self.opening_transactions:
            mid = load_trades.get_mid(opening_transaction.stats.option_root, current_date)
            if mid == None:
                return None
            if opening_transaction.buy_or_sell == 'buy':
                current_value += mid
            else:
                current_value -= mid
        return current_value

    """Are two trades considered equivalent in terms of strikes, dates, etc."""
    def are_trades_equivalent(self, test_trade, max_rel_expiration_delta):

        # Is open date (w/r/t the applicable earnings date) more-or-less the same?
        open_date_delta = abs(self.open_rel_date - test_trade.open_rel_date)
        if open_date_delta > params.max_open_date_delta:
            return False

        # Is the close date (w/r/t the applicable earnings date) more-or-less the same?
        close_date_delta = abs(self.close_rel_date - test_trade.close_rel_date)
        if close_date_delta > params.max_close_date_delta:
            return False

        # Make a list of the expirations, strikes, buy/sell, and option type in the trade.
        trade_stats = []
        for opening_transaction in self.opening_transactions:
            trade_stat = (
                opening_transaction.get_rel_expiration(self.earnings_date),
                opening_transaction.stats.rel_strike,
                opening_transaction.buy_or_sell,
                opening_transaction.stats.option_type)
            trade_stats.append(trade_stat)

        # Make the same list for the test trade.
        test_trade_stats = []
        for opening_transaction in test_trade.opening_transactions:
            test_trade_stat = (
                opening_transaction.get_rel_expiration(test_trade.earnings_date),
                opening_transaction.stats.rel_strike,
                opening_transaction.buy_or_sell,
                opening_transaction.stats.option_type)
            test_trade_stats.append(test_trade_stat)

        # See if the lists match.
        for trade_expiration, trade_strike, trade_buysell, trade_option_type in trade_stats:
        
            for test_trade_stat in test_trade_stats:

                # Unpack.
                test_trade_expiration  = test_trade_stat[0]
                test_trade_strike      = test_trade_stat[1]
                test_trade_buysell     = test_trade_stat[2]
                test_trade_option_type = test_trade_stat[3]

                # Calculate deltas.
                rel_expiration_delta = abs(trade_expiration - test_trade_expiration)
                rel_strike_delta = abs(trade_strike - test_trade_strike)

                # If we found a match, remove it from the test_trade list.
                if rel_expiration_delta < max_rel_expiration_delta and \
                   rel_strike_delta < params.max_rel_strike_delta and \
                   trade_buysell == test_trade_buysell and \
                   trade_option_type == test_trade_option_type:
                    test_trade_stats.remove(test_trade_stat)
                    break

        # If there are none left, we found a matching trade.
        if len(test_trade_stats) != 0:
            return False
    
        # We have a match.
        return True

    """Are trades identical?"""
    def are_trades_identical(self, test_trade):

        # Are the open dates the same?
        if self.open_date != test_trade.open_date:
            return False

        # Are the close dates the same?
        if self.close_date != test_trade.close_date:
            return False

        # Compare the option_root and buy_or_sell of each trade.
        trade_stats = set()
        for leg in self.opening_transactions:
            trade_stats.add((leg.stats.option_root, leg.buy_or_sell))

        test_trade_stats = set()
        for leg in test_trade.opening_transactions:
            test_trade_stats.add((leg.stats.option_root, leg.buy_or_sell))

        if trade_stats != test_trade_stats:
            return False
        return True

    """See if this is one of several types of trade."""
    def get_trade_type(self):

        if params.num_legs == 1:
            if self.opening_transactions[0].buy_or_sell == 'buy':
                if self.opening_transactions[0].stats.option_type == 'call':
                    return "long call"
                else:
                    return "long put"
            else:
                if self.opening_transactions[0].stats.option_type == 'call':
                    return "short call"
                else:
                    return "short put"

        # Only do this if the strikes are the same.
        if not params.legs_have_same_strike:
            return ""

        short_expiration = None
        long_expiration = None
        leg0 = self.opening_transactions[0]
        leg1 = self.opening_transactions[1]

        # Is it a calendar at all?
        if leg0.buy_or_sell == 'sell' and leg1.buy_or_sell == 'buy':
            short_expiration = leg0.stats.expiration
            long_expiration  = leg1.stats.expiration
        elif leg0.buy_or_sell == 'buy' and leg1.buy_or_sell == 'sell':
            long_expiration  = leg0.stats.expiration
            short_expiration = leg1.stats.expiration
        elif leg0.buy_or_sell == 'buy' and leg1.buy_or_sell == 'buy':
            return "long_straddle"
        else:
            return ""
        
        # Calendars
        if short_expiration > long_expiration:
            return "reverse_calendar"
        if short_expiration < long_expiration:
            return "calendar"
        
        # Unrecognized
        return ""

    """Returns the greeks of a set of transactions."""
    def get_position_greeks(self, transactions):
        greeks = {'iv': 0.0, 'delta': 0.0, 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0}

        iv = []
        for transaction in transactions:
            iv.append(float(transaction.stats.iv))
            if transaction.buy_or_sell == "buy":
                greeks['delta'] = greeks['delta'] + transaction.stats.delta
                greeks['gamma'] = greeks['gamma'] + transaction.stats.gamma
                greeks['theta'] = greeks['theta'] - transaction.stats.theta
                greeks['vega']  = greeks['vega']  + transaction.stats.vega
            else:
                greeks['delta'] = greeks['delta'] - transaction.stats.delta
                greeks['gamma'] = greeks['gamma'] - transaction.stats.gamma
                greeks['theta'] = greeks['theta'] + transaction.stats.theta
                greeks['vega']  = greeks['vega']  - transaction.stats.vega
        greeks['iv'] = mean(iv)
        return greeks

    """Return a string with the results of a trade."""
    def print_trade(self):
            
        results = ""
        results += "\n Open Date: " + str(self.open_date)
        results += "\n Close Date: " + str(self.close_date)
        results += "\n Original Confidence: " + str(self.original_confidence)
        results += "\n Original Category: " + str(self.original_category)
        results += "\n Current Confidence: " + str(self.current_confidence)
        results += "\n Current Category: " + str(self.current_category)
        results += "\n Max Possible Loss: " + str(self.max_possible_loss)
        results += "\n Weight: " + str(self.weight)
        results += "\n Num. Contracts: " + str(self.num_contracts)
        results += "\n Profit: $" + str(self.profit_dollars)
        if self.profit_percent:
            results += "\n Profit: " + str(round(100*self.profit_percent, 2)) + "%"

        results += "\n Underlying Open Price: " + str(self.opening_transactions[0].stats.underlying_price)
        if len(self.closing_transactions) != 0:
            results += "\n Underlying Close Price: " + str(self.closing_transactions[0].stats.underlying_price)
        results += "\n Open Value: $" + str(round(self.open_value, 2))
        if self.close_value != None:
            results += "\n Close Value: $" + str(round(self.close_value, 2))
        else:
            results += "\n Close Value: None"
        if self.open_rel_value:
            results += "\n Relative Value: " + str(round(100*self.open_rel_value, 2)) + "%"
        results += "\n Position IV: " + str(self.position_iv)
        results += "\n Position Delta: " + str(self.position_delta)
        results += "\n Position Gamma: " + str(self.position_gamma)
        results += "\n Position Theta: " + str(self.position_theta)
        results += "\n Position Vega: " + str(self.position_vega)
        results += "\n------OPENING TRANSACTIONS----"
        for opening_transaction in self.opening_transactions:
            results += "\n  - " + opening_transaction.buy_or_sell
            results += "\n  - " + opening_transaction.stats.option_type
            results += "\n  - Strike: " + str(opening_transaction.stats.strike)
            results += "\n  - Relative Strike: " + str(opening_transaction.stats.rel_strike)
            results += "\n  - Bid: " + str(opening_transaction.stats.bid)
            results += "\n  - Ask: " + str(opening_transaction.stats.ask)
            results += "\n  - Mid: " + str(opening_transaction.stats.mid)
            results += "\n  - Bid/Ask Spread: " + str(round(
                100*opening_transaction.stats.bid_ask_spread, 2)) + "%"
            results += "\n  - Delta: " + str(opening_transaction.stats.delta)
            results += "\n  - Data Date: " + str(opening_transaction.stats.data_date)
            results += "\n  - Expiration: " + str(opening_transaction.stats.expiration)
            results += "\n  - Volume: " + str(opening_transaction.stats.volume)
            results += "\n  - Open Interest: " + str(opening_transaction.stats.open_interest)
            results += "\n  - ID: " + str(opening_transaction.stats.option_root)
        results += "\n------CLOSING TRANSACTIONS----"
        for closing_transaction in self.closing_transactions:
            results += "\n  - " + closing_transaction.buy_or_sell
            results += "\n  - " + closing_transaction.stats.option_type
            results += "\n  - Bid: " + str(closing_transaction.stats.bid)
            results += "\n  - Ask: " + str(closing_transaction.stats.ask)
            results += "\n  - Mid: " + str(closing_transaction.stats.mid)
            results += "\n  - Bid/Ask Spread: " + str(round(
                100*closing_transaction.stats.bid_ask_spread, 2)) + "%"
            results += "\n  - ID: " + str(closing_transaction.stats.option_root)
            results += "\n  - Data Date: " + str(closing_transaction.stats.data_date)
            results += "\n  - Volume: " + str(closing_transaction.stats.volume)
            results += "\n  - Open Interest: " + str(closing_transaction.stats.open_interest)
        return results

    """Calculate the number of contracts."""
    def calculate_position_size(self,
                                num_compliant_trades,
                                avg_compliant_trades,
                                avg_confidence,
                                base_trade_size,
                                max_position_size,
                                portfolio_value):

        # Error check.
        if base_trade_size > max_position_size:
            print("ERROR: base_trade_size larger than max_position_size.")
            exit(1)

        self.num_compliant_trades = num_compliant_trades
        
        # Calculate the weight based on the number
        # of compliant trades on this day and the confidence.
        weight = (num_compliant_trades/ \
                  avg_compliant_trades) * \
                  (self.original_confidence / \
                   avg_confidence)
        weight *= base_trade_size

        # Limit to max.
        if weight > max_position_size:
            weight = max_position_size
        self.weight = weight

        # Calculate the number of contracts.
        exposure = self.max_possible_loss * 100
        num_contracts = (portfolio_value * weight) /\
                        exposure
        self.num_contracts = int(num_contracts)

        # Error check.
        if num_contracts < 0:
            print("ERROR: num_contracts < 0 in Trade.py")
            self.print_trade()
            exit(1)

    """Returns a list of strings representing the legs."""
    def get_leg_strings(self):
        
        leg_strings = []
        for leg in self.opening_transactions:
            leg_string = leg.buy_or_sell.upper() + \
                         " " + \
                         str(leg.stats.underlying_symbol) + \
                         " $" + \
                         str(leg.stats.strike) + \
                         " " + \
                         str(leg.stats.expiration) + \
                         " " + \
                         leg.stats.option_type + \
                         " Mid: $" + \
                         str(leg.stats.mid) + \
                         " (" + \
                         str(leg.stats.option_root) + \
                         ")"
            leg_strings.append(leg_string)
        return leg_strings
