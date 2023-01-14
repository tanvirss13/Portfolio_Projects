BlackScholesMerton Model
Black Scholes Model considering the interest rates. Also, calculates the greeks for calls and puts.

General Assumptions : 
1) The stock pays no dividends during the option's life
    Most companies pay dividends to their share holders, so this might seem a serious limitation to the model considering the observation that higher dividend yields elicit lower call premiums. A common way of adjusting the model for this situation is to subtract the discounted value of a future dividend from the stock price.
2) European exercise terms are used
    European exercise terms dictate that the option can only be exercised on the expiration date. 
    American exercise term allow the option to be exercised at any time during the life of the option, making american options more valuable due to their greater flexibility. 
    This limitation is not a major concern because very few calls are ever exercised before the last few days of their life. This is true because when you exercise a call early, you forfeit the remaining time value on the call and collect the intrinsic value. 
    Towards the end of the life of a call, the remaining time value is very small, but the intrinsic value is the same.
3) Markets are efficient
    This assumption suggests that people cannot consistently predict the direction of the market or an individual stock. The market operates continuously with share prices following a continuous Itô process. To understand what a continuous Itô process is, you must first know that a Markov process is "one where the observation in time period t depends only on the preceding observation."
    An Itô process is simply a Markov process in continuous time.
    If you were to draw a continuous process you would do so without picking the pen up from the piece of paper.
4) No commissions are charged
    Usually market participants do have to pay a commission to buy or sell options. Even floor traders pay some kind of fee, but it is usually very small. The fees that Individual investor's pay is more substantial and can often distort the output of the model.
5) Interest rates remain constant and known
    The Black and Scholes model uses the risk-free rate to represent this constant and known rate. In reality there is no such thing as the risk-free rate, but the discount rate on U.S. Government Treasury Bills with 30 days left until maturity is usually used to represent it.
    During periods of rapidly changing interest rates, these 30 day rates are often subject to change, thereby violating one of the assumptions of the model.
6) Returns are lognormally distributed
    This assumption suggests, returns on the underlying stock are normally distributed, which is reasonable for most assets that offer options.



![image](https://user-images.githubusercontent.com/79608956/182674828-f1ae4347-3f7b-414e-83a3-7887e0b9db74.png)



The Black and Scholes Option Pricing Model didn't appear overnight, in fact, Fisher Black started out working to create a valuation model for stock warrants.
This work involved calculating a derivative to measure how the discount rate of a warrant varies with time and stock price.
The result of this calculation held a striking resemblance to a well-known heat transfer equation. Soon after this discovery, Myron Scholes joined Black and the result of their work is a startlingly accurate option pricing model.
Black and Scholes can't take all credit for their work, in fact their model is actually an improved version of a previous model developed by A. 
James Boness in his Ph.D. dissertation at the University of Chicago. Black and Scholes' improvements on the Boness model come in the form of a proof that the risk-free interest rate is the correct discount factor, and with the absence of assumptions regarding investor's risk preferences.
