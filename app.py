from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
import random
import string
import pyotp
import requests
import threading
import time
import imaplib
import email
from email.header import decode_header
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email config (example with Gmail SMTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your_email_password'  # Replace with your email password or app password

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    otp_secret = db.Column(db.String(16))
    phonepe_notifications = db.Column(db.Boolean, default=False)
    bank_details = db.Column(db.Text, default='')

# Transaction model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)
    description = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    fraud_flag = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def send_email(subject, recipients, body):
    msg = Message(subject, recipients=recipients)
    msg.body = body
    mail.send(msg)

def generate_otp_secret():
    return pyotp.random_base32()

def send_otp_email(user):
    totp = pyotp.TOTP(user.otp_secret)
    otp = totp.now()
    send_email("Your OTP Code", [user.email], f"Your OTP code is {otp}")

def verify_otp(user, otp):
    totp = pyotp.TOTP(user.otp_secret)
    return totp.verify(otp)

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email_ = request.form.get('email')
        password_ = request.form.get('password')
        if User.query.filter_by(email=email_).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        otp_secret = generate_otp_secret()
        new_user = User(email=email_, password=password_, otp_secret=otp_secret)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_ = request.form.get('email')
        password_ = request.form.get('password')
        user = User.query.filter_by(email=email_).first()
        if not user or user.password != password_:
            flash('Invalid credentials')
            return redirect(url_for('login'))
        session['pre_2fa_userid'] = user.id
        send_otp_email(user)
        return redirect(url_for('two_factor'))
    return render_template('login.html')

@app.route('/two_factor', methods=['GET', 'POST'])
def two_factor():
    if 'pre_2fa_userid' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['pre_2fa_userid'])
    if request.method == 'POST':
        otp = request.form.get('otp')
        if verify_otp(user, otp):
            login_user(user)
            session.pop('pre_2fa_userid', None)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid OTP')
            return redirect(url_for('two_factor'))
    return render_template('two_factor.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # YouTube awareness program embed link (example)
    youtube_embed_url = "https://www.youtube.com/embed/videoseries?list=PLAwxTw4SYaPn_7u7v7v6zQ7vQ9Q6q3x7p"  # Replace with actual playlist ID
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('dashboard.html', youtube_embed_url=youtube_embed_url, transactions=transactions, bank_details=current_user.bank_details)

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    data = request.json
    amount = data.get('amount')
    description = data.get('description')
    fraud_flag = detect_fraud(description)
    transaction = Transaction(user_id=current_user.id, amount=amount, description=description, fraud_flag=fraud_flag)
    db.session.add(transaction)
    db.session.commit()
    # Send email notification
    send_email(
        "New Transaction Alert",
        [current_user.email],
        f"Transaction of amount {amount} recorded.\nDescription: {description}\nFraud Alert: {'Yes' if fraud_flag else 'No'}"
    )
    return jsonify({'status': 'success', 'fraud_flag': fraud_flag})

def detect_fraud(description):
    # Simple fraud detection example: flag if suspicious keywords found
    suspicious_keywords = ['scam', 'fraud', 'phishing', 'hack']
    desc_lower = description.lower()
    for word in suspicious_keywords:
        if word in desc_lower:
            return True
    return False

@app.route('/update_bank_details', methods=['POST'])
@login_required
def update_bank_details():
    bank_details = request.form.get('bank_details')
    current_user.bank_details = bank_details
    db.session.commit()
    flash('Bank details updated')
    return redirect(url_for('dashboard'))

@app.route('/user_guide')
@login_required
def user_guide():
    # Static user guide page
    return render_template('user_guide.html')

@app.route('/tutorials')
@login_required
def tutorials():
    # Static tutorials page
    return render_template('tutorials.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# PhonePe transaction notification simulation endpoint
@app.route('/phonepe_notify', methods=['POST'])
def phonepe_notify():
    data = request.json
    email_ = data.get('email')
    amount = data.get('amount')
    description = data.get('description')
    user = User.query.filter_by(email=email_).first()
    if not user:
        return jsonify({'status': 'user not found'}), 404
    transaction = Transaction(user_id=user.id, amount=amount, description=description)
    db.session.add(transaction)
    db.session.commit()
    # Send email notification
    send_email(
        "PhonePe Transaction Notification",
        [user.email],
        f"PhonePe transaction received.\nAmount: {amount}\nDescription: {description}"
    )
    return jsonify({'status': 'notification sent'})

# Email monitoring for transaction messages (example for Gmail IMAP)
def monitor_email_transactions():
    EMAIL = app.config['MAIL_USERNAME']
    PASSWORD = app.config['MAIL_PASSWORD']
    IMAP_SERVER = 'imap.gmail.com'

    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, PASSWORD)
            mail.select("inbox")
            status, messages = mail.search(None, '(UNSEEN)')
            mail_ids = messages[0].split()
            for mail_id in mail_ids:
                status, msg_data = mail.fetch(mail_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else 'utf-8')
                        from_ = msg.get("From")
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                if content_type == "text/plain" and "attachment" not in content_disposition:
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                        # Simple parsing to detect transaction info (customize as needed)
                        if "transaction" in subject.lower() or "transaction" in body.lower():
                            # Extract email from 'from_' or body or subject as needed
                            # Here we assume the email is the user email
                            user = User.query.filter_by(email=EMAIL).first()
                            if user:
                                amount = extract_amount(body)
                                description = subject
                                fraud_flag = detect_fraud(body)
                                transaction = Transaction(user_id=user.id, amount=amount, description=description, fraud_flag=fraud_flag)
                                db.session.add(transaction)
                                db.session.commit()
                                send_email(
                                    "New Transaction Email Detected",
                                    [user.email],
                                    f"Transaction detected from email.\nAmount: {amount}\nDescription: {description}\nFraud Alert: {'Yes' if fraud_flag else 'No'}"
                                )
            mail.logout()
        except Exception as e:
            print("Email monitoring error:", e)
        time.sleep(60)  # Check every 60 seconds

def extract_amount(text):
    # Simple extraction of amount from text (improve regex as needed)
    import re
    match = re.search(r'(\d+[\.,]?\d*)', text)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except:
            return 0.0
    return 0.0

# Start email monitoring in background thread
email_thread = threading.Thread(target=monitor_email_transactions, daemon=True)
email_thread.start()

# Templates (minimal inline for demonstration, replace with actual HTML files)
from flask import Markup

@app.context_processor
def inject_templates():
    def render_register():
        return Markup('''
        <h2>Register</h2>
        <form method="POST">
            Email: <input type="email" name="email" required><br>
            Password: <input type="password" name="password" required><br>
            <button type="submit">Register</button>
        </form>
        <a href="/login">Login</a>
        ''')

    def render_login():
        return Markup('''
        <h2>Login</h2>
        <form method="POST">
            Email: <input type="email" name="email" required><br>
            Password: <input type="password" name="password" required><br>
            <button type="submit">Login</button>
        </form>
        <a href="/register">Register</a>
        ''')

    def render_two_factor():
        return Markup('''
        <h2>Enter OTP</h2>
        <form method="POST">
            OTP: <input type="text" name="otp" required><br>
            <button type="submit">Verify</button>
        </form>
        ''')

    def render_dashboard(youtube_embed_url, transactions, bank_details):
        transactions_html = ''.join([
            f"<li>{t.timestamp} - {t.description} - ${t.amount} - Fraud: {'Yes' if t.fraud_flag else 'No'}</li>"
            for t in transactions
        ])
        return Markup(f'''
        <h2>Dashboard</h2>
        <iframe width="560" height="315" src="{youtube_embed_url}" frameborder="0" allowfullscreen></iframe>
        <h3>Bank Details</h3>
        <form method="POST" action="/update_bank_details">
            <textarea name="bank_details" rows="4" cols="50">{bank_details}</textarea><br>
            <button type="submit">Update Bank Details</button>
        </form>
        <h3>Transaction History</h3>
        <ul>{transactions_html}</ul>
        <a href="/user_guide">User Guide</a> | <a href="/tutorials">Tutorials</a> | <a href="/logout">Logout</a>
        ''')

    def render_user_guide():
        return Markup('''
        <h2>User Guide</h2>
        <p>Welcome to the app. Use the dashboard to view transactions, bank details, and tutorials.</p>
        <a href="/dashboard">Back to Dashboard</a>
        ''')

    def render_tutorials():
        return Markup('''
        <h2>Tutorials</h2>
        <ul>
            <li><a href="https://www.youtube.com/watch?v=example1" target="_blank">Tutorial 1</a></li>
            <li><a href="https://www.youtube.com/watch?v=example2" target="_blank">Tutorial 2</a></li>
        </ul>
        <a href="/dashboard">Back to Dashboard</a>
        ''')

    return dict(
        render_register=render_register,
        render_login=render_login,
        render_two_factor=render_two_factor,
        render_dashboard=render_dashboard,
        render_user_guide=render_user_guide,
        render_tutorials=render_tutorials
    )

@app.route('/register.html')
def register_html():
    return render_template_string('{{ render_register() }}')

@app.route('/login.html')
def login_html():
    return render_template_string('{{ render_login() }}')

@app.route('/two_factor.html')
def two_factor_html():
    return render_template_string('{{ render_two_factor() }}')

@app.route('/dashboard.html')
def dashboard_html():
    return render_template_string('{{ render_dashboard(youtube_embed_url, transactions, bank_details) }}')

@app.route('/user_guide.html')
def user_guide_html():
    return render_template_string('{{ render_user_guide() }}')

@app.route('/tutorials.html')
def tutorials_html():
    return render_template_string('{{ render_tutorials() }}')

# Overriding render_template to use inline templates for demo
from flask import render_template_string

@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST':
        email_ = request.form.get('email')
        password_ = request.form.get('password')
        if User.query.filter_by(email=email_).first():
            flash('Email already registered')
            return redirect(url_for('register_route'))
        otp_secret = generate_otp_secret()
        new_user = User(email=email_, password=password_, otp_secret=otp_secret)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully. Please login.')
        return redirect(url_for('login_route'))
    return render_template_string('{{ render_register() }}')

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        email_ = request.form.get('email')
        password_ = request.form.get('password')
        user = User.query.filter_by(email=email_).first()
        if not user or user.password != password_:
            flash('Invalid credentials')
            return redirect(url_for('login_route'))
        session['pre_2fa_userid'] = user.id
        send_otp_email(user)
        return redirect(url_for('two_factor_route'))
    return render_template_string('{{ render_login() }}')

@app.route('/two_factor', methods=['GET', 'POST'])
def two_factor_route():
    if 'pre_2fa_userid' not in session:
        return redirect(url_for('login_route'))
    user = User.query.get(session['pre_2fa_userid'])
    if request.method == 'POST':
        otp = request.form.get('otp')
        if verify_otp(user, otp):
            login_user(user)
            session.pop('pre_2fa_userid', None)
            return redirect(url_for('dashboard_route'))
        else:
            flash('Invalid OTP')
            return redirect(url_for('two_factor_route'))
    return render_template_string('{{ render_two_factor() }}')

@app.route('/dashboard')
@login_required
def dashboard_route():
    youtube_embed_url = "https://www.youtube.com/embed/videoseries?list=PLAwxTw4SYaPn_7u7v7v6zQ7vQ9Q6q3x7p"
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template_string('{{ render_dashboard(youtube_embed_url, transactions, bank_details) }}',
                                  youtube_embed_url=youtube_embed_url,
                                  transactions=transactions,
                                  bank_details=current_user.bank_details)

@app.route('/user_guide')
@login_required
def user_guide_route():
    return render_template_string('{{ render_user_guide() }}')

@app.route('/tutorials')
@login_required
def tutorials_route():
    return render_template_string('{{ render_tutorials() }}')

@app.route('/update_bank_details', methods=['POST'])
@login_required
def update_bank_details_route():
    bank_details = request.form.get('bank_details')
    current_user.bank_details = bank_details
    db.session.commit()
    flash('Bank details updated')
    return redirect(url_for('dashboard_route'))

@app.route('/logout')
@login_required
def logout_route():
    logout_user()
    return redirect(url_for('login_route'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
