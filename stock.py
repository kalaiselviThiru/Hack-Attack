from datetime import datetime
import finnhub
import pandas as pd
import requests
import yfinance as yf
from dateutil import parser

from config import Config

CLIENT = finnhub.Client(api_key=Config.FINNHUB_API_KEY)

def analyst(input_symbol):
    try:
        recommendations = CLIENT.recommendation_trends(symbol=input_symbol)
        if not recommendations:
            return f"No analyst recommendations found for {input_symbol}"

        recommendations_df = pd.DataFrame(recommendations)
        latest_recommendation = recommendations_df.iloc[0]

        response = (
            f"Latest analyst recommendation for {input_symbol}: "
            f"Date: {latest_recommendation['period']}, "
            f"Buy: {latest_recommendation['buy']}, "
            f"Hold: {latest_recommendation['hold']}, "
            f"Sell: {latest_recommendation['sell']}, "
            f"Strong Buy: {latest_recommendation['strongBuy']}, "
            f"Strong Sell: {latest_recommendation['strongSell']}"
        )
        return response
    except Exception as e:
        return f"Error fetching analyst recommendation: {str(e)}"


def parse_input(prompt):
    try:
        quantity, ticker, start_date_str, end_date_str = prompt

        start_date = parser.parse(start_date_str, fuzzy=True)
        end_date = datetime.now() if end_date_str.lower() == "today" else parser.parse(end_date_str, fuzzy=True)

        if start_date >= end_date:
            raise ValueError("Invalid date range: start date must be before end date")

        if end_date.date() > datetime.now().date():
            raise ValueError("Invalid date range: end date cannot be after today's date")

        return quantity, ticker.upper(), start_date, end_date, None
    except ValueError as e:
        return None, None, None, None, str(e)
    except Exception:
        return None, None, None, None, (
            "Invalid prompt format: please enter the prompt in the format "
            "'num_shares ticker start_date end_date'."
        )


def get_stock_data(num_shares, ticker, start_date, end_date):
    try:
        ticker_obj = yf.Ticker(ticker)
        company_name = ticker_obj.info.get('longName', ticker)

        stock_data = yf.download(ticker, start=start_date, end=end_date)
        if stock_data.empty:
            return f"No stock data found for {ticker}", None

        start_price = round(stock_data['Close'].iloc[0], 2)
        end_price = round(stock_data['Close'].iloc[-1], 2)

        return_amount = round((end_price - start_price) * int(num_shares), 2)
        return_percent = round((end_price - start_price) / start_price * 100, 2)
        total = round(end_price * int(num_shares), 2)
        profit_loss = 'profit' if return_amount > 0 else 'loss'

        response = (
            f"{num_shares} shares of {company_name} ({ticker}) from {start_date.strftime('%d-%m-%Y')} "
            f"to {end_date.strftime('%d-%m-%Y')}: start price = ${start_price:.2f}, "
            f"end price = ${end_price:.2f}, {profit_loss} = ${return_amount:.2f}"
        )
        return response, (start_date, ticker, num_shares, start_price, end_price, return_percent, return_amount, total)
    except Exception:
        return f"Invalid ticker symbol or data issue for: {ticker}", None


def prompt_profit(input_list):
    if len(input_list) == 4:
        num_shares, ticker, start_date, end_date, error_msg = parse_input(input_list)
        if error_msg:
            return error_msg, None
        response, data_tuple = get_stock_data(num_shares, ticker, start_date, end_date)
        full_response = (
            "Assume that I bought or sold the stock, using this information to give me a response on "
            "my stock details including start price, end price and profit if I sell it on the end date: "
            + response
        )
        return full_response, data_tuple
    return "Invalid input format. Provide 4 elements: num_shares, ticker, start_date, end_date", None


def prompt_recomendation(ticker):
    analystical = analyst(ticker)
    return "Using this information to give me an appropriate stock recommendation: " + analystical


def stock_price_target(symbol):
    try:
        api_key = 'MWQ9WK5A5KFZA5U6'
        url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        target_price = data.get('AnalystTargetPrice', 'N/A')
        return target_price if target_price != 'N/A' else 'No price target found for this stock'
    except requests.exceptions.RequestException as e:
        return f"Error accessing Alpha Vantage API: {str(e)}"
    except Exception:
        return "Unexpected error occurred while fetching price target."
