"""
This class represents option data for a particular
date. It is comprised both of data directly from the
DB and also derived data that can be calculated.
"""
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import datetime
import load_trades
from collections import defaultdict
from py_vollib.black_scholes_merton.implied_volatility import implied_volatility as iv
from py_vollib.black_scholes_merton.greeks.analytical import delta
from py_vollib.black_scholes_merton.greeks.analytical import theta
from py_vollib.black_scholes_merton.greeks.analytical import gamma
from py_vollib.black_scholes_merton.greeks.analytical import vega
from py_lets_be_rational.exceptions import BelowIntrinsicException, AboveMaximumException

class TransactionCandidate:

    """Create a new TradeCandidate object and populate Greeks and IV."""
    def __init__(self, backtest_data_db_tuple):

        self.RISK_FREE_RATE       = .011
        self.underlying_symbol    = backtest_data_db_tuple[0]
        self.underlying_price     = float(backtest_data_db_tuple[1].replace('$', '').replace(',', ''))
        self.exchange             = backtest_data_db_tuple[2]
        self.option_root          = backtest_data_db_tuple[3]
        self.option_ext           = backtest_data_db_tuple[4]
        self.option_type          = backtest_data_db_tuple[5]
        self.expiration           = backtest_data_db_tuple[6]
        self.data_date            = backtest_data_db_tuple[7]
        self.strike               = float(
            backtest_data_db_tuple[8].replace('$', '').replace(',', ''))
        self.last                 = float(
            backtest_data_db_tuple[9].replace('$', '').replace(',', ''))
        self.bid                  = float(
            backtest_data_db_tuple[10].replace('$', '').replace(',', ''))
        self.ask                  = float(
            backtest_data_db_tuple[11].replace('$', '').replace(',', ''))
        self.volume               = backtest_data_db_tuple[12]
        self.open_interest        = backtest_data_db_tuple[13]
        self.t1_open_interest     = backtest_data_db_tuple[14]
        self.mid                  = None
        self.rel_value            = None
        self.rel_strike           = None
        self.bid_ask_spread       = None
        self.iv                   = backtest_data_db_tuple[15]
        self.delta                = backtest_data_db_tuple[16]
        self.gamma                = backtest_data_db_tuple[17]
        self.theta                = backtest_data_db_tuple[18]
        self.vega                 = backtest_data_db_tuple[19]

    """Return the mid between the bid/ask in the option_data."""
    def calculate_mid(self):
        self.mid = round((self.bid + self.ask)/2, 2)

    """Returns the years to expiration (including fractional years)."""
    def get_years_to_expiration(self, data_date, expiration):
        days_to_expiration = self.get_days_to_expiration(data_date, expiration)
        years_to_expiration = round(float(days_to_expiration) / 365, 3)
        years_to_expiration = max(years_to_expiration, .001) # Avoid division by zero.
        return years_to_expiration
        
    """Returns the days to expiration."""
    def get_days_to_expiration(self, data_date, expiration):
        return (expiration - data_date).days

    """Wrapper for vollib's IV calculation.
       Returns IV to 4 decimal places.
       The option_type flag must be either 'p'
       or 'c'."""
    def get_implied_volatility(self,
                               mid,
                               underlying_price,
                               strike,
                               data_date,
                               expiration,                               
                               risk_free_rate,
                               option_type_flag,
                               dividend_rate=0.0):

        years_to_expiration = self.get_years_to_expiration(data_date, expiration)

        try:
            raw_iv = iv(mid,
                        underlying_price,
                        strike,
                        years_to_expiration,
                        risk_free_rate,
                        dividend_rate,
                        option_type_flag)
        except BelowIntrinsicException as e:
            raw_iv = .0001
        except AboveMaximumException as e:
            raw_iv = 10000

        # Sanity check for IV.
        if raw_iv > 1000 or raw_iv < 0:
            return 0.0
        return round(raw_iv, 4)

    """Wrapper for vollib function. Returns delta to 4 decimal places. 
       The option_type_flag must be 'c' or 'p'."""
    def get_delta(self,
                  option_type_flag,
                  underlying_price,
                  strike,
                  data_date,
                  expiration,
                  risk_free_rate,
                  implied_volatility,
                  dividend_rate=0):

        raw_delta = delta(option_type_flag,
                          underlying_price,
                          strike,
                          self.get_years_to_expiration(data_date, expiration),
                          risk_free_rate,
                          implied_volatility,
                          dividend_rate)
        
        return round(raw_delta, 4)

    """Wrapper for vollib. Returns theta to 4 decimal places."""
    def get_theta(self,
                  option_type_flag,
                  underlying_price,
                  strike,
                  data_date,
                  expiration,
                  risk_free_rate,
                  implied_volatility,
                  dividend_rate=0):

        raw_theta = theta(option_type_flag,
                          underlying_price,
                          strike,
                          self.get_years_to_expiration(data_date, expiration),
                          risk_free_rate,
                          implied_volatility,
                          dividend_rate)
        return round(raw_theta, 4)

    """Wrapper for vollib. Returns gamma to 4 decimal places."""
    def get_gamma(self,
                  option_type_flag,
                  undelying_price,
                  strike,
                  data_date,
                  expiration,
                  risk_free_rate,
                  implied_volatility,
                  dividend_rate=0):

        raw_gamma = gamma(option_type_flag,
                          undelying_price,
                          strike,
                          self.get_years_to_expiration(data_date, expiration),
                          risk_free_rate,
                          implied_volatility,
                          dividend_rate)
        return round(raw_gamma, 4)

    """Wrapper for vollib. Returns vega to 4 decimal places."""
    def get_vega(self,
                 option_type_flag,
                 underlying_price,
                 strike,
                 data_date,
                 expiration,
                 risk_free_rate,
                 implied_volatility,
                 dividend_rate=0):

        raw_vega = vega(option_type_flag,
                        underlying_price,
                        strike,
                        self.get_years_to_expiration(data_date, expiration),
                        risk_free_rate,
                        implied_volatility,
                        dividend_rate)
        return round(raw_vega, 4)

    """Fill in the relative value and relative strike."""
    def calculate_derived_values(self, calculate_greeks=True):

        # Pricing stuff.
        if self.mid == None:
            self.calculate_mid()
        self.rel_value = round(self.mid/self.underlying_price, 4)
        self.rel_strike = round(self.strike/self.underlying_price, 4)
        self.bid_ask_spread = round((self.ask - self.bid)/max(self.mid, .001), 4)

        # If we don't need the Greeks, return.
        if not calculate_greeks:
            return

        # Decide whether we need to calculate and store the greeks.
        need_to_store_greeks = False
        if self.iv == None or \
           self.delta == None or \
           self.gamma == None or \
           self.theta == None or \
           self.vega == None:
            need_to_store_greeks = True
            
        # Calculate greeks, if necessary.
        option_type_flag = ""
        if self.option_type == 'call':
            option_type_flag = 'c'
        else:
            option_type_flag = 'p'

        # Vollib calculations.
        if self.iv == None:
            self.iv = self.get_implied_volatility(self.mid,
                                                  self.underlying_price,
                                                  self.strike,
                                                  self.data_date,
                                                  self.expiration,
                                                  self.RISK_FREE_RATE,
                                                  option_type_flag)
        if self.delta == None:
            self.delta              = self.get_delta(option_type_flag,
                                                     self.underlying_price,
                                                     self.strike,
                                                     self.data_date,
                                                     self.expiration,
                                                     self.RISK_FREE_RATE,
                                                     self.iv)
        if self.theta == None:
            self.theta              = self.get_theta(option_type_flag,
                                                     self.underlying_price,
                                                     self.strike,
                                                     self.data_date,
                                                     self.expiration,
                                                     self.RISK_FREE_RATE,
                                                     self.iv)
        if self.gamma == None:
            self.gamma              = self.get_gamma(option_type_flag,
                                                     self.underlying_price,
                                                     self.strike,
                                                     self.data_date,
                                                     self.expiration,
                                                     self.RISK_FREE_RATE,
                                                     self.iv)
        if self.vega == None:
            self.vega               = self.get_vega(option_type_flag,
                                                    self.underlying_price,
                                                    self.strike,
                                                    self.data_date,
                                                    self.expiration,
                                                    self.RISK_FREE_RATE,
                                                    self.iv)
        # Store for later use.
        if need_to_store_greeks:
            load_trades.store_greeks(self.data_date,
                                     self.option_root,
                                     self.underlying_symbol,
                                     self.iv,
                                     self.delta,
                                     self.gamma,
                                     self.theta,
                                     self.vega)

    """Convenience function to print the info for this transaction."""
    def print_stats(self):
        result = "\n"
        result += self.underlying_symbol + "\n"
        result += self.option_type
        result += "\nData Date: " + str(self.data_date)
        result += "\nExpiration: " + str(self.expiration)
        result += "\nUnderlying Price: " + str(self.underlying_price)
        result += "\nStrike: " + str(self.strike)
        result += "\nMid: " + str(self.mid)
        result += "\nBid-Ask Spread: " + str(self.bid_ask_spread)
        result += "\nVolume: " + str(self.volume)
        result += "\nOpen Interest: " + str(self.open_interest)
        result += "\nImplied Volatiliy: " + str(self.iv)
        result += "\nDelta: " + str(self.delta)
        return result
