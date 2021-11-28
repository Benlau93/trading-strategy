import pandas as pd
import numpy as np
import mplfinance as mpf
import tradingpattern as tp

class TradingStrategy:

    def __init__(self):
        pass

    def generate_signal(self, df):
        buy_signal = df["Close"].values
        sell_signal = df["Close"].values
        return (buy_signal, sell_signal)


    def __repr__(self):
        return f"{self.__class__.__name__}"

    def additional_plot_element(self, df):
        return None

    def __name__(self):
        return "TradingStrategy"



class MovingAverage(TradingStrategy):
    
    def __init__(self, type = "simple", window =9, value = "Close" ):
        super().__init__()
        # validation
        if not isinstance(window, int) or window < 0:
            raise ValueError("Moving Average Window must be int more than 0")
        if not isinstance(value, str) or value not in ["Open", "High", "Low","Close"]:
            raise ValueError("Moving average value should be Open, High, Low, or Close")
        if not isinstance(type, str) or type not in ["simple","weighted","exponential"]:
            raise ValueError("Moving Average type should be one of simple,weighted,exponential")

        self.__window = window
        self.__value = value
        self.type = type

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

    def generate_signal(self, df):
        '''
        Identify buy and sell signals and the respective price
        Return Tuple of (bool, float)
        baseline strategy -> Buy when above SMA, Sell when below SMA
        '''
        df["SMA"] = tp.moving_average(df, self.window, value = self.value, type = self.type)
        buy_signal = df.apply(lambda row: row["Close"] if row["Close"] > row["SMA"] else np.nan, axis=1).values
        sell_signal = df.apply(lambda row: row["Close"] if row["Close"] < row["SMA"] else np.nan, axis=1).values
        return (buy_signal, sell_signal)

    def additional_plot_element(self, df, start_date, end_date):
        df["ADDPLOT"] = tp.moving_average(df, self.window, value = self.value, type = self.type)
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
        addplot = df["ADDPLOT"]

        return [mpf.make_addplot(addplot, type="line", width=1)]


    def __repr__(self):
        return f"{self.__class__.__name__}({self.window})"
    