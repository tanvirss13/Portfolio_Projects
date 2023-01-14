"""
Simple class representing a purchase
or sale of a transaction candidate, and
a single leg of a trade.
"""
import random

class Transaction:

    def __init__(self):
        # This is a TransactionCandidate.
        self.stats = None

        # Either "buy" or "sell"
        self.buy_or_sell = None

    # Assign a random buy or sell.
    def assign_random_buy_sell(self):
        if random.uniform(0, 1) > .5:
            self.buy_or_sell = "buy"
        else:
            self.buy_or_sell = "sell"

    """Returns the expiration date relative to the provided earnings date."""
    def get_rel_expiration(self, earnings_date):
        return (self.stats.expiration - earnings_date).days
            
    """Convenience function to print the info for this transaction."""
    def print_stats(self):
        result = ""
        result += self.stats.underlying_symbol
        result += self.buy_or_sell
        result += self.stats.option_type
        result += "Data Date: " + str(self.stats.data_date)
        result += "Expiration: " + str(self.stats.expiration)
        result += "Underlying Price: " + str(self.stats.underlying_price)
        result += "Strike: " + str(self.stats.strike)
        result += "Price: " + str(self.stats.mid) 
        result += "Implied Volatiliy: " + str(self.stats.iv)
        result += "Delta: " + str(self.stats.delta)
        return result


