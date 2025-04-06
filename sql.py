from flask import jsonify
from application import app, models
from application.routes import message_id_exists
from sqlalchemy.exc import SQLAlchemyError


def get_json_object(key, table, column_list=None):
    try:
        get_table = getattr(models, table)
        result = get_table.query.filter_by(id=key).first()
        if not result:
            return jsonify({'error': f"No entry found with id {key} in table {table}."})

        if column_list is None:
            column_list = get_table.__table__.columns.keys()

        data = {column: getattr(result, column, None) for column in column_list}
        return jsonify(data)

    except AttributeError:
        return jsonify({'error': f"{table} is not a valid table name."})


def add_user(user_name, email, password, phone_number):
    if models.user.query.filter_by(email=email).first():
        raise ValueError("User with provided email already exists")

    hashed_password = password  # Add hashing here
    new_user = models.user(user_name=user_name, email=email,
                           password=hashed_password, phone_number=phone_number, risk_tolerance='Moderate')
    models.db.session.add(new_user)
    models.db.session.commit()
    models.db.session.close()


def get_user_data(email):
    user = models.user.query.filter_by(email=email).first()
    if user:
        return user, [user.user_name, user.email, user.phone_number, user.risk_tolerance]
    return None, None


def check_api_key(email):
    user = models.user.query.filter_by(email=email).first()
    return user and user.openai_key is not None


def update_user_field(email, field_name, new_value):
    user = models.user.query.filter_by(email=email).first()
    if not user:
        raise ValueError("User not found")

    if hasattr(user, field_name):
        setattr(user, field_name, new_value)
        models.db.session.commit()
        models.db.session.close()
        return True
    raise ValueError("Invalid field name")


update_api_key = lambda email, key: update_user_field(email, 'openai_key', key)
update_name = lambda email, val: update_user_field(email, 'user_name', val)
update_email = lambda email, val: update_user_field(email, 'email', val)
update_phone = lambda email, val: update_user_field(email, 'phone_number', val)
update_risk_tolerance = lambda email, val: update_user_field(email, 'risk_tolerance', val)


def check_query_count(email):
    user = models.user.query.filter_by(email=email).first()
    return user and user.query_count > 0


def reduce_query_count(email):
    user = models.user.query.filter_by(email=email).first()
    if user:
        user.query_count -= 1
        models.db.session.commit()
        models.db.session.close()
        return True
    return False


def get_user_id(email):
    user = models.user.query.filter_by(email=email).first()
    return user.user_id if user else None


def add_or_update_stock(email, date, ticker, quantity, start_price, current_price, return_percent, return_amount, total):
    user_id = get_user_id(email)
    if not user_id:
        raise ValueError("Invalid user")

    stock = models.portfolio.query.filter_by(user_id=user_id, ticker=ticker, date_added=date).first()
    if stock:
        stock.quantity += float(quantity)
        stock.current_price = float(current_price)
        stock.return_percent = float(return_percent)
        stock.return_amount = float(return_amount)
        stock.total = float(total)
    else:
        new_stock = models.portfolio(user_id=user_id, date_added=date, ticker=ticker, quantity=float(quantity),
                                     price_bought=float(start_price), current_price=float(current_price),
                                     return_percent=float(return_percent), return_amount=float(return_amount),
                                     total=float(total))
        models.db.session.add(new_stock)
    models.db.session.commit()
    models.db.session.close()


def update_stock(email, ticker, quantity):
    user_id = get_user_id(email)
    stock = models.portfolio.query.filter_by(user_id=user_id, ticker=ticker).first()
    if not stock:
        raise ValueError("No such stock")
    if quantity == 0:
        models.db.session.delete(stock)
    else:
        stock.quantity = str(int(stock.quantity) + int(quantity))
    models.db.session.commit()
    models.db.session.close()


def reset_portfolio(email):
    user_id = get_user_id(email)
    stocks = models.portfolio.query.filter_by(user_id=user_id).all()
    for stock in stocks:
        models.db.session.delete(stock)
    models.db.session.commit()
    models.db.session.close()


def get_stock_data(email):
    user_id = get_user_id(email)
    stocks = models.portfolio.query.filter_by(user_id=user_id).order_by(models.portfolio.date_added).all()
    stock_data = [[s.date_added.strftime('%d-%m-%Y'), s.ticker, s.quantity, s.price_bought,
                   s.current_price, s.return_percent, s.return_amount, s.total] for s in stocks]
    return stocks, stock_data


def get_messages(email):
    user_id = get_user_id(email)
    messages = models.messages.query.filter_by(user_id=user_id).all()
    messages_data = {str(idx): {'body': m.body, 'created_at': m.created_at, 'is_bot': m.is_bot}
                     for idx, m in enumerate(messages)}
    return messages, messages_data


def add_message(email, message, date, is_bot=False):
    user_id = get_user_id(email)
    if not models.messages.query.filter_by(user_id=user_id, body=message).first():
        new_message = models.messages(user_id=user_id, body=message, created_at=date, is_bot=is_bot)
        models.db.session.add(new_message)
        models.db.session.commit()
        models.db.session.close()


def chat_data_list(user_chats, search_query):
    def append_pair(chat_idx, is_search=False):
        if not user_chats[chat_idx].is_bot:
            next_msg = user_chats[chat_idx+1] if chat_idx+1 < len(user_chats) else None
            return_data.append({
                'created_at': user_chats[chat_idx].created_at,
                'body': user_chats[chat_idx].body,
                'id': user_chats[chat_idx].message_id
            })
            return_data.append({
                'created_at': next_msg.created_at if next_msg else user_chats[chat_idx].created_at,
                'body': next_msg.body if next_msg and next_msg.is_bot else "(No message from bot is stored for this message...)",
                'id': next_msg.message_id if next_msg else user_chats[chat_idx].message_id
            })

    return_data = []
    all_chats = user_chats.all()
    if not search_query:
        for i in range(len(all_chats)):
            append_pair(i)
    else:
        filtered = user_chats.filter(models.messages.body.contains(search_query)).all()
        filtered_ids = {msg.message_id for msg in filtered}
        for i in range(len(all_chats)):
            if all_chats[i].message_id in filtered_ids:
                append_pair(i, is_search=True)

    return return_data


with app.app_context():
    models.db.create_all()
