from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField,SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Length
from flask_mysqldb import MySQL
import bcrypt
from flask_wtf.csrf import CSRFProtect
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# CSRF protection
csrf = CSRFProtect(app)

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")
    
    
class BookingForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    service_type = SelectField("Service Type", choices=[('maintenance', 'Maintenance'), ('repair', 'Repair'), ('inspection', 'Inspection')], validators=[DataRequired()])
    date = DateField("Preferred Date", format='%Y-%m-%d', validators=[DataRequired()])
    time = TimeField("Preferred Time", format='%H:%M', validators=[DataRequired()])
    submit = SubmitField("Book Now")

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'root')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'car_service_booking')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route("/index")
def index():
    return render_template("index.html")

@app.route('/', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", [email])
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            cursor.close()
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            try:
                cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
                mysql.connection.commit()
                flash('You are now registered and can log in', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                flash('Registration failed: ' + str(e), 'danger')
            finally:
                cursor.close()
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cursor.fetchone()
        cursor.close()

        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                session['user_id'] = user['ID']
                flash('You are now logged in', 'success')
                return redirect(url_for('index'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('Email not registered. Please register first.', 'danger')
    
    return render_template('login.html', form=form)

@app.route("/booking", methods=['GET', 'POST'])

def booking():
    form = BookingForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        service_type = form.service_type.data
        date = form.date.data
        time = form.time.data

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO bookings (name, email, service_type, date, time) VALUES (%s, %s, %s, %s, %s)", (name, email, service_type, date, time))
        mysql.connection.commit()
        cursor.close()

        flash('Your service has been booked successfully', 'success')
        return redirect(url_for('submit_book'))
    return render_template('booking.html', form=form)


@app.route('/submit_book')
def submit_book():
    
    return render_template('submit_book')


if __name__ == '__main__':
    app.run(debug=True)
