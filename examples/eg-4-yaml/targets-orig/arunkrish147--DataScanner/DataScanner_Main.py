from typing import List, Any, Union

import keyring as keyring
import robin_stocks as rh
import yaml as yaml
import json
import warnings
import datetime as dt
import pandas as pd
import psycopg2

company_list_csv = "./companylist.csv"
rh_stocks_json = "./rh_stocks.json"
rh_options_json = "./rh_options.json"
rh_options_shortlist_json = "./rh_options_shortlist.json"
ObjectStructure_yaml = "./ObjectStructure.yaml"
rh_options_expiration_json = "./options_by_expiration.json"
Auth_Flag = False


def authenticate():
    try:

        with open(r'./AccountConfig.yaml') as file:
            config_dict = yaml.full_load(file)
        service = config_dict["service"]
        user = config_dict["user"]
        pwd = keyring.get_password(service, user)
        login = rh.login(user, pwd)
        print("\n")
        print("Login success")
        print(" ~-~-~-~-~-~  ")
    except:
        print("Login failed! ABORT!!")
        print(" ~-~-~-~-~-~-~-~-~  ")
        exit()

    global Auth_Flag
    Auth_Flag = True


def find_options_by_profitability(ticker="AAPL", profitFloor=0.00, profitCeil=1.00):
    if Auth_Flag:
        option_query = rh.find_options_by_specific_profitability(ticker, strikePrice="1800", optionType="call",
                                                                 typeProfit="chance_of_profit_short", profitFloor=0.8,
                                                                 profitCeiling=1.0)
        return pd.DataFrame(option_query)
    else:
        print("Authentication missing")
        exit()


def get_option_schema(df_opt_query=None):
    with open(ObjectStructure_yaml, 'r') as file:
        option_search_dict = yaml.full_load(file)
    return option_search_dict['OptionSchema']  # returns list

    # pd.set_option("max_columns", None)
    # print(df_opt_query[print_list])
    # print(df_opt_query.size)

    # get_fundamentals()
    # get_popularity()
    # get_quotes()
    # get_ratings()
    # get_top_movers()
    # get_top_movers_sp500()
    # find_instrument_data()


# scans company_list csv dump from NASDAQ and generates list of symbols available for trade in Robinhood
def master_stock_list_refresh():
    warnings.filterwarnings("ignore")
    df_tickers = pd.read_csv(company_list_csv)[["Symbol"]]  # double square brackets returns DF instead of Series
    if Auth_Flag:
        rh_list = rh.stocks.get_instruments_by_symbols(df_tickers["Symbol"].tolist(), info='symbol')
    else:
        print("Authentication missing")
        exit()

    with open(rh_stocks_json, 'w') as outfile:
        json.dump(rh_list, outfile)
    print("RH Ticker List updated!")

# Not used as of now
def get_latest_price(ticker_list):
    return_list = []
    if Auth_Flag:
        for ticker_item in ticker_list:
            rh_quote = rh.stocks.get_latest_price(ticker_item)
            return_list.append(str(rh_quote))
    else:
        print("Authentication missing")
        exit()

    return return_list


def master_option_list_refresh():
    with open(rh_stocks_json, 'r') as infile:
        stock_tickers_list = json.load(infile)

    # stock_tickers_list = ['AAPL', 'INPX']
    option_tickers_list = []

    if Auth_Flag:
        for ti in stock_tickers_list:
            try:
                lis = rh.options.find_options_by_expiration(ti, "2020-08-15")
                option_tickers_list.append(str(ti))

            except:
                print("Passing : " + str(ti))
    else:
        print("Authentication missing")
        exit()

    with open(rh_options_json, 'w') as outfile:
        json.dump(option_tickers_list, outfile)

    print("RH Options List updated!")


def write_options_to_file(expiry_date):
    with open(rh_options_json, 'r') as infile:
        options_ticker_list = json.load(infile)

    option_extract_list = []
    option_skip_list = []

    # options_ticker_list = ["BA", "ZYXW", "BAC"]  # to be used for testing one file
    options_ticker_list.sort()

    df_option_chain = pd.DataFrame()

    if Auth_Flag:
        for options_ticker in options_ticker_list:
            try:
                print("Now Extracting : " + str(options_ticker))
                df_option_chain_temp = pd.DataFrame(rh.options.find_options_by_expiration(options_ticker,
                                                                                          expirationDate=expiry_date)
                                                    )
                quote_item = rh.stocks.get_latest_price(options_ticker)[0]  # Get price value from list
                df_option_chain_temp["quote"] = quote_item

                if df_option_chain.empty:
                    df_option_chain = df_option_chain_temp
                else:
                    df_option_chain = pd.concat([df_option_chain, df_option_chain_temp], ignore_index=True, sort=False)
                option_extract_list.append(options_ticker)
                print("Extracted : " + str(options_ticker))
            except:
                option_skip_list.append(options_ticker)
                print("Skipped : " + str(options_ticker))
    else:
        print("Authentication missing")
        exit()

    df_option_chain.to_json(r'./options_by_expiration.json')
    print('Options written to file!')

    print("Extract List : ")
    print(*option_extract_list)
    print("Skip List : ")
    print(*option_skip_list)


def scan_options(expiry_date, iv_from=0.01, iv_to=100.0):
    with open('./options_by_expiration.json', 'r') as infile:
        dic_test = json.load(infile)

    main_df = pd.DataFrame()
    for key, value in dic_test.items():
        df_temp = pd.DataFrame(value.values(), columns=[key])
        main_df = pd.concat([main_df, df_temp], axis=1).reindex(df_temp.index)

    # typecasting
    main_df["volume"] = pd.to_numeric(main_df["volume"], downcast="integer")
    main_df["open_interest"] = pd.to_numeric(main_df["open_interest"], downcast="integer")

    main_df["strike_price"] = pd.to_numeric(main_df["strike_price"], downcast="float")
    main_df["quote"] = pd.to_numeric(main_df["quote"], downcast="float")
    main_df["chance_of_profit_long"] = pd.to_numeric(main_df["chance_of_profit_long"], downcast="float")
    main_df["chance_of_profit_short"] = pd.to_numeric(main_df["chance_of_profit_short"], downcast="float")
    main_df["implied_volatility"] = pd.to_numeric(main_df["implied_volatility"], downcast="float")
    main_df["delta"] = pd.to_numeric(main_df["delta"], downcast="float")
    main_df["theta"] = pd.to_numeric(main_df["theta"], downcast="float")

    main_df["ask_price"] = pd.to_numeric(main_df["ask_price"], downcast="float")
    main_df["ask_size"] = pd.to_numeric(main_df["ask_size"], downcast="integer")
    main_df["bid_price"] = pd.to_numeric(main_df["bid_price"], downcast="float")
    main_df["bid_size"] = pd.to_numeric(main_df["bid_size"], downcast="integer")

    # Row Filters
    df_option_chain_filtered = main_df.loc[
        (main_df['state'] == "active") &
        (main_df['tradability'] == "tradable") &
        (main_df['expiration_date'] == expiry_date) &
        (main_df['implied_volatility'] >= float(iv_from)) &
        (main_df['implied_volatility'] <= float(iv_to)) &
        (main_df['volume'] > 999) &
        (main_df['open_interest'] > 999) &
        (main_df['bid_size'] > 9) &
        (main_df['ask_size'] > 9) &
        (main_df['bid_price'] > 0.01) &
        (main_df['ask_price'] > 0.01)
        ]

    # Filter columns
    df_option_chain_view = df_option_chain_filtered[get_option_schema()]

    # Rename Columns
    df_option_chain_view = df_option_chain_view.rename(
        columns={"chance_of_profit_long": "Long Profit%", "chance_of_profit_short": "Short Profit%"})

    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)
    pd.options.display.float_format = "{:.2f}".format

    print("*---------------------------------------------*")
    print("|  Options Scan Results for IV : " + str(iv_from) + " - " + str(iv_to) + "  |")
    print("*---------------------------------------------*")

    df_option_chain_sorted = df_option_chain_view.nlargest(100, 'implied_volatility')
    print(df_option_chain_sorted.sort_values(by=['implied_volatility', 'chain_symbol'], ascending=False).to_string(
        index=False))
    # print(df_option_chain_view)

    # Shortlist
    with open(rh_options_shortlist_json, 'r') as infile:
        options_ticker_shortlist = json.load(infile)

    df_sp500_plus = pd.DataFrame(options_ticker_shortlist, columns=["chain_symbol"])

    df_short_list_view = df_option_chain_view[df_option_chain_view.chain_symbol.isin(list(df_sp500_plus.chain_symbol))]
    df_short_list_sorted = df_short_list_view.nlargest(100, 'implied_volatility')
    print("")
    print("*--------------------------------------------------------*")
    print("|  SHORT LIST Options Scan Results for IV : " + str(iv_from) + " - " + str(iv_to) + "  |")
    print("*--------------------------------------------------------*")
    print(df_short_list_sorted.sort_values(by=['implied_volatility', 'chain_symbol'], ascending=False).to_string(
        index=False))


def get_front_expiry_week():
    today = dt.date.today()
    friday = today + dt.timedelta((4 - today.weekday()) % 7)
    return friday


def fetch_from_db():
    conn = psycopg2.connect(
        host="localhost",
        database="stock_mart",
        user="datascanner",
        password="1234")

    curr = conn.cursor()
    curr.execute('select * from stock_fundamentals')
    print(curr.fetchone())



def scanner_main():
    front_expiry = get_front_expiry_week()

    # authenticate()
    # master_stock_list_refresh()  # Generates RH stock ticker list and saves to rh_stocks json file
    # master_option_list_re#fresh() # Generates RH option ticker list and saves to rh_options json file
    # write_options_to_file(expiry_date=front_expiry.strftime("%Y-%m-%d"))  # Generates RH option data based on RH options ticker list
    #                                                 # and writes the data to options_by_expiration file

    # print("\nScanning Options for " + front_expiry.strftime("%b %d, %Y") + " Expiry\n")
    # scan_options(expiry_date=front_expiry.strftime("%Y-%m-%d"), iv_from=0.4, iv_to=100.0)

    print("DB Connection")
    fetch_from_db()

if __name__ == "__main__":
    scanner_main()
