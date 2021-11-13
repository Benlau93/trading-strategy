import pandas as pd
import numpy as np


class TradingStrategy:

    def __init__(self):
        pass

    def buy(self, df):
        '''
        Identify buy signal and the buying price
        Return Tuple of (bool, float)
        baseline: buy at closing price
        '''
        signal_df = df.sort_values(["Date"]).tail(1)
        return (True, signal_df["Close"].iloc[0], signal_df["Date"].iloc[0])
        

    
    def sell(self, df):
        '''
        Identify sell signal and the selling price
        Return Tuple of (bool, float)
        baseline strategy: sell at closing price
        '''
        signal_df = df.sort_values(["Date"]).tail(1)

        return (True, signal_df["Close"].iloc[0], signal_df["Date"].iloc[0])

    def __repr__(self):
        return f"{self.__class__.__name__}"

    def __name__(self):
        return "TradingStrategy"



class SimpleMovingAverage(TradingStrategy):
    
    def __init__(self, window =9):
        super().__init__()
        self.window = window

    def buy(self, df):
        '''
        Identify buy signal and the buying price
        Return Tuple of (bool, float)
        baseline strategy -> Buy when above 9 SMA
        '''
        # check if dataframe is big enough to construct 9 SMA
        size = self.window + 1
        if len(df) < size:
            return (False, 0)

        else:
            df = df.sort_values(["Date"])
            signal_price = df[-size:-1].rolling(self.window).mean()["Close"].iloc[-1]
            # check if current price exceed signal_price
            signal = True if df["High"].iloc[-1] > signal_price else False
            signal_date = df["Date"].iloc[-1]
            return (signal, signal_price, signal_date)
        

    
    def sell(self, df):
        '''
        Identify sell signal and the selling price
        Return Tuple of (bool, float)
        baseline strategy -> sell when below 9 SMA
        '''
        size = self.window + 1
        if len(df) < size:
            return (False, 0)

        else:
            df = df.sort_values(["Date"])
            signal_price = df[-size:-1].rolling(self.window).mean()["Close"].iloc[-1]
            # check if current price below signal_price
            signal = True if df["Low"].iloc[-1] < signal_price else False
            signal_date = df["Date"].iloc[-1]
            return (signal, signal_price, signal_date)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.window})"
    