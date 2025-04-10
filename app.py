from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import Length, EqualTo, Email, DataRequired

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

class RegisterForm(FlaskForm):
    username = StringField(label = 'username', validators = [Length(min = 2, max = 30), DataRequired()])
    fullname = StringField(label = 'fullname', validators = [Length(min=3, max = 30), DataRequired()])
    address = StringField(label = 'address', validators = [Length(min=7, max = 50), DataRequired()])
    phone_number = IntegerField(label = 'phone_number', validators = [DataRequired()]) #try to find phone
    password1 = PasswordField(label = 'password1', validators = [Length(min = 6), DataRequired()])
    password2 = PasswordField(label = 'password2', validators = [EqualTo('password1'), DataRequired()])
    submit = SubmitField(label = 'Sign Up')

class LoginForm(FlaskForm):
    username = StringField(label = 'username', validators = [DataRequired()])
    password = PasswordField(label = 'password', validators = [DataRequired()])
    submit = SubmitField(label = 'Sign In')


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
    forml = LoginForm()
    form = RegisterForm()
    if forml.validate_on_submit():
        attempted_user = Uzytkownik.query.filter_by(email=forml.username.data).first()
        if attempted_user and attempted_user.password == forml.password.data:  # Plaintext porównanie
            login_user(attempted_user)
            flash(f'Zalogowano pomyślnie jako: {attempted_user.email}', category='success')
            return redirect(url_for('home'))
        else:
            flash('Email lub hasło nieprawidłowe! Spróbuj ponownie.', category='danger')
    return render_template('login.html', forml=forml, form=form)


# Wylogowanie
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/register', methods = ['GET', 'POST'])
def register_page():
    forml = LoginForm()
    form = RegisterForm()
    #checks if form is valid
    if form.validate_on_submit():
         user_to_create = Uzytkownik(username = form.username.data,
                               fullname = form.fullname.data,
                               address = form.address.data,
                               phone_number = form.phone_number.data,
                               password = form.password1.data,)
         db.session.add(user_to_create)
         db.session.commit()
         login_user(user_to_create) #login the user on registration
         return redirect(url_for('verify'))
    # else:
    #     flash("Username already exists!")

    if form.errors != {}: #if there are not errors from the validations
        for err_msg in form.errors.values():
            flash(f'There was an error with creating a user: {err_msg}')
    return render_template('login.html', form = form, forml = forml)

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