from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import Length, EqualTo, Email, DataRequired, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4

app = Flask(__name__)
app.config['SECRET_KEY'] = '1231231321'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:bazahaslo@localhost/system_rezerwacji'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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
    rezerwacje = db.relationship('Rezerwacja', backref='stolik', lazy=True)

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

class UserForm(FlaskForm):
    email = StringField(label='Email', validators=[Length(min=2, max=100), DataRequired(), Email()])
    imie = StringField(label='Imię', validators=[Length(min=3, max=50), DataRequired()])
    nazwisko = StringField(label='Nazwisko', validators=[Length(min=3, max=50), DataRequired()])
    status = SelectField(label='Status', choices=[('admin', 'Admin'), ('klient', 'Klient')], validators=[DataRequired()])
    submit = SubmitField(label='Zapisz')

    def __init__(self, user_id=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.user_id = user_id

    def validate_status(self, status):
        if self.user_id:
            user = Uzytkownik.query.get(self.user_id)
            if user and user.status == 'admin' and status.data != 'admin':
                raise ValidationError('Użytkownik z rolą admina nie może zmienić statusu na klient.')

@login_manager.user_loader
def load_user(user_id):
    return Uzytkownik.query.get(int(user_id))

# Endpointy
@app.route('/')
def home():
    messages = []
    return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)

@app.route('/login', methods=['GET', 'POST'])
def login():
    messages = []
    forml = LoginForm()
    form = RegisterForm()
    if forml.validate_on_submit():
        attempted_user = Uzytkownik.query.filter_by(email=forml.email.data).first()
        if attempted_user and attempted_user.password == forml.password.data:
            login_user(attempted_user)
            if attempted_user.status == 'admin':
                messages.append({'category': 'success', 'content': 'Zalogowano jako admin!'})
                return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(), uzytkownicy=Uzytkownik.query.all(), messages=messages)
            else:
                messages.append({'category': 'success', 'content': 'Zalogowano pomyślnie!'})
                return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
        else:
            messages.append({'category': 'error', 'content': 'Email lub hasło nieprawidłowe!'})
    return render_template('login.html', forml=forml, form=form, active_form='login', messages=messages)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    messages = [{'category': 'success', 'content': 'Wylogowano pomyślnie!'}]
    return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    messages = []
    form = RegisterForm()
    forml = LoginForm()
    if form.validate_on_submit():
        existing_user = Uzytkownik.query.filter_by(email=form.email.data).first()
        if existing_user:
            messages.append({'category': 'error', 'content': 'Ten adres e-mail jest już zarejestrowany!'})
            return render_template('login.html', form=form, forml=forml, active_form='register', messages=messages)
        try:
            user_to_create = Uzytkownik(
                email=form.email.data,
                password=form.password1.data,
                imie=form.imie.data,
                nazwisko=form.nazwisko.data,
                status='klient'
            )
            db.session.add(user_to_create)
            db.session.commit()
            new_user = Uzytkownik.query.filter_by(email=form.email.data).first()
            if new_user:
                login_user(new_user)
                messages.append({'category': 'success', 'content': 'Rejestracja zakończona sukcesem!'})
                return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
            else:
                messages.append({'category': 'error', 'content': 'Błąd: Użytkownik nie został zapisany w bazie.'})
        except SQLAlchemyError as e:
            db.session.rollback()
            messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})
        except Exception as e:
            db.session.rollback()
            messages.append({'category': 'error', 'content': f'Niespodziewany błąd: {str(e)}'})
    return render_template('login.html', form=form, forml=forml, active_form='register', messages=messages)

@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    messages = []
    if request.method == 'POST':
        stolik_id = request.form.get('stolik_id')
        data = request.form.get('data')
        stolik = Stolik.query.get(stolik_id)
        if stolik and stolik.wolny:
            try:
                rezerwacja = Rezerwacja(
                    id_user=current_user.id_user,
                    id_stolika=stolik_id,
                    data=datetime.strptime(data, '%Y-%m-%dT%H:%M'),
                    oplacony=False
                )
                stolik.wolny = False
                db.session.add(rezerwacja)
                db.session.commit()
                messages.append({'category': 'success', 'content': 'Rezerwacja zakończona sukcesem!'})
                return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)
            except ValueError:
                messages.append({'category': 'error', 'content': 'Nieprawidłowy format daty!'})
            except SQLAlchemyError as e:
                db.session.rollback()
                messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})
        else:
            messages.append({'category': 'error', 'content': 'Stolik niedostępny.'})
    stoliki = Stolik.query.filter_by(wolny=True).all()
    return render_template('reserve.html', stoliki=stoliki, messages=messages)

