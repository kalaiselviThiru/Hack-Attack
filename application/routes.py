from application import app, models
from flask import render_template, redirect, url_for, session
from datetime import timedelta

from forms import LoginForm
import secrets

secrets_key = secrets.token_bytes(32)
app.config['SECRET_KEY'] = secrets_key



@app.route("/")
@app.route("/index")
@app.route("/home")
def index():
    if'Email' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

@app.route('/portfolio')
def portfolio():
    myportfolio = models.portfolio.query.order_by(models.portfolio.date_added).all()
    return render_template('portfolio.html', menuCss=True, portfolio=myportfolio)

@app.route('/history')
def history():
    return render_template('history.html')

@app.route("/settings")
def settings():
    return render_template('settings.html', menuCss=True)

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/about-us')
def aboutUs():
    return render_template('about-us.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session['Email'] = form.email.data
        session.permanent = True  # make the session cookie permanent
        app.permanent_session_lifetime = timedelta(days=1)
        return redirect(url_for('index'))
    return render_template('login.html',form=form)

@app.route("/logOut", methods=['GET', 'POST'])
def logOut():
    session.pop('email', None)
    form = LoginForm()
    
    return render_template('login.html',form=form)
