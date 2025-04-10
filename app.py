from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

app = Flask(__name__)
app.secret_key = '1231231321'  # Zmień na losowy ciąg

# Konfiguracja bazy MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:bazahaslo@localhost/system_rezerwacji'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Modele
class Uzytkownik(db.Model, UserMixin):
    __tablename__ = 'uzytkownicy'
    id_user = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    imie = db.Column(db.String(50), nullable=False)
    nazwisko = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Enum('admin', 'klient'), nullable=False)

    def get_id(self):
        return str(self.id_user)


class Stolik(db.Model):
    __tablename__ = 'stoliki'
    id_stolika = db.Column(db.Integer, primary_key=True)
    ilosc_miejsc = db.Column(db.Integer, nullable=False)
    wolny = db.Column(db.Boolean, nullable=False, default=True)


class Rezerwacja(db.Model):
    __tablename__ = 'rezerwacje'
    id_rezerwacji = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('uzytkownicy.id_user'), nullable=False)
    id_stolika = db.Column(db.Integer, db.ForeignKey('stoliki.id_stolika'), nullable=False)
    data = db.Column(db.DateTime, nullable=False)
    oplacony = db.Column(db.Boolean, nullable=False, default=False)


@login_manager.user_loader
def load_user(user_id):
    return Uzytkownik.query.get(int(user_id))


# Strona główna
@app.route('/')
def home():
    stoliki = Stolik.query.all()
    return render_template('home.html', user=current_user, stoliki=stoliki)


# Logowanie
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = Uzytkownik.query.filter_by(email=email).first()

        if user and user.password == password:
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


# Rezerwacja stolika
@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    if request.method == 'POST':
        stolik_id = request.form['stolik_id']
        data = request.form['data']  # Format: "YYYY-MM-DD HH:MM"
        stolik = Stolik.query.get(stolik_id)

        if stolik and stolik.wolny:
            rezerwacja = Rezerwacja(
                id_user=current_user.id_user,
                id_stolika=stolik_id,
                data=datetime.strptime(data, '%Y-%m-%d %H:%M'),
                oplacony=False
            )
            stolik.wolny = False
            db.session.add(rezerwacja)
            db.session.commit()
            flash('Rezerwacja dodana!')
            return redirect(url_for('my_reservations'))
        else:
            flash('Stolik niedostępny.')
    stoliki = Stolik.query.filter_by(wolny=True).all()
    return render_template('reserve.html', stoliki=stoliki)


# Moje rezerwacje
@app.route('/my_reservations')
@login_required
def my_reservations():
    rezerwacje = Rezerwacja.query.filter_by(id_user=current_user.id_user).all()
    return render_template('my_reservations.html', rezerwacje=rezerwacje)


# Panel admina
@app.route('/admin')
@login_required
def admin():
    if current_user.status != 'admin':
        flash('Dostęp tylko dla admina.')
        return redirect(url_for('home'))
    rezerwacje = Rezerwacja.query.all()
    stoliki = Stolik.query.all()
    return render_template('admin.html', rezerwacje=rezerwacje, stoliki=stoliki)


# Oznacz jako opłacone (dla admina)
@app.route('/mark_paid/<int:rezerwacja_id>')
@login_required
def mark_paid(rezerwacja_id):
    if current_user.status != 'admin':
        return redirect(url_for('home'))
    rezerwacja = Rezerwacja.query.get(rezerwacja_id)
    if rezerwacja:
        rezerwacja.oplacony = True
        db.session.commit()
        flash('Rezerwacja oznaczona jako opłacona.')
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True)