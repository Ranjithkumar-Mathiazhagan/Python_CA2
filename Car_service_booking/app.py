from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Email, Length
from flask_mysqldb import MySQL
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from flask_mail import Mail,Message

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# MySQL configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'root')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'car_service_booking')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


mysql = MySQL(app)



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
    service_type = SelectField("Service Type", choices=[('maintenance', 'Maintenance'), ('repair', 'Repair'), ('inspection', 'Inspection')], validators=[DataRequired()])
    date = DateField("Preferred Date", format='%Y-%m-%d', validators=[DataRequired()])
    time = TimeField("Preferred Time", format='%H:%M', validators=[DataRequired()])
    vehicle_make = StringField("Vehicle Make", validators=[DataRequired()])
    vehicle_model = StringField("Vehicle Model", validators=[DataRequired()])
    vehicle_year = StringField("Vehicle Year", validators=[DataRequired()])
    license_plate = StringField("License Plate Number", validators=[DataRequired()])
    submit = SubmitField("Book Now")

class AdminRegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    submit = SubmitField("Register")


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
        service_type = form.service_type.data
        date = form.date.data
        time = form.time.data
        vehicle_make=form.vehicle_make.data
        vehicle_model = form.vehicle_model.data
        vehicle_year = form.vehicle_year.data
        license_plate=form.license_plate.data

        if 'user_id' in session:
            user_id = session['user_id']
        else:
            flash('User not logged in', 'danger')
            return redirect(url_for('login'))  # Redirect to login if user is not logged in

        cursor = mysql.connection.cursor()
        try:
            cursor.execute("INSERT INTO bookings (user_id, service_type, date, time,vehicle_make,vehicle_model,vehicle_year,license_plate) VALUES (%s, %s, %s, %s,%s,%s,%s,%s)",
                           (user_id, service_type, date, time,vehicle_make,vehicle_model,vehicle_year,license_plate))
            mysql.connection.commit()
            cursor.close()

            session['service_type'] = service_type
            session['date'] = date.strftime('%Y-%m-%d')
            session['time'] = time.strftime('%H:%M')
            session['vehicle_make'] = vehicle_make
            session['vehicle_model'] = vehicle_model
            session['vehicle_year'] = vehicle_year
            session['license_plate'] = license_plate
            

            flash('Your service has been booked successfully', 'success')
            return redirect(url_for('submit_book'))
        except Exception as e:
            flash('Booking failed: ' + str(e), 'danger')
            cursor.close()

    return render_template('booking.html', form=form)

@app.route('/submit_book', methods=['GET'])
def submit_book():
    service_type = session.get('service_type')
    date = session.get('date')
    time = session.get('time')

    if not service_type or not date or not time:
        flash('Booking information is missing. Please book your service again.', 'danger')
        return redirect(url_for('booking'))

    return render_template('submit_book.html', service_type=service_type, date=date, time=time)


@app.route("/bookings", methods=['GET'])
def bookings():
    if 'user_id' not in session:
        flash('You need to be logged in to view your bookings', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT booking_id, service_type, date, time FROM bookings WHERE user_id = %s", (user_id,))
    user_bookings = cursor.fetchall()
    cursor.close()

    # Convert date and time to strings
    for booking in user_bookings:
        if isinstance(booking['date'], datetime):
            booking['date'] = booking['date'].strftime('%Y-%m-%d')
        if isinstance(booking['time'], timedelta):
            total_seconds = booking['time'].total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            booking['time'] = f'{hours:02}:{minutes:02}'

    return render_template('bookings.html', bookings=user_bookings)


@app.route("/delete_booking/<int:booking_id>", methods=["POST"])
def delete_booking(booking_id):
    if 'user_id' not in session:
        flash('You need to be logged in to delete your bookings', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s AND user_id = %s", (booking_id, user_id))
        mysql.connection.commit()
        flash('Booking deleted successfully', 'success')
    except Exception as e:
        flash('Failed to delete booking: ' + str(e), 'danger')
    finally:
        cursor.close()

    return redirect(url_for('bookings'))


# Route for logging out
@app.route("/logout")
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/admin_reg',methods=['GET', 'POST'])
def admin_reg():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admins WHERE email = %s", [email])
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            cursor.close()
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            try:
                cursor.execute("INSERT INTO admins ( email, password) VALUES (%s, %s)", (email,hashed_password))
                mysql.connection.commit()
                flash('You are now registered and can log in', 'success')
                return redirect(url_for('admin_login'))
            except Exception as e:
                flash('Registration failed: ' + str(e), 'danger')
            finally:
                cursor.close()
    return render_template('admin_reg.html', form=form)


@app.route('/admin_login',methods=['GET', 'POST'])
def admin_login():  
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admins WHERE email = %s", [email])
        user = cursor.fetchone()
        cursor.close()

        if user:
            if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                session['admin_id'] = user['admin_id']
                flash('You are now logged in', 'success')
                return redirect(url_for('admin_index'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        else:
            flash('Email not registered. Please register first.', 'danger')
    
    return render_template('admin_login.html', form=form)



@app.route('/admin_index')
def admin_index():
     if 'admin_id' not in session:
        flash('You need to be logged as Admin in to access the dashboard', 'danger')
        return redirect(url_for('admin_login'))
    
     cursor = mysql.connection.cursor()
     cursor.execute("SELECT count(ID) as total_users FROM users")
     total_users = cursor.fetchone()['total_users']
     
     cursor = mysql.connection.cursor()
     cursor.execute("SELECT count(booking_id) as total_bookings FROM bookings")
     total_bookings = cursor.fetchone()['total_bookings']
     
     cursor=mysql.connection.cursor()
     cursor.execute("""
                   select  b.booking_id, u.ID,b.service_type, b.date, b.time,b.vehicle_make,b.vehicle_model,b.vehicle_year,b.license_plate
                   from bookings as b
                   join users u on b.user_id=u.ID
                   ORDER BY b.booking_id ASC """)
     
     bookings= cursor.fetchall()
                
     cursor.close()

     return render_template('admin_index.html',  total_users=total_users,total_bookings=total_bookings,bookings=bookings)
 
@app.route("/admin_delete/<int:booking_id>", methods=["POST"])
def admin_delete(booking_id):

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s" , (booking_id,))
        mysql.connection.commit()
        flash('Booking deleted successfully', 'success')
    except Exception as e:
        flash('Failed to delete booking: ' + str(e), 'danger')
    finally:
        cursor.close()

    return redirect(url_for('admin_index'))


@app.route('/admin_update/<int:booking_id>',methods=['GET', 'POST'])
def admin_update(booking_id):
    if 'admin_id' not in session:
        flash('You need to be logged as Admin in to access the dashboard', 'danger')
        return redirect(url_for('admin_login'))
    
    cursor = mysql.connection.cursor()
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
        booking = cursor.fetchone()
        cursor.close()
        
        if not booking:
            flash('Booking not found', 'danger')
            return redirect(url_for('admin_index'))
        return render_template('admin_update.html', booking=booking)
    
    elif request.method == 'POST':
        
        service_type = request.form['service_type']
        date = request.form['date']
        time = request.form['time']
        
        try:
            cursor.execute("""
                UPDATE bookings
                SET service_type = %s, date = %s, time = %s
                WHERE booking_id = %s
            """, (service_type, date, time, booking_id))
            mysql.connection.commit()
            cursor.close()
            
            flash('Booking updated successfully', 'success')
            return redirect(url_for('admin_index'))
        except Exception as e:
            flash('Failed to update booking: ' + str(e), 'danger')
            cursor.close()
            return redirect(url_for('admin_index'))                    
                                          
if __name__ == '__main__':
    app.run(debug=True)


