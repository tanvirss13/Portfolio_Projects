import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from math import ceil, floor

#Define parameters
long_leg_rel_strike = 0.9
short_leg_rel_strike = 2
long_leg_days_to_exp = 30
short_leg_days_to_exp = 20
profit_take = 0.05
min_days_to_exp = 7
max_rel_sma_to_open = 1.2
initial_cash_value = 1000000
position_size = 0.01

#Define function to calculate SMA
def get_sma(data,window):
  return data.rollling(window=window).mean()

#Get VIX data
vix_data = yf.download("^VIX", start="2006-01-01", end="2023-03-28")
vix_data = vix_data.reset_index()
vix_data = vix_data.rename(columns={"Date": "date", "Adj Close": "vix_spot_price"})


#Calculate SMA
vix_data["vix_sma"] = get_sma(vix_data["vix_spot_price"], 60)


#Define function to categorize dates as in_sample or out_of_sample
def categorize_dates(data):
  in_sample_start_date = datetime(2006,1,1) + timedelta(days = np.random.randint(0,120))
  for i in range(len(data)):
    if data.loc[i, "date"] < in_sample_start_date:
      data.loc[i, "date_category"] = "out_of_sample"
    else:
      days_since_start = (data.loc[i, "date"] - in_sample_start_date).days
      nums_periods = days_since_start // 120
      if nums_periods%2==0:
        data.loc[i, "date_category"] = "in_sample"
      else:
        data.loc[i, "date_category"] = "out_of_sample"
  return data


#Categories data
vix_data = categorize_dates(vix_data)


#Define function to calculate relative strike price
def get_rel_strike_price(row, leg_type):
  if leg_type == "long":
    strike_price = row["vix_spot_price"]*long_leg_rel_strike
  else:
    strike_price = row["vix_spot_price"]*short_leg_rel_strike
  return round(strike_price)


#Define function to calculate days to expiration
def get_days_to_exp(row, leg_type):
  if leg_type == "long":
    days_to_exp = long_leg_days_to_exp
  else:
    days_to_exp = short_leg_days_to_exp
  exp_dates = pd.to_datetime(row["options_expiration_dates"])
  days_to_exp_list = [(d - row["date"]).days for d in exp_dates]
  days_to_exp_list = [d for d in days_to_exp_list if d>=0]
  if not days_to_exp_list:
    days_to_exp = 0
  else:
    days_to_exp = min(days_to_exp_list)
  if days_to_exp < min_days_to_exp:
    days_to_exp = 0
  return ceil(days_to_exp)


#Define function to open a new trade 
def open_trade(portfolio_value, vix_date):
  #Get relevant data
  curr_row = vix_data.iloc[0]
  long_strike_price = get_rel_strike_price(curr_row, "long")
  short_stike_price = get_rel_strike_price(curr_row, "short")
  long_days_to_exp = get_days_to_exp(curr_row, "long")
  short_days_to_exp
                                           