@app.route('/my_reservations')
@login_required
def my_reservations():
    messages = []
    rezerwacje = Rezerwacja.query.filter_by(id_user=current_user.id_user).all()
    return render_template('my_reservations.html', rezerwacje=rezerwacje, messages=messages)

@app.route('/cancel_reservation/<int:rezerwacja_id>', methods=['POST'])
@login_required
def cancel_reservation(rezerwacja_id):
    messages = []
    rezerwacja = Rezerwacja.query.get_or_404(rezerwacja_id)
    if rezerwacja.id_user != current_user.id_user:
        messages.append({'category': 'error', 'content': 'Nie masz uprawnień do anulowania tej rezerwacji!'})
        return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)
    if rezerwacja.oplacony:
        messages.append({'category': 'error', 'content': 'Nie można anulować opłaconej rezerwacji!'})
        return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)
    try:
        stolik = Stolik.query.get(rezerwacja.id_stolika)
        stolik.wolny = True
        db.session.delete(rezerwacja)
        db.session.commit()
        messages.append({'category': 'success', 'content': 'Rezerwacja została anulowana!'})
    except SQLAlchemyError as e:
        db.session.rollback()
        messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})
    return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)

@app.route('/admin')
@login_required
def admin():
    messages = []
    if current_user.status != 'admin':
        messages.append({'category': 'error', 'content': 'Brak uprawnień do panelu admina!'})
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
    rezerwacje = Rezerwacja.query.all()
    stoliki = Stolik.query.all()
    uzytkownicy = Uzytkownik.query.all()
    return render_template('admin.html', rezerwacje=rezerwacje, stoliki=stoliki, uzytkownicy=uzytkownicy, messages=messages)

@app.route('/mark_paid/<int:rezerwacja_id>')
@login_required
def mark_paid(rezerwacja_id):
    messages = []
    if current_user.status != 'admin':
        messages.append({'category': 'error', 'content': 'Brak uprawnień!'})
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
    rezerwacja = Rezerwacja.query.get(rezerwacja_id)
    if rezerwacja:
        rezerwacja.oplacony = True
        db.session.commit()
        messages.append({'category': 'success', 'content': 'Rezerwacja oznaczona jako opłacona!'})
    else:
        messages.append({'category': 'error', 'content': 'Rezerwacja nie istnieje!'})
    return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(), uzytkownicy=Uzytkownik.query.all(), messages=messages)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    messages = []
    if current_user.status != 'admin':
        messages.append({'category': 'error', 'content': 'Brak uprawnień!'})
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
    user = Uzytkownik.query.get_or_404(user_id)
    form = UserForm(user_id=user_id, obj=user)
    if form.validate_on_submit():
        try:
            existing_user = Uzytkownik.query.filter_by(email=form.email.data).filter(Uzytkownik.id_user != user_id).first()
            if existing_user:
                messages.append({'category': 'error', 'content': 'Ten adres e-mail jest już zarejestrowany!'})
                return render_template('edit_user.html', form=form, user=user, messages=messages)
            user.email = form.email.data
            user.imie = form.imie.data
            user.nazwisko = form.nazwisko.data
            user.status = form.status.data
            db.session.commit()
            messages.append({'category': 'success', 'content': 'Dane użytkownika zostały zaktualizowane!'})
            return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(), uzytkownicy=Uzytkownik.query.all(), messages=messages)
        except SQLAlchemyError as e:
            db.session.rollback()
            messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})
    return render_template('edit_user.html', form=form, user=user, messages=messages)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    messages = []
    if current_user.status != 'admin':
        messages.append({'category': 'error', 'content': 'Brak uprawnień!'})
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
    user = Uzytkownik.query.get_or_404(user_id)
    if user.id_user == current_user.id_user:
        messages.append({'category': 'error', 'content': 'Nie możesz usunąć własnego konta!'})
        return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(), uzytkownicy=Uzytkownik.query.all(), messages=messages)
    try:
        Rezerwacja.query.filter_by(id_user=user_id).delete()
        db.session.delete(user)
        db.session.commit()
        messages.append({'category': 'success', 'content': f'Użytkownik {user.email} został usunięty!'})
    except SQLAlchemyError as e:
        db.session.rollback()
        messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})
    return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(), uzytkownicy=Uzytkownik.query.all(), messages=messages)

if __name__ == '__main__':
    app.run(debug=True)