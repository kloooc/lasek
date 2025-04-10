from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = '123131313'  # Zmień na losowy ciąg znaków

# Konfiguracja bazy MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:bazahaslo@localhost/system_rezerwacji'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Model użytkownika
class Uzytkownik(db.Model, UserMixin):
    __tablename__ = 'uzytkownicy'
    id_user = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # Zmienione na 'password'
    imie = db.Column(db.String(50), nullable=False)
    nazwisko = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Enum('admin', 'klient'), nullable=False)

    def get_id(self):
        return str(self.id_user)


# Ładowanie użytkownika
@login_manager.user_loader
def load_user(user_id):
    return Uzytkownik.query.get(int(user_id))


# Strona główna
@app.route('/')
def home():
    return render_template('home.html', user=current_user)


# Panel logowania
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Uzytkownik.query.filter_by(email=email).first()

        if user and user.password == password:  # Porównanie w plaintekście
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Nieprawidłowy email lub hasło.')
    return render_template('login.html')


# Wylogowanie
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)