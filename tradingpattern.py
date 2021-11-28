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
        ma = ema.ewm(span = window, adjust=False).mean().values
    else:
        if type == "simple":
            weights = np.ones(window)
        elif type =="weighted":
            weights = np.arange(1, window+1)
        ma = price[value].rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True).values

    return ma


def cross_over(ma1, ma2):
    crossover = np.where(ma1 > ma2, 1,0)
    crossover = np.diff(crossover)
    crossover = np.append(np.array([0]) , crossover)
    crossover = np.where(crossover == 1, 1,0)
    return crossover

def cross_under(ma1, ma2):
    crossunder = np.where(ma1 > ma2, 1,0)
    crossunder = np.diff(crossunder)
    crossunder = np.append(np.array([0]) , crossunder)
    crossunder = np.where(crossunder == -1, 1,0)
    return crossunder