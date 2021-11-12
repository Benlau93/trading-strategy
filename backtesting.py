import pandas as pd
import numpy as np
from tradingstrategy import TradingStrategy
import yfinance as yf
from datetime import date
from datetime import datetime
from dateutil import parser
import xlsxwriter
import os

class BackTesting:
    transaction = pd.DataFrame()

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

    @property
    def strategy(self):
        return self.__strategy


    def backtesting(self, ticker :str, start_date: str, end_date: str, timeframe = "1d" , capital = 10000, fees = 0, buy_and_hold = False, verbose = True):
        # validation
        if timeframe not in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]:
            raise ValueError("Only timeframe allowed are 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo")
        # validate date
        try:
            start_date = parser.parse(start_date).date()
            end_date = parser.parse(end_date).date()
        except:
            raise ValueError("Start or End date is not a valid date format")
        if capital < 0:
            raise ValueError("Capital cannot be less than 0")
        if fees < 0:
            raise ValueError("Fees cannot be less than 0")
        
        # get ticker
        if ticker.endswith(".txt"):
            # read from text file
            with open(ticker,"r") as f:
                ticker = f.read()
        else:
            ticker = ticker.upper()

        # initaite capital
        original_capital = capital

        # download historical price
        df = self.download_price(ticker ,timeframe, start_date, end_date)
        if self.strategy.chart == "line":
            df = df[["Close"]].copy()
        df = df.sort_index().dropna().reset_index()

        # get signal based on trading strategy and append to transaction
        self.__get_trading_signal(ticker, df, capital, fees, verbose)

        # generate result
        result = self.__generate_result(ticker, df, original_capital, buy_and_hold)

        return result


    def __generate_result(self, ticker, df, original_capital, buy_and_hold):
        print()
        print(f"----- {ticker} Result -----")
        if len(self.transaction) < 1:
            print("No transaction based on current trading strategy.")
        else:
            closed = self.get_closed_position()
            closed = closed[closed["TICKER"]==ticker].copy()
            pl = closed["P/L"].sum()
            pl = round(pl,2)
            pl_per = round(pl / original_capital * 100,2)
            print(f"Trading Strategy: Total Profit of ${pl} ({pl_per}%) with {len(closed)} closed position(s)")

            if buy_and_hold:
                bnh = self.buy_and_hold(df)
                bnh_pl = round(bnh[1] / 100 * original_capital,2)
                print(f"Buy and Hold: Total Profit of ${bnh_pl} ({bnh[1]}%)")
                better_strategy = self.strategy.__class__.__name__ if pl > bnh_pl else "Buy and Hold"
                print(f"{better_strategy} is a better strategy")
        return closed


    def __get_trading_signal(self, ticker, df, capital, fees, verbose):
        # initaite trade
        trade = 0
        position = {}
        print()
        print(f"----- {ticker} Transaction(s) -----")
        for i in range(1,len(df)+1):
            if position:
                sell_signal = self.strategy.sell(df.iloc[:i,:])
                if sell_signal[0]:
                    sell_value = (position["NumShares"] * sell_signal[1]) - fees
                    capital += sell_value
                    closed_dict = {"SellDate":sell_signal[2],
                                    "SellPrice":sell_signal[1],
                                    "SellValue":sell_value}
                    position.update(closed_dict)
                    # update trade
                    trade += 1
                    # record transaction
                    self.__append_transaction(position)
                    # remove position
                    position = {}
                    # verbose
                    if verbose:
                        print(f"Sold {num_shares} of {ticker} shares at ${round(sell_signal[1],2)} on {str(sell_signal[2])[:10]}")
            else:
                buy_signal = self.strategy.buy(df.iloc[:i,:])
                if buy_signal[0]:
                    num_shares = int((self.strategy.position_sizing() * capital) // buy_signal[1])
                    if num_shares <= 0: # invalid trade if capital not enough to purchase additional stocks
                        continue
                    buy_value = (num_shares * buy_signal[1]) + fees
                    capital -= buy_value
                    position = {"TICKER":ticker,
                                        "BuyPrice":buy_signal[1],
                                        "NumShares":num_shares,
                                        "BuyValue":buy_value,
                                        "BuyDate":buy_signal[2],
                                        "Trade":trade}
                    # record transactions
                    self.__append_transaction(position)

                    # verbose
                    if verbose:
                        print(f"Bought {num_shares} of {ticker} shares at ${round(buy_signal[1],2)} on {str(buy_signal[2])[:10]}")
        
        if position:
            final_price = df.sort_values(["Date"]).tail(1)
            sell_value = (position["NumShares"] * final_price["Close"].iloc[0]) - fees
            capital += sell_value
            closed_dict = {"SellDate":final_price["Date"].iloc[0],
                            "SellPrice":final_price["Close"].iloc[0],
                            "SellValue":sell_value}
            position.update(closed_dict)
            # update trade
            trade += 1
            # record transaction
            self.__append_transaction(position)


    @staticmethod
    def download_price(ticker ,timeframe, start_date, end_date):
        # download historical price using yfinance
        historical = yf.download(ticker, start=start_date, end=end_date, interval=timeframe, auto_adjust=True, progress = False)
        if "Adj Close" in historical.columns.tolist():
            historical["Close"] = historical["Adj Close"]

        return historical[["Open","High","Low","Close"]]
    

    @staticmethod
    def buy_and_hold(df):
        buy_price = df.sort_values("Date").head(1)["Close"].iloc[0]
        cur_price = df.sort_values("Date").tail(1)["Close"].iloc[0]
        pl = round(cur_price - buy_price, 2)
        pl_per = round((cur_price - buy_price) / buy_price * 100, 2)
        return (pl, pl_per)


    @classmethod
    def __append_transaction(cls, position):
        # append transaction
        position = pd.Series(position)
        if "SellPrice" in position.index:
            position = position.drop([idx for idx in position.index if idx.startswith("Buy")])
        position["Action"] = "Sell" if "SellPrice" in position.index else "Buy"
        position = position.rename({"SellPrice":"Price",
                                        "BuyPrice":"Price",
                                        "BuyValue":"Value",
                                        "SellValue":"Value",
                                        "BuyDate":"Date",
                                        "SellDate":"Date"})
        
        cls.transaction = cls.transaction.append(position, sort=True, ignore_index=True)


    @classmethod
    def get_closed_position(cls):
        # validate
        if len(cls.transaction) < 1:
            raise Exception("There is no result to export")
        buy_df = cls.transaction[cls.transaction["Action"]=="Buy"].rename({"Price":"BuyPrice",
                                                                    "Date":"BuyDate",
                                                                    "Value":"BuyValue"}, axis=1).drop("Action", axis=1)
        sell_df = cls.transaction[cls.transaction["Action"]=="Sell"].rename({"Price":"SellPrice",
                                                                            "Date":"SellDate",
                                                                            "Value":"SellValue"}, axis=1).drop("Action", axis=1)

        closed = pd.merge(buy_df, sell_df, on=["TICKER","NumShares","Trade"])
        closed["P/L"] = closed["SellValue"] - closed["BuyValue"]
        closed["P/L (%)"] = (closed["SellValue"] - closed["BuyValue"]) / closed["BuyValue"] * 100
        return closed


    @classmethod
    def export_result(cls, filepath):
        if len(cls.transaction) < 1:
            raise Exception("There is no result to export")

        else:
            # format transaction
            transaction_write = cls.transaction.copy()
            for col in ["Price","Value"]:
                transaction_write[col] = transaction_write[col].map(lambda x: round(x,2))
            transaction_write["Date"] = pd.to_datetime(transaction_write["Date"], format="%Y-%m-%d")
            transaction_write = transaction_write[["TICKER","Date","Action","Price","NumShares","Value"]].copy()

            closed = cls.get_closed_position()
            # format closed position
            for col in ["BuyDate","SellDate"]:
                closed[col] = pd.to_datetime(closed[col], format="%Y-%m-%d")
            for col in ["BuyPrice","SellPrice","BuyValue","SellValue","P/L","P/L (%)"]:
                closed[col] = closed[col].map(lambda x: round(x,2))
            closed = closed.drop("Trade", axis=1)
            closed = closed[["TICKER","BuyDate","NumShares","BuyPrice","BuyValue","SellDate","SellPrice","SellValue","P/L","P/L (%)"]]

            # write to excel
            timestamp = str(datetime.now())[:19].replace(":","")
            filename = os.path.join(filepath,f"backtesting result_{timestamp}.xlsx")
            workbook = xlsxwriter.Workbook(filename)
            workbook.close()
            with pd.ExcelWriter(filename, date_format="YYYY-MM-DD") as writer:
                transaction_write.to_excel(writer, sheet_name = "Transaction", index=False)
                closed.to_excel(writer, sheet_name="Closed Position", index=False)