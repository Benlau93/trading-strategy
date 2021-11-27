import pandas as pd
import numpy as np


def moving_average(price: pd.DataFrame, window:int, value="Close", type="simple"):
    # validation
    if not isinstance(window, int):
        raise Exception("Window must be integer")
    if value not in price.columns:
        raise Exception("Value cannot be found in dataframe")
    if type not in ["simple","weighted","exponential"]:
        raise Exception("Type should be one of simple,weighted,exponential")


    if type == "exponential":
        sma = price[value].rolling(window).mean()
        ema = price[value].copy()
        ema.iloc[0:window] = sma[0:window]
        ma = ema.ewm(span = window, adjust=False).mean()
    else:
        if type == "simple":
            weights = np.ones(window)
        elif type =="weighted":
            weights = np.arange(1, window+1)
        ma = price[value].rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

    return ma


def cross_over(ma1, ma2):
    pass

def cross_under(ma1, ma2):
    pass