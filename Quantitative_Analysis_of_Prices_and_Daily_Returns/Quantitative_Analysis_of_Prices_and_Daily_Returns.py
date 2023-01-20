#!/usr/bin/env python
# coding: utf-8

# <h1> Quantitative Analysis of Price & Daily Returns </h1>
# 
# <ul>
#     <li> Can returns be described with a normal distribution? </li>
#     <li> Is there directional bias in daily change? </li>
#     <li> Can price movement be described as a random walk? </li>
# </ul>

# <h3> 1. Setting up the environment </h3>

# In[109]:


import numpy as np
import pandas as pd
import pandas_datareader.data as web
import yfinance as fin
import datetime as dt
import quandl as qdl
import matplotlib.pyplot as plt
import os
from scipy import stats
from scipy.stats import norm
from matplotlib import rcParams as rcp
rcp['figure.figsize'] = 8, 6
import seaborn as sb
sb.set()


# <h3> 2. Download stock price data, store in dataframe </h3>

# In[92]:


start_date = dt.datetime(2012,5,18)
end_date = dt.datetime(2023,1,10)
symbols = ['NVDA', 'VWDRY', 'OLED', 'TSM', 'SONO', 'PAG', 'MDT', 'LLY', 'GLNCY', 'GVDNY', 'EMR', 'EBAY', 'CRWD', 'COO',
          'STZ', 'CMSQY', 'CTSH', 'CB', 'CF', 'BF.B', 'BK', 'ASML', 'AMGN', 'ALSN', 'EADSY', 'ADDYY', 'SPCE', 'LCID', 'BMBL', 'SNAP',
          'AAPL', 'TSLA', 'NFLX', 'META', 'MSFT', 'DIS', 'GPRO', 'SBUX', 'F', 'BABA', 'BAC', 'GE', 'AMZN']
fb = fin.Ticker("META")
fb_hist = fb.history(start = start_date, end = end_date)


# <h3> 3. Viewing Data </h3>

# In[93]:


fb_hist.head()


# <h3> 4. Store instantaneous rate of return in separate series </h3>

# In[173]:


fb_close = fb_hist['Close']
fb_ret = pd.DataFrame(round(np.log(fb_close).diff() * 100, 2))
fb_ret.dropna(inplace = True)
fb_ret.head()


# <h3> 5. Plot the series </h3>

# In[121]:


fb_ret.plot()


# <h3> 6. Describing function using descreptive statistics, default assumes we are dealing eith a sample Pandas also deals with missing vallues by omitting them </h3>

# In[122]:


fb_ret.describe()


# <h3> 7. An alternative table of descriptives from scipy stats </h3>

# In[136]:


n, minmax, mean, var, skew, kurt = stats.describe(fb_ret)
mini, maxi = minmax
std = np.sqrt(var)


# <ul>
#     <li> Looking just a the skewness we see a suggested tilt towards the left. </li>
# </ul>

# <h3> 8. For comparison we generate random numbers that follow normal distribution </h3>

# In[148]:


plt.hist(fb_ret, bins = 15);


# In[145]:


x = norm.rvs(mean, std, n)
plt.hist(x, bins = 20);


# <h2> Is price change normally distributed? </h2>

# <h3> 9. Testing Kurtosis </h3>
# <ul> 
#     <li> Null Hypothesis: Sample is drawn from a population where where the underlying kurtosis is that of a normally distributed variable </li>
#     <li> Alternate Hypothesis: Sample is not drawn from a population where where the underlying kurtosis is that of a normally distributed variable </li>
# </ul>

# In[175]:


x_test = stats.kurtosistest(x)
fb_ret1 = round(np.log(fb_close).diff() * 100, 2)
fb_ret1.dropna(inplace = True)
fb_test = stats.kurtosistest(fb_ret1)
print(f'{"      Test statistic":20}{"p-value": >15}')
print(f'{" "*5}{"-"* 30}')
print(f"x:{x_test[0]:>17.2f}{x_test[1]:16.4f}")
print(f"META: {fb_test[0]:13.2f}{fb_test[1]:16.4f}")


# <h3> 10. Plot histogram of Price changes with Normal Curve overlay </h3>

# In[176]:


plt.hist(fb_ret,bins = 25, edgecolor = 'w', density = True)
overlay = np.linspace(mini,maxi,100)
plt.plot(overlay, norm.pdf(overlay, mean, std))


# <h2> Is daily price change significantly different from zero? </h2>

# <h3> 11. Conduct simple hypothesis test </h3>

# In[183]:


stats.ttest_1samp(fb_ret1,0,alternative = 'two-sided')


# <ul>
#     <li> Null hypothesis can be rejected as the P-value is less than 0.5. </li>
# </ul>

# <i> As the sample is too large for the T-test we make the sample smaller and take a sample of one year. </i>

# In[185]:


stats.ttest_1samp(fb_ret1.sample(252),0,alternative = 'two-sided')


# <h2> Can price movement be described as a random walk? </h2>

# <h3> 12. Creating price lags </h3>

# In[190]:


fb_close = pd.DataFrame(fb_close, columns = ['Close'])
fb_close['lag_1'] = fb_close.Close.shift(1)
fb_close['lag_2'] = fb_close.Close.shift(2)
fb_close.dropna(inplace = True)
fb_close.head()


# <h3> 13. Fit Linear Model </h3>

# In[198]:


lr = np.linalg.lstsq(fb_close[['lag_1', 'lag_2']], fb_close['Close'], rcond = None)[0]
lr


# In[199]:


fb_close['Predict'] = np.dot(fb_close[['lag_1', 'lag_2']], lr)
fb_close.head()


# <h3> 14. Visualizing the Close Price and Predicted Price </h3>

# In[200]:


fb_close[['Close', 'Predict']].plot()


# In[201]:


fb_close.iloc[-252:][['Close', 'Predict']].plot()

