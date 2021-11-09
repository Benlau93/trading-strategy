import pandas as pd
import numpy as np


class TradingStrategy:
    position_size = 0.3

    def __init__(self, chart="OHLC"):
        if chart not in ["OHLC","line"]:
            raise ValueError("Only charts allowed are OHLC,line")

        # initiation
        self.__chart = chart

    @property
    def chart(self):
        return self.__chart


    def buy(self, df):
        '''
        Identify buy signal and the buying price
        Return Tuple of (bool, float)
        baseline strategy -> Buy when above 9 SMA
        '''
        # check if dataframe is big enough to construct 9 SMA
        if len(df) < 10:
            return (False, 0)

        else:
            df = df.sort_values(["Date"])
            signal_price = df[-10:-1].rolling(9).mean()["Close"].iloc[-1]
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
        if len(df) < 10:
            return (False, 0)

        else:
            df = df.sort_values(["Date"])
            signal_price = df[-10:-1].rolling(9).mean()["Close"].iloc[-1]
            # check if current price below signal_price
            signal = True if df["Low"].iloc[-1] < signal_price else False
            signal_date = df["Date"].iloc[-1]
            return (signal, signal_price, signal_date)

    def position_sizing(self):
        '''
        positioning. to determine the position size of each buy
        '''
        return self.position_size

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.__chart}')"

    def __name__(self):
        return "TradingStrategy"

