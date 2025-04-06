import time
import openai
from flask import request

import sql
from config import Config

openai.api_key = Config.OPENAI_API_KEY


def update_openai_key(email, key):
    """
    Update OpenAI key

    Args:
        email (str): user's email
        key (str): new OpenAI key
    Returns:
        bool: True if key works, False otherwise
    """
    sql.update_api_key(email, key)
    Config.OPENAI_API_KEY = key
    openai.api_key = key

    # Test if key is valid
    try:
        test_result = davinci_003("test api key")
        return test_result is not None
    except Exception as e:
        print(f"OpenAI key validation failed: {e}")
        return False


def davinci_003(query, temperature=0):
    print("Starting text-davinci-003...\n")
    start_time = time.time()

    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=query,
        temperature=temperature,
        max_tokens=100,
        top_p=0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["|"]
    )

    elapsed_time = time.time() - start_time
    print(f"\nTime elapsed: {elapsed_time} seconds\n")

    return response.choices[0].text.strip().strip("'").strip()


def gpt_3(message_list, temperature=0.2):
    """
    Generate a GPT-3.5-turbo response.
    """
    print("Starting GPT-3.5-turbo...\n")
    start_time = time.time()

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=message_list,
        temperature=temperature
    )

    elapsed_time = time.time() - start_time
    print(f"\nTime elapsed: {elapsed_time} seconds\n")

    return response.choices[0].message.content


def gpt_with_info(message_list, temperature=1):
    """
    Add user + portfolio info to messages and use GPT-3.5-turbo.
    """
    email = request.cookies.get('email')
    user_data = sql.get_user_data(email)[1]
    portfolio_data = sql.get_stock_data(email)[1]

    user_info = f"User information: Username: {user_data[0]}, Email: {user_data[1]}, Phone number: {user_data[2]}."
    portfolio_info = f"User's risk tolerance: {user_data[3]}. "

    if not portfolio_data:
        portfolio_info += "User's portfolio is empty."
    else:
        portfolio_info += "User's portfolio information:"
        for stock in portfolio_data:
            portfolio_info += (
                f" Date added: {stock[0]}, Ticker: {stock[1]}, Quantity: {stock[2]}, "
                f"Start price: {stock[3]}, End price: {stock[4]}, Return percent: {stock[5]}, "
                f"Return amount: {stock[6]}, Total: {stock[7]}."
            )

    system_prompt = (
        "You are a friendly financial chatbot named Monetize.ai. The user will ask you questions, and you will provide polite responses. "
        + user_info + ' ' + portfolio_info +
        " If user asks to change risk tolerance, respond that it has been changed. "
        "If user bought or sold a stock, respond that their portfolio has been updated and include profit details."
    )

    # Ensure the first message is a system message
    if message_list:
        message_list[0] = {"role": "system", "content": system_prompt}
    else:
        message_list.insert(0, {"role": "system", "content": system_prompt})

    return gpt_3(message_list, temperature=temperature)
