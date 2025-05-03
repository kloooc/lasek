from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, EqualTo, Email, DataRequired
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = '1231231321'  # Zmień na losowy ciąg w produkcji
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
    status = db.Column(db.Enum('admin', 'klient'), nullable=False, default='klient')

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


# Formularze
class RegisterForm(FlaskForm):
    email = StringField(label='email', validators=[Length(min=2, max=100), DataRequired(), Email()])
    password1 = PasswordField(label='password1', validators=[Length(min=6, max=100), DataRequired()])
    password2 = PasswordField(label='password2', validators=[EqualTo('password1'), DataRequired()])
    imie = StringField(label='imie', validators=[Length(min=3, max=50), DataRequired()])
    nazwisko = StringField(label='nazwisko', validators=[Length(min=3, max=50), DataRequired()])
    submit = SubmitField(label='Sign Up')


class LoginForm(FlaskForm):
    email = StringField(label='email', validators=[DataRequired(), Email()])
    password = PasswordField(label='password', validators=[DataRequired()])
    submit = SubmitField(label='Sign In')


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
        attempted_user = Uzytkownik.query.filter_by(email=forml.email.data).first()
        if attempted_user and attempted_user.password == forml.password.data:
            login_user(attempted_user)
            return redirect(url_for('home'))
        else:
            return jsonify({'status': 'error', 'message': 'Email lub hasło nieprawidłowe!'})
    return render_template('login.html', forml=forml, form=form, active_form='login')


# Wylogowanie
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


# Rejestracja
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    forml = LoginForm()

    if form.validate_on_submit():
        # Sprawdzenie, czy użytkownik już istnieje
        existing_user = Uzytkownik.query.filter_by(email=form.email.data).first()
        if existing_user:
            return jsonify({'status': 'error', 'message': 'Ten adres e-mail jest już zarejestrowany!'})

        try:
            # Tworzenie nowego użytkownika (bez hashowania hasła)
            user_to_create = Uzytkownik(
                email=form.email.data,
                password=form.password1.data,
                imie=form.imie.data,
                nazwisko=form.nazwisko.data,
                status='klient'
            )
            db.session.add(user_to_create)
            db.session.commit()

            # Weryfikacja zapisu
            new_user = Uzytkownik.query.filter_by(email=form.email.data).first()
            if new_user:
                login_user(new_user)
                return jsonify(
                    {'status': 'success', 'message': 'Rejestracja zakończona sukcesem!', 'redirect': url_for('home')})
            else:
                return jsonify({'status': 'error', 'message': 'Błąd: Użytkownik nie został zapisany w bazie.'})

        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Błąd bazy danych: {str(e)}'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Niespodziewany błąd: {str(e)}'})

    else:
        if request.method == 'POST':
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            return jsonify({'status': 'error', 'message': 'Walidacja formularza nie powiodła się.', 'errors': errors})

    return render_template('login.html', form=form, forml=forml, active_form='register')  # Dodaj active_form='register'


# Rezerwacja stolika
@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    if request.method == 'POST':
        stolik_id = request.form.get('stolik_id')
        data = request.form.get('data')
        stolik = Stolik.query.get(stolik_id)

        if stolik and stolik.wolny:
            try:
                rezerwacja = Rezerwacja(
                    id_user=current_user.id_user,
                    id_stolika=stolik_id,
                    data=datetime.strptime(data, '%Y-%m-%d %H:%M'),
                    oplacony=False
                )
                stolik.wolny = False
                db.session.add(rezerwacja)
                db.session.commit()
                return redirect(url_for('my_reservations'))
            except ValueError:
                return redirect(url_for('reserve', error='Nieprawidłowy format daty!'))
        else:
            return redirect(url_for('reserve', error='Stolik niedostępny.'))
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
        return redirect(url_for('home'))
    rezerwacje = Rezerwacja.query.all()
    stoliki = Stolik.query.all()
    return render_template('admin.html', rezerwacje=rezerwacje, stoliki=stoliki)


# Oznacz jako opłacone
@app.route('/mark_paid/<int:rezerwacja_id>')
@login_required
def mark_paid(rezerwacja_id):
    if current_user.status != 'admin':
        return redirect(url_for('home'))
    rezerwacja = Rezerwacja.query.get(rezerwacja_id)
    if rezerwacja:
        rezerwacja.oplacony = True
        db.session.commit()
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True)