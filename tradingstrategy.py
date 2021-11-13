import pandas as pd
import numpy as np
import mplfinance as mpf

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

    def additional_plot_element(self, df):
        return None

    def __name__(self):
        return "TradingStrategy"



class SimpleMovingAverage(TradingStrategy):
    
    def __init__(self, window =9, value = "Close"):
        super().__init__()
        # validation
        if not isinstance(window, int) or window < 0:
            raise ValueError("Moving Average Window must be int more than 0")
        if not isinstance(value, str) or value not in ["Open", "High", "Low","Close"]:
            raise ValueError("Moving averager price should be Open, High, Low, or Close")

        self.__window = window
        self.__value = value

    @property
    def window(self):
        return self.__window

    @property
    def value(self):
        return self.__value

    @window.setter
    def window(self, new_window):
        if not isinstance(new_window, int):
            if new_window < 0:
                raise ValueError("Moving Average Window must be int more than 0")
        self.__window = new_window

    @value.setter
    def value(self, new_value):
        if not isinstance(new_value, str) or new_value not in ["Open", "High", "Low","Close"]:
            raise ValueError("Moving averager price should be Open, High, Low, or Close")
        self.__value = new_value

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
            signal_price = df[-size:-1].rolling(self.window).mean()[self.__value].iloc[-1]
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
            signal_price = df[-size:-1].rolling(self.window).mean()[self.__value].iloc[-1]
            # check if current price below signal_price
            signal = True if df["Low"].iloc[-1] < signal_price else False
            signal_date = df["Date"].iloc[-1]
            return (signal, signal_price, signal_date)

    def additional_plot_element(self, df):
        addplot = df.sort_index().rolling(self.window).mean()[self.__value]
        return [mpf.make_addplot(addplot, type="line", width=1)]


    def __repr__(self):
        return f"{self.__class__.__name__}({self.window})"
    