from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure secret key

# Configure Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure SQLite database
DATABASE = 'football_turf.db'

# User class for Flask-Login
class User(UserMixin):  
    def __init__(self, id, username):
        self.id = id
        self.username = username

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Initialize the database
init_db()

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Register form
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Home Page/ index page
@app.route('/index')
def index():
    return render_template('index.html')

# Available Slots Page
@app.route('/available_slots')      
def available_slots():
    # Retrieve booked slots for the current date from the database
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT date, start_time, end_time FROM bookings WHERE date = ?', (current_date,))
        booked_slots = set(
            (start_time, end_time) for date, start_time, end_time in cursor.fetchall()
        )

    # Generate available slots for the current date from 6:00 AM to 12:00 AM with 1-hour intervals
    start_time = datetime.strptime("06:00", "%H:%M")
    end_time = datetime.strptime("00:00", "%H:%M") + timedelta(days=1)  # Add one day to reach 12:00 AM next day

    current_time = start_time
    available_slots = []

    while current_time < end_time:
        end_slot_time = current_time + timedelta(hours=1)
        slot = (current_time.strftime('%H:%M'), end_slot_time.strftime('%H:%M'))

        # Check if the slot is booked
        slot_status = "Available"
        if slot in booked_slots:
            slot_status = "Booked"

        available_slots.append({"time_slot": f"{slot[0]} - {slot[1]}", "status": slot_status})
        current_time = end_slot_time

    return render_template('available_slots.html', available_slots=available_slots)

# Book Slot Page
@app.route('/book_slot', methods=['GET', 'POST'])
@login_required
def book_slot():
    if request.method == 'POST':
        username = current_user.username  # Get the current user's username
        date = request.form['date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute('''
                INSERT INTO bookings (username, date, start_time, end_time)
                VALUES (?, ?, ?, ?)
            ''', (username, date, start_time, end_time))
            db.commit()

        return render_template('booking_confirmation.html', booking_date=date, time_slot=f"{start_time} - {end_time}")

    return render_template('book_slot.html')

# My Bookings Page
@app.route('/my_bookings')
@login_required
def my_bookings():
    username = current_user.username  # Get the current user's username
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('''
            SELECT date, start_time, end_time
            FROM bookings
            WHERE username = ?
        ''', (username,))
        bookings = cursor.fetchall()

    return render_template('my_bookings.html', bookings=bookings)

# Booking Confirmation Page
@app.route('/booking_confirmation')
def booking_confirmation():
    # Get the booking details from the query parameters
    booking_date = request.args.get('booking_date')
    time_slot = request.args.get('time_slot')

    return render_template('booking_confirmation.html', booking_date=booking_date, time_slot=time_slot)

# Login route
@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()

            if user and user['password'] == password:
                # Login successful, load user into the session
                user_obj = User(id=user['id'], username=user['username'])
                login_user(user_obj)
                flash('Login successful!', 'success')

                # Redirect to the index page after successful login
                return redirect(url_for('index'))

        flash('Invalid username or password', 'error')

    return render_template('login.html', form=form)


# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            db.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html', form=form)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'success')
    return redirect(url_for('login'))

# User loader function
@login_manager.user_loader
def load_user(user_id):
    # Load and return the user from the database
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return User(id=user['id'], username=user['username'])
    return None

if __name__ == '__main__':
    app.run(debug=True)
