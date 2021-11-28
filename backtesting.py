import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from tradingstrategy import TradingStrategy
import yfinance as yf
from datetime import date
from datetime import datetime
from dateutil import parser
import xlsxwriter
import os
import re


class BackTesting:
    def __init__(self, strategy: TradingStrategy):
        # validation
        try:
            strategy_name = strategy.__name__()
        except AttributeError:
            strategy_name = None
        finally:
            if strategy_name !="TradingStrategy":
                raise ValueError("Only class of TradingStrategy is accepted for backtesting")

        # initiation
        self.__strategy = strategy
        self.__transaction = pd.DataFrame()
        self.historical = {}
        self.buyandhold = pd.DataFrame()

    @property
    def transaction(self):
        if len(self.__transaction) < 1:
            raise Exception("There is no transaction yet. Run backtesting first")
        else:
            return self.__transaction.drop("UNIQUE", axis=1)

    @property
    def strategy(self):
        return self.__strategy

    @strategy.setter
    def strategy(self, tradingStrategy):
        # validation
        try:
            strategy_name = tradingStrategy.__name__()
        except AttributeError:
            strategy_name = None
        finally:
            if strategy_name !="TradingStrategy":
                raise ValueError("Only class of TradingStrategy is accepted for backtesting")

        self.__strategy = tradingStrategy

    def backtesting(self, ticker :str, start_date: str, end_date: str, timeframe = "1d", buy_and_hold = False, verbose = True):
        # validation
        if timeframe not in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]:
            raise ValueError("Only timeframe allowed are 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo")
        # validate date
        try:
            start_date = parser.parse(start_date)
            end_date = parser.parse(end_date)
        except:
            raise ValueError("Start or End date is not a valid date format")

        # get ticker
        if ticker.endswith(".txt"):
            # read from text file
            with open(ticker,"r") as f:
                ticker = f.read()
        else:
            ticker = ticker.upper()

        # get unique identifier of current backtesting
        self.__unique = self.strategy.__repr__() + "|" + ticker + "|" + str(start_date) + " to " + str(end_date) + "|" + timeframe

        # download historical price
        if self.historical.get(self.__unique):
            df = self.historical[self.__unique]
        else:
            df = self.download_price(ticker ,timeframe)
            # save latest downloaded price
            if "Adj Close" in df.columns:
                df["Close"] = df["Adj Close"]
                df = df.drop("Adj Close", axis=1)
            self.historical[self.__unique] = df

        df = df.sort_values("Date").dropna()

        # get signal based on trading strategy and append to transaction
        self.__get_trading_signal(ticker, df, start_date, end_date, verbose)
        # generate buy and hold return
        df_filtered = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
        bnh = self.buy_and_hold(df_filtered)
        max_paper_loss = ((bnh[0] - df_filtered["Close"].min()) / bnh[0]) if df_filtered["Close"].min() < bnh[0] else 0
        bnh_series = pd.Series({"UNIQUE":self.__unique,
                        "Buy and Hold P/L (%)": bnh[2],
                        "Buy and Hold Max Loss (%)":-max_paper_loss})
        # append buy and hold
        self.__append_buyandhold(bnh_series)

        # generate result
        if buy_and_hold:
            buy_and_hold = bnh
        result = self.__generate_result(ticker, buy_and_hold)
        result = result[result["UNIQUE"]==self.__unique].drop("UNIQUE", axis=1).reset_index(drop=True)
        return result


    def __generate_result(self, ticker, buy_and_hold):
        print()
        print(f"----- {ticker} Result -----")
        if len(self.__transaction) < 1:
            print("No transaction based on current trading strategy.")
        else:
            closed = self.get_closed_position()
            closed = closed[closed["UNIQUE"]==self.__unique].copy()
            pl_per = closed["P/L (%)"].sum()
            pl_per = round(pl_per * 100,2)
            print(f"{self.strategy.__repr__()}: Total Profit of {pl_per}% with {len(closed)} closed position(s)")

        if buy_and_hold:
            bnl_pl = round(buy_and_hold[2] * 100,2)
            print(f"Buy and Hold: Total Profit of {bnl_pl}%")
            better_strategy = self.strategy.__repr__() if pl_per > bnl_pl else "Buy and Hold"
            print(f"{better_strategy} is a better strategy")


        return closed


    def __get_trading_signal(self, ticker, df, start_date, end_date, verbose):
        # initaite trade
        trade = 1
        position = {}
        signals = self.strategy.generate_signal(df)
        df["BUY"], df["SELL"] = signals[0], signals[1]
        df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
        if verbose:
            print()
            print(f"----- {ticker} Transaction(s) -----")
        for row in df.iterrows():
            row = row[1]
            if position:
                if pd.notnull(row["SELL"]):
                    closed_dict = {"SellDate":row["Date"],
                                    "SellPrice":row["SELL"]}
                    position.update(closed_dict)
                    # verbose
                    if verbose:
                        print(f"Sold {ticker} at ${round(position['SellPrice'],2)} on {str(position['SellDate'])[:10]}")
                        
                    
                    # update trade
                    trade += 1
                    # record transaction
                    self.__append_transaction(position)
                    # remove position
                    position = {}

            else:
                if pd.notnull(row["BUY"]):
                    position = {"UNIQUE":self.__unique,
                                "BuyPrice":row["BUY"],
                                "BuyDate":row["Date"],
                                "Trade":trade}
                    # record transactions
                    self.__append_transaction(position)

                    # verbose
                    if verbose:
                        print(f"Bought {ticker} at ${round(position['BuyPrice'],2)} on {str(position['BuyDate'])[:10]}")
        
        if position:
            final_price = df.tail(1)
            closed_dict = {"SellDate":final_price["Date"].iloc[0],
                            "SellPrice":final_price["Close"].iloc[0]}
            position.update(closed_dict)
            # update trade
            trade += 1
            # record transaction
            self.__append_transaction(position)

    def plot(self):
        # validate
        if len(self.__transaction) < 1:
            raise Exception("There is no transaction yet. Run backtesting first before plotting")
        # get buying and selling price
        df_plot = self.historical[self.__unique]
        start_date, end_date = self.__unique.split("|")[2].split(" to ")
        df_plot = df_plot[(df_plot["Date"] >= pd.to_datetime(start_date)) & (df_plot["Date"] <= pd.to_datetime(end_date))].set_index("Date")

        signal_df = self.__transaction[self.__transaction["UNIQUE"]==self.__unique][["Date","Action","Price"]].set_index("Date")
        buy_plot = signal_df[signal_df["Action"]=="Buy"][["Price"]].copy()
        buy_plot = pd.merge(df_plot, buy_plot, left_index=True, right_index=True, how="left")[["Price"]]
        sell_plot = signal_df[signal_df["Action"]=="Sell"][["Price"]].copy()
        sell_plot = pd.merge(df_plot, sell_plot, left_index=True, right_index=True, how="left")[["Price"]]
        
        # add buy and sell marker
        buy_plot = mpf.make_addplot(buy_plot,type='scatter',markersize=100,marker=6)
        sell_plot = mpf.make_addplot(sell_plot,type='scatter',markersize=100,marker=7)
        add_plot = [buy_plot, sell_plot]

        # add any additional plot for the specific tradingstrategy
        additional_plot = self.strategy.additional_plot_element(self.historical[self.__unique], start_date, end_date)
        if additional_plot:
            add_plot.extend(additional_plot)
        
        # plot chart
        mpf.plot(df_plot, type="candle", style ="yahoo", addplot = add_plot, title = self.__unique, figscale = 2)
        plt.show()


    @staticmethod
    def download_price(ticker ,timeframe, start_date=date(2015,1,1), end_date=date.today()):
        # download historical price using yfinance
        historical = yf.download(ticker, start=start_date, end=end_date, interval=timeframe, auto_adjust=True, progress = False)

        if len(historical) <1:
            raise Exception(f"No historical data found for {ticker}")

        return historical.reset_index().dropna()
    

    @staticmethod
    def buy_and_hold(df):
        buy_price = df.head(1)["Close"].iloc[0]
        cur_price = df.tail(1)["Close"].iloc[0]
        pl = round(cur_price - buy_price, 2)
        pl_per = (cur_price - buy_price)/ buy_price
        return (buy_price, pl, pl_per)

    def __append_buyandhold(self, bnh_series):
        self.buyandhold = self.buyandhold.append(bnh_series, sort=True, ignore_index=True)
        self.buyandhold = self.buyandhold.drop_duplicates(subset=["UNIQUE"])


    def __append_transaction(self, position):
        # append transaction
        position = pd.Series(position)
        if "SellPrice" in position.index:
            position = position.drop([idx for idx in position.index if idx.startswith("Buy")])
        position["Action"] = "Sell" if "SellPrice" in position.index else "Buy"
        position = position.rename({"SellPrice":"Price",
                                        "BuyPrice":"Price",
                                        "BuyDate":"Date",
                                        "SellDate":"Date"})
        unique_list =  position["UNIQUE"].split("|")
        uni_col = ["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL"]
        for i in range(len(uni_col)):
            position[uni_col[i]] = unique_list[i]
        self.__transaction = self.__transaction.append(position, sort=True, ignore_index=True)
        self.__transaction = self.__transaction.drop_duplicates(subset=["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL","Date","Action"])


    def get_closed_position(self):
        # validate
        if len(self.__transaction) < 1:
            raise Exception("There is no transaction yet. Run backtesting first")
        self.__transaction["Date"] = pd.to_datetime(self.__transaction["Date"], format="%Y-%m-%d")
        buy_df = self.__transaction[self.__transaction["Action"]=="Buy"].rename({"Price":"BuyPrice",
                                                                    "Date":"BuyDate"}, axis=1).drop("Action", axis=1)
        sell_df = self.__transaction[self.__transaction["Action"]=="Sell"].rename({"Price":"SellPrice",
                                                                            "Date":"SellDate"}, axis=1).drop("Action", axis=1)

        closed = pd.merge(buy_df, sell_df, on=["UNIQUE","TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL","Trade"])
        closed["P/L"] = closed["SellPrice"] - closed["BuyPrice"]
        closed["P/L (%)"] = (closed["SellPrice"] - closed["BuyPrice"]) / closed["BuyPrice"]
        return closed

    def get_performance(self):
        # validate
        if len(self.__transaction) < 1:
            raise Exception("There is no transaction yet. Run backtesting first")

        # pre-processing
        closed = self.get_closed_position()
        closed["PROFIT"] = closed["P/L"].map(lambda x: True if x>0 else False)
        closed["LOSS"] = closed["P/L"].map(lambda x: False if x>0 else True)

        def get_bar(row):
            timeframe = row["INTERVAL"]
            time_digit, time_str = re.search("[0-9]+",timeframe)[0], re.search("[a-z]+", timeframe)[0]
            bar_map = {"m":60,
                    "h":3600,
                    "d":86400,
                    "wk":604800,
                    "mo":2419200}
            bar = int(time_digit) * bar_map[time_str]
            return int((row["SellDate"] - row["BuyDate"]).total_seconds() // bar)
    
        closed["BAR"] = closed.apply(get_bar,axis=1)
        # engineer performance metrics that require additional processing
        closed_win = closed[closed["PROFIT"]][["UNIQUE","P/L (%)","BAR"]].groupby(["UNIQUE"]).agg(
            AvergeWinTrade = pd.NamedAgg(column="P/L (%)", aggfunc="mean"),
            AverageWinBar = pd.NamedAgg(column="BAR", aggfunc="mean")).reset_index()
        closed_lose = closed[closed["LOSS"]][["UNIQUE","P/L (%)","BAR"]].groupby(["UNIQUE"]).agg(
            AvergeLossTrade = pd.NamedAgg(column="P/L (%)", aggfunc="mean"),
            AverageLossBar = pd.NamedAgg(column="BAR", aggfunc="mean")).reset_index()
        # to handle if there is no winning or losing trade
        if len(closed_win) == 0:
            closed_merge = closed_lose
        elif len(closed_lose) ==0:
            closed_merge = closed_win
        else:
            closed_merge = pd.merge(closed_win, closed_lose, on="UNIQUE")
        closed_merge = pd.merge(closed_merge, self.buyandhold, on="UNIQUE")

        # get performance metrics
        performance = closed.groupby(["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL","UNIQUE"]).agg(
                            NetProfit = pd.NamedAgg(column="P/L (%)", aggfunc="sum"),
                            TotalTrade = pd.NamedAgg(column="Trade", aggfunc="max"),
                            NumWinningTrade = pd.NamedAgg(column = "PROFIT", aggfunc="sum"),
                            NumLosingTrade = pd.NamedAgg(column="LOSS", aggfunc="sum"),
                            PercentProfitable = pd.NamedAgg(column="PROFIT",aggfunc="mean"),
                            LargestWining = pd.NamedAgg(column="P/L (%)", aggfunc="max"),
                            LargestLosing = pd.NamedAgg(column="P/L (%)", aggfunc="min"),
                            AverageTrade = pd.NamedAgg(column="P/L (%)", aggfunc="mean"),
                            AverageNumBar = pd.NamedAgg(column="BAR", aggfunc="mean"),
                            HighestNumBar = pd.NamedAgg(column="BAR", aggfunc="max"),
                            LowestNumBar = pd.NamedAgg(column="BAR", aggfunc="min")).reset_index()

        # rename column
        performance = performance.rename({"NetProfit":"NetProfit (%)",
                                        "LargestWining":"LargestWining (%)",
                                        "LargestLosing":"LargestLosing (%)",
                                        "AverageTrade":"AverageTrade (%)"}, axis=1)

        performance = pd.merge(performance, closed_merge, on="UNIQUE").drop("UNIQUE", axis=1).set_index(["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL"])
        performance = performance.stack().reset_index().rename({"level_4":"Performance Metrics",0:"Value"}, axis=1)
        performance["Value"] = performance["Value"].map(lambda x: round(x, 4))

        return performance


    def export_result(self, filepath = os.getcwd()):
        if len(self.__transaction) < 1:
            raise Exception("There is no result to export")

        else:
            # get transaction
            transaction_write = self.__transaction.copy()
            transaction_write["Price"] = transaction_write["Price"].map(lambda x: round(x,2))
            transaction_write["Date"] = pd.to_datetime(transaction_write["Date"], format="%Y-%m-%d")
            transaction_write = transaction_write[["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL","Date","Action","Price"]].copy()

            closed = self.get_closed_position()
            # get closed position
            for col in ["BuyDate","SellDate"]:
                closed[col] = pd.to_datetime(closed[col], format="%Y-%m-%d")
            for col in ["BuyPrice","SellPrice","P/L"]:
                closed[col] = closed[col].map(lambda x: round(x,2))
            closed["P/L (%)"] = closed["P/L (%)"].map(lambda x: round(x,4))
            closed = closed[["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL","Trade","BuyDate","BuyPrice","SellDate","SellPrice","P/L","P/L (%)"]].copy()

            # get performance metrics
            performance = self.get_performance()
            performance = performance[["TRADINGSTRATEGY","TICKER","TIMEPERIOD","INTERVAL","Performance Metrics","Value"]]
            # write to excel
            timestamp = str(datetime.now())[:19].replace(":","")
            filename = os.path.join(filepath,f"backtesting result_{timestamp}.xlsx")
            workbook = xlsxwriter.Workbook(filename)
            workbook.close()
            with pd.ExcelWriter(filename, date_format="YYYY-MM-DD") as writer:
                transaction_write.to_excel(writer, sheet_name = "Transaction", index=False)
                closed.to_excel(writer, sheet_name="Closed Position", index=False)
                performance.to_excel(writer, sheet_name="Performance Metrics", index=False)

    def clear_history(self):
        self.__transaction = pd.DataFrame()
        self.buyandhold = pd.DataFrame()