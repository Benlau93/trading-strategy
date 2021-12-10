import pandas as pd
import numpy as np
import mplfinance as mpf
import tradingpattern as tp
import pandas_ta as ta

class TradingStrategy:

    def __init__(self):
        pass

    def generate_signal(self, df):
        buy_signal = df["Close"].values
        sell_signal = df["Close"].values
        return (buy_signal, sell_signal)


    def __repr__(self):
        return f"{self.__class__.__name__}"

    def additional_plot_element(self, df, start_date, end_date):
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
    

class CrossOverStrategy(TradingStrategy):
    def __init__(self, ma1 = {"type":"simple", "window":9, "value":"Close"}, ma2 = {"type":"simple", "window":20, "value":"Close"}):
        # validation
        required_col = ["type","window","value"]
        if sorted(required_col) != sorted(list(ma1.keys())) or sorted(required_col) != sorted(list(ma2.keys())):
            raise Exception("Only allowable keys for moving average are type,window,value")

        self.ma1 = ma1
        self.ma2 = ma2

    def generate_signal(self, df):
        '''
        Buy when ma1 crossover ma2,
        Sell when ma1 crossunder ma2
        '''
        df["MA1"] = tp.moving_average(df, self.ma1["window"], self.ma1["value"], self.ma1["type"])
        df["MA2"] = tp.moving_average(df, self.ma2["window"], self.ma2["value"], self.ma2["type"])
        df["CROSSOVER"] = tp.cross_over(df["MA1"].values, df["MA2"].values)
        buy_signal = df.apply(lambda row: row["MA1"] if row["CROSSOVER"]==1 else np.nan, axis=1)
        df["CROSSUNDER"] = tp.cross_under(df["MA1"].values, df["MA2"].values)
        sell_signal = df.apply(lambda row: row["MA1"] if row["CROSSUNDER"]==1 else np.nan, axis=1)

        return (buy_signal, sell_signal)

    def additional_plot_element(self, df, start_date, end_date):
        df["MA1"] = tp.moving_average(df, self.ma1["window"], self.ma1["value"], self.ma1["type"])
        df["MA2"] = tp.moving_average(df, self.ma2["window"], self.ma2["value"], self.ma2["type"])
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
        addplot1 , addplot2 = df["MA1"], df["MA2"]
        
        return [mpf.make_addplot(addplot1, type="line", width=1), mpf.make_addplot(addplot2, type="line", width=1)]

    def __repr(self):
        return f"{self.__class__.__name__})"



class RelativeStrengthIndex(TradingStrategy):

    def __init__ (self, strength = (30,70)):
        # validation
        buy_str, sell_str = strength[0], strength[1]
        if not isinstance(buy_str, int) or buy_str <0 or buy_str >100:
            raise Exception("RSI can only be int from 0 to 100")
        if not isinstance(sell_str, int) or buy_str <0 or buy_str >100:
            raise Exception("RSI can only be int from 0 to 100")

        self.buy_str = buy_str
        self.sell_str = sell_str
    

    def generate_signal(self, df):
        df["RSI"] = df.ta.rsi()
        df["BEFORE_RSI"] = df["RSI"].shift(1)
        buy_signal = df.apply(lambda row: row["Close"] if row["RSI"] >= self.buy_str and row["BEFORE_RSI"] < self.buy_str else np.nan, axis=1)
        sell_signal = df.apply(lambda row: row["Close"] if row["RSI"] >= self.sell_str and row["BEFORE_RSI"] < self.sell_str else np.nan, axis=1)

        return (buy_signal, sell_signal)

    
    def additional_plot_element(self, df, start_date, end_date):
        df["RSI"] = df.ta.rsi()
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()

        rsi_ylim = (0, 100)

        addplots = [
            mpf.make_addplot(df["RSI"], ylabel="RSI", width=1.5, color="black",panel=1, ylim=rsi_ylim),
            mpf.make_addplot(np.array([self.buy_str] * len(df)), color="green", width=1, panel=1, ylim=rsi_ylim),
            mpf.make_addplot(np.array([50] * len(df)), color="gray", width=0.8, panel=1, ylim=rsi_ylim),
            mpf.make_addplot(np.array([self.sell_str] * len(df)), color="red", width=1, panel=1, ylim=rsi_ylim)]

        return addplots
    