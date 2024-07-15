from flask import Flask,render_template,  redirect, url_for, request, flash, session
from flask_mysqldb import MySQL

app = Flask (__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'car_service_booking'
app.config['MYSQL_CURSORCLASS']='DictCursor'
mysql = MySQL(app)

@app.route("/")
def index():
    return render_template ("index.html")

@app.route('/regsiter' )
def regsiter():
    if request.method=='POST':
        try:
            name=request.form['name']
            email=request.form['email']
            password=request.form['password']
            con=mysql.connection.cursor()
            cur=con.cursor()
            cur.excute("INSERT INTO users(name.email.password)values(?,?,?)",(name,email,password))
            con.commit()
            flash("Regsiter successfully")
            
        except:
            flash("error in insertion")
        finally:
            return redirect(url_for("login.html"))
            con.close()
        
        

@app.route('/login', methods=['GET','POST'])
def login():
    return render_template("login.html")



if __name__ == '__main__':
    app.run(debug=True)