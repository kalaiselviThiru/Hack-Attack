import datetime
import logging
from datetime import datetime
import re

import openai
from flask import jsonify, request
from flask_cors import CORS

import open_ai_call
import sql
import stock as stk
from application import app

CORS(app)

context_data = 'You are a friendly financial chatbot named Monetize.ai. The user will ask you questions, and you will provide polite responses.\n\n'
messages = [{}]

def record(role, message):
    global messages
    messages.append({"role": role, "content": message})

@app.route('/generate', methods=['POST'])
def generate():
    try:
        global messages
        print("🔧 /generate called")

        email = request.cookies.get('email')
        if not email:
            return jsonify({'response': '❗Error: User email not found in cookies'})

        data = request.get_json()
        if 'prompt' not in data:
            return jsonify({'response': '❗Error: No prompt key in request body'})

        user_message = data['prompt']
        print(f"📥 Prompt: {user_message}")

        with open('prompt.txt', 'r') as prompt:
            prompt_input = prompt.read()
            result = open_ai_call.davinci_003(prompt_input + user_message + "\nOutput: |", 0)

        if not result or result.strip() == "":
            return jsonify({'response': '⚠️ AI model returned empty response'})

        output_list = result.split(' ')
        case = output_list[0]
        output_data = output_list[1:]
        print("🔎 Case:", case)
        print("📊 Output Data:", output_data)

        if case == 'buy':
            prompt_result = stk.prompt_profit(output_data)
            start_date, ticker, quantity, start_price, end_price, return_percent, return_amount, total = prompt_result[1]
            sql.add_stock(email, start_date, ticker, quantity, start_price, end_price, return_percent, return_amount, total)
            record("user", prompt_result[0])

        elif case == 'sell':
            prompt_result = stk.prompt_profit(output_data)
            start_date, ticker, quantity, start_price, end_price, return_percent, return_amount, total = prompt_result[1]
            if sql.get_stock_data(email):
                sql.update_stock(email, ticker, (0 - int(quantity)))
            record("user", prompt_result[0])

        elif case == 'rebalance':
            query = "Using my portfolio and risk tolerance above, suggest how to rebalance using only my current holding stocks."
            record("user", query)

        elif case == 'recommendation':
            ticker = output_data[0].strip()
            prompt_recommendation = stk.prompt_recomendation(ticker)
            record("user", prompt_recommendation)

        elif case == 'target':
            ticker = output_data[0].strip()
            price_target = stk.stock_price_target(ticker)
            query = f'This is the up-to-date price target: {price_target} for {ticker}. Using the price target to answer: {user_message}'
            record("user", query)

        elif case == 'risk':
            risk_tolerance = output_data[0].strip()
            sql.update_risk_tolerance(email, risk_tolerance)
            record("user", user_message)

        elif user_message.lower() == 'reset':
            messages = [{}]
            return jsonify({'response': "✅ Chatbot context has been reset."})

        elif case == 'reset_portfolio':
            sql.reset_portfolio(email)
            return jsonify({'response': "✅ Your portfolio has been reset."})

        else:
            record("user", user_message)

        result = open_ai_call.gpt_with_info(messages)
        record("assistant", result)

        sql.add_message(email, user_message, datetime.now(), False)
        sql.add_message(email, result, datetime.now(), True)

        return jsonify({'response': result})

    except openai.error.RateLimitError:
        return jsonify({'response': '🚫 Chatbot is overloaded. Please try again after a few seconds.'})
    except Exception as e:
        print("🚨 Exception:", str(e))
        return jsonify({'response': f"⚠️ Internal Server Error: {str(e)}"})

@app.route('/get_messages', methods=['GET', 'POST'])
def get_messages():
    email = request.cookies.get('email')
    if not email:
        return jsonify({'messages': ''})

    messages = sql.get_messages(email)[1]
    if messages is None or len(messages) < 2:
        return jsonify({'messages': ''})

    msg_result = {}
    length = len(messages)
    if not messages[str(length - 1)]['is_bot']:
        length -= 1

    msg_result['0'] = messages[str(length - 2)]
    msg_result['1'] = messages[str(length - 1)]
    return jsonify({'messages': msg_result})

@app.route('/update_openai_key', methods=['POST'])
def update_openai_key():
    data = request.get_json()
    email = request.cookies.get('email')
    key = data['key']
    print(f"🔐 Received key for {email}")

    update_success = open_ai_call.update_openai_key(email, key)
    if update_success:
        return jsonify({'response': 'success'})
    return jsonify({'response': 'error'})

@app.route('/update_field', methods=['POST'])
def update_field():
    email = request.cookies.get('email')
    data = request.get_json()
    field = data['field']
    new_value = data['newValue']
    print(f"🔄 Updating field {field} to {new_value}")

    try:
        if field == 'name':
            sql.update_name(email, new_value)
        elif field == 'email':
            sql.update_email(email, new_value)
        elif field == 'phone':
            sql.update_phone(email, new_value)
        elif field == 'openai-key':
            open_ai_call.update_openai_key(email, new_value)
    except ValueError as error:
        print("❗ ValueError:", error)
        return jsonify({'error': str(error)})
    except Exception as e:
        print("❗ Unknown error in update_field:", e)
        return jsonify({'error': 'unknown error'})

    return jsonify({'response': 'success'})

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)  # ✅ Match with frontend
