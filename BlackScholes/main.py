

from math import log, sqrt, pi, exp
from stats import norm
from datetime import datetime, date
import numpy as np
import pandas as pd
from pandas import DataFrame

def d1(S,K,T,r,sig):
    return (log(S/K)+((r+sig**2/2.)*T))/(sig*sqrt(T))
def d2(S,K,T,r,sig):
    return d1(S,K,T,r,sig)-sig*sqrt(T)

def bs_call(S, K, T, r, sig):
    return S * norm.cdf(d1(S, K, T, r, sig)) - K * exp(-r * T) * norm.cdf(d2(S, K, T, r, sig))

def bs_put(S, K, T, r, sig):
    return K * exp(-r * T) - S * bs_call(S, K, T, r, sig)

#### Implied Volatility
def call_implied_volatility(Price, S, K, T, r):
    sig = 0.001
    while sig < 1:
        Price_implied = S * \
            norm.cdf(d1(S, K, T, r, sig))-K*exp(-r*T) * \
            norm.cdf(d2(S, K, T, r, sig))
        if Price-(Price_implied) < 0.001:
            return sig
        sig += 0.001
    return "Not Found"

def put_implied_volatility(Price, S, K, T, r):
    sig = 0.001
    while sig < 1:
        Price_implied = K*exp(-r*T)-S+bs_call(S, K, T, r, sig)
        if Price-(Price_implied) < 0.001:
            return sig
        sigma += 0.001
    return "Not Found"

print("Implied Volatility: " +
      str(100 * call_implied_volatility(bs_call(lcp, strike_price, t, uty, sig,), lcp, strike_price, t, uty,)) + " %")

####CALL greeks
def call_delta(S, K, T, r, sig):
    return norm.cdf(d1(S, K, T, r, sig))

def call_gamma(S, K, T, r, sig):
    return norm.pdf(d1(S, K, T, r, sig)) / (S * sig * sqrt(T))


def call_vega(S, K, T, r, sig):
    return 0.01 * (S * norm.pdf(d1(S, K, T, r, sigma)) * sqrt(T))


def call_theta(S, K, T, r, sig):
    return 0.01 * (-(S * norm.pdf(d1(S, K, T, r, sig)) * sig) / (2 * sqrt(T)) - r * K * exp(-r * T) * norm.cdf(
        d2(S, K, T, r, sig)))


def call_rho(S, K, T, r, sig):
    return 0.01 * (K * T * exp(-r * T) * norm.cdf(d2(S, K, T, r, sig)))

####PUT greeks
def put_delta(S, K, T, r, sig):
    return -norm.cdf(-d1(S, K, T, r, sig))


def put_gamma(S, K, T, r, sig):
    return norm.pdf(d1(S, K, T, r, sigma)) / (S * sig * sqrt(T))


def put_vega(S, K, T, r, sig):
    return 0.01 * (S * norm.pdf(d1(S, K, T, r, sig)) * sqrt(T))


def put_theta(S, K, T, r, sig):
    return 0.01 * (-(S * norm.pdf(d1(S, K, T, r, sigma)) * sigma) / (2 * sqrt(T)) + r * K * exp(-r * T) * norm.cdf(
        -d2(S, K, T, r, sig)))


def put_rho(S, K, T, r, sig):
    return 0.01 * (-K * T * exp(-r * T) * norm.cdf(-d2(S, K, T, r, sig)))
