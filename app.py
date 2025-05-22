import paypalrestsdk
from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFError, validate_csrf
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import Length, EqualTo, Email, DataRequired, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_
from datetime import datetime, timedelta
from uuid import uuid4
import paypalrestsdk

app = Flask(__name__)
app.config['SECRET_KEY'] = '1231231321'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:bazahaslo@localhost/system_rezerwacji'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Konfiguracja PayPal (zastąp kluczami z Twojego konta PayPal)
paypalrestsdk.configure({
    "mode": "sandbox",  # Użyj "live" dla produkcji
    "client_id": "ASjyr4bpQyd4KcNcc3k9XBmGXIxG_yG6Io22_wobTmAMJhtIYTjM7oH_nkdNqLxUrl-73WCePmEJIuP3",
    "client_secret": "EIBeFnUG6fqg1h6Ifd3vNRqUF5Xu88DLyuFTBGIsg7v_SKAE27BCw4ROSw7A_JKNMEnRmv5AjA1LOcXx"
})

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
    rezerwacje = db.relationship('Rezerwacja', backref='stolik', lazy=True)

class Rezerwacja(db.Model):
    __tablename__ = 'rezerwacje'
    id_rezerwacji = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('uzytkownicy.id_user'), nullable=False)
    id_stolika = db.Column(db.Integer, db.ForeignKey('stoliki.id_stolika'), nullable=False)
    data = db.Column(db.DateTime, nullable=False)
    data_konca = db.Column(db.DateTime, nullable=False)
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
        # Jawnie ustaw domyślne wartości, jeśli obiekt jest przekazany
        if 'obj' in kwargs and kwargs['obj']:
            obj = kwargs['obj']
            self.email.data = obj.email
            self.imie.data = obj.imie
            self.nazwisko.data = obj.nazwisko
            self.status.data = obj.status

    def validate_email(self, email):
        if self.user_id:
            existing_user = Uzytkownik.query.filter_by(email=email.data).filter(Uzytkownik.id_user != self.user_id).first()
            if existing_user:
                raise ValidationError('Ten adres e-mail jest już zarejestrowany.')

    def validate_status(self, status):
        if self.user_id:
            user = Uzytkownik.query.get(self.user_id)
            if user and user.status == 'admin' and status.data != 'admin':
                raise ValidationError('Użytkownik z rolą admina nie może zmienić statusu na klient.')
            if user and user.status != 'admin' and status.data == 'admin':
                raise ValidationError('Nie można zmienić statusu na admina bez odpowiednich uprawnień.')

@login_manager.user_loader
def load_user(user_id):
    return Uzytkownik.query.get(int(user_id))

# Endpointy - Strony Główne i Autoryzacja
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

            # Sprawdzanie rezerwacji na jutro
            tomorrow_start = datetime.now() + timedelta(days=1)
            tomorrow_start = tomorrow_start.replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

            rezerwacje_jutro = Rezerwacja.query.filter(
                Rezerwacja.id_user == attempted_user.id_user,
                Rezerwacja.data >= tomorrow_start,
                Rezerwacja.data <= tomorrow_end
            ).all()

            if rezerwacje_jutro:
                for r in rezerwacje_jutro:
                    messages.append({
                        'category': 'reminder',
                        'content': f"🔔 Przypomnienie: Masz rezerwację stolika nr {r.id_stolika} na {r.data.strftime('%Y-%m-%d %H:%M')}"
                    })

            if attempted_user.status == 'admin':
                uzytkownicy = Uzytkownik.query.all()
                formy = {u.id_user: UserForm(user_id=u.id_user, obj=u) for u in uzytkownicy}
                messages.append({'category': 'success', 'content': 'Zalogowano jako admin!'})
                return render_template('admin.html', rezerwacje=Rezerwacja.query.all(),
                           stoliki=Stolik.query.all(),
                           uzytkownicy=uzytkownicy,
                           messages=messages,
                           formy=formy)
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
            return jsonify({'status': 'error', 'message': 'Ten adres e-mail jest już zarejestrowany!'})
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
                return jsonify({'status': 'success', 'message': 'Rejestracja zakończona sukcesem!', 'redirect': url_for('home')})
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
    return render_template('login.html', form=form, forml=forml, active_form='register', messages=messages)

# Endpointy - Rezerwacje
@app.route('/get_available_tables', methods=['POST'])
@login_required
def get_available_tables():
    date_str = request.form.get('date')
    hour_str = request.form.get('hour')
    if not date_str or not hour_str:
        return jsonify({'status': 'error', 'message': 'Brak daty lub godziny!'}), 400

    try:
        hour_str = hour_str.zfill(2)
        datetime_str = f"{date_str} {hour_str}:00:00"
        selected_date = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        end_date = selected_date.replace(hour=selected_date.hour + 2)
    except ValueError as e:
        return jsonify({'status': 'error', 'message': f'Nieprawidłowy format daty lub godziny! {str(e)}'}), 400

    all_tables = Stolik.query.all()
    overlapping_reservations = Rezerwacja.query.filter(
        Rezerwacja.id_stolika == Stolik.id_stolika,
        and_(
            Rezerwacja.data < end_date,
            Rezerwacja.data_konca > selected_date
        )
    ).all()

    reserved_table_ids = {res.id_stolika for res in overlapping_reservations}
    tables = [
        {
            'id_stolika': table.id_stolika,
            'ilosc_miejsc': table.ilosc_miejsc,
            'available': table.id_stolika not in reserved_table_ids
        }
        for table in all_tables
    ]

    return jsonify({'status': 'success', 'tables': tables})

@app.route('/reserve', methods=['GET', 'POST'])
@login_required
def reserve():
    if request.method == 'POST':
        stolik_id = request.form.get('stolik_id')
        date_str = request.form.get('date')
        hour_str = request.form.get('hour')

        if not stolik_id or not date_str or not hour_str:
            return jsonify({'status': 'error', 'message': 'Brak wymaganych danych!'})

        try:
            hour_str = hour_str.zfill(2)
            datetime_str = f"{date_str} {hour_str}:00:00"
            selected_date = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            end_date = selected_date.replace(hour=selected_date.hour + 2)
        except ValueError as e:
            return jsonify({'status': 'error', 'message': f'Nieprawidłowy format daty lub godziny! {str(e)}'})

        stolik = Stolik.query.get(stolik_id)
        if not stolik:
            return jsonify({'status': 'error', 'message': 'Stolik nie istnieje!'})

        overlapping_reservations = Rezerwacja.query.filter(
            Rezerwacja.id_stolika == stolik_id,
            and_(
                Rezerwacja.data < end_date,
                Rezerwacja.data_konca > selected_date
            )
        ).first()

        if overlapping_reservations:
            return jsonify({'status': 'error', 'message': 'Stolik jest już zarezerwowany w tym czasie!'})

        try:
            rezerwacja = Rezerwacja(
                id_user=current_user.id_user,
                id_stolika=stolik_id,
                data=selected_date,
                data_konca=end_date,
                oplacony=False
            )
            db.session.add(rezerwacja)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Rezerwacja zakończona sukcesem!', 'redirect': url_for('my_reservations')})
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'Błąd bazy danych: {str(e)}'})

    messages = []
    now = datetime.now()
    return render_template('reserve.html', messages=messages, now=now)

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
        db.session.delete(rezerwacja)
        db.session.commit()
        messages.append({'category': 'success', 'content': 'Rezerwacja została anulowana!'})
    except SQLAlchemyError as e:
        db.session.rollback()
        messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})
    return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)
@app.route('/pay_reservation/<int:rezerwacja_id>')
@login_required
def pay_reservation(rezerwacja_id):
    messages = []
    rezerwacja = Rezerwacja.query.get_or_404(rezerwacja_id)

    if rezerwacja.id_user != current_user.id_user:
        messages.append({'category': 'error', 'content': 'Nie masz uprawnień do opłacenia tej rezerwacji!'})
        return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)

    if rezerwacja.oplacony:
        messages.append({'category': 'error', 'content': 'Ta rezerwacja jest już opłacona!'})
        return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)

    try:
        # Tworzenie płatności PayPal
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [{
                "amount": {
                    "total": "0.01",
                    "currency": "PLN"
                },
                "description": f'Rezerwacja stolika {rezerwacja.id_stolika} na {rezerwacja.data.strftime("%Y-%m-%d %H:%M")}',
                "custom": str(rezerwacja.id_rezerwacji)
            }],
            "redirect_urls": {
                "return_url": url_for('payment_success', _external=True),
                "cancel_url": url_for('payment_cancel', _external=True)
            }
        })

        if payment.create():
            rezerwacja.payment_intent_id = payment.id
            db.session.commit()
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            messages.append({'category': 'error', 'content': 'Błąd podczas tworzenia płatności!'})
            db.session.rollback()
    except Exception as e:
        db.session.rollback()
        messages.append({'category': 'error', 'content': f'Błąd: {str(e)}'})

    return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)

@app.route('/payment_success')
@login_required
def payment_success():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')
    messages = []

    if payment_id and payer_id:
        payment = paypalrestsdk.Payment.find(payment_id)
        payment = paypalrestsdk.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            # Odczytaj ID rezerwacji z pola custom
            rezerwacja_id = payment['transactions'][0]['custom']
            rezerwacja = Rezerwacja.query.get(rezerwacja_id)

            if rezerwacja:
                rezerwacja.oplacony = True
                db.session.commit()
                messages.append(
                    {'category': 'success', 'content': 'Płatność została pomyślnie wykonana! Rezerwacja opłacona.'})
            else:
                messages.append({'category': 'error', 'content': 'Nie znaleziono rezerwacji o podanym ID!'})
        else:
            messages.append({'category': 'error', 'content': 'Błąd podczas finalizacji płatności!'})
    else:
        messages.append({'category': 'error', 'content': 'Brak wymaganych danych do finalizacji płatności!'})

    return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)

@app.route('/payment_cancel')
@login_required
def payment_cancel():
    messages = [{'category': 'error', 'content': 'Płatność została anulowana!'}]
    return render_template('my_reservations.html', rezerwacje=Rezerwacja.query.filter_by(id_user=current_user.id_user).all(), messages=messages)
# Endpointy - Panel Admina
@app.route('/admin')
@login_required
def admin():
    rezerwacje = Rezerwacja.query.all()
    stoliki = Stolik.query.all()
    uzytkownicy = Uzytkownik.query.all()
    formy = {u.id_user: UserForm(user_id=u.id_user, obj=u) for u in uzytkownicy}
    messages = []
    if current_user.status != 'admin':
        messages.append({'category': 'error', 'content': 'Brak uprawnień do panelu admina!'})
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)
    return render_template('admin.html', rezerwacje=rezerwacje, stoliki=stoliki, uzytkownicy=uzytkownicy, messages=messages, formy=formy)
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


from flask import request, jsonify, render_template, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.status != 'admin':
        messages = [{'category': 'error', 'content': 'Brak uprawnień do edycji użytkowników!'}]
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Brak uprawnień!'}), 403
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)

    user = Uzytkownik.query.get_or_404(user_id)
    form = UserForm(user_id=user_id)

    if request.method == 'POST':
        print(f"Raw POST data: {request.form}")
        form = UserForm(user_id=user_id, formdata=request.form)
        print(f"Form data received: {form.data}")
        print(f"Form errors: {form.errors}")
        print(f"Form validated: {form.validate_on_submit()}")

    if form.validate_on_submit():
        try:
            existing_user = Uzytkownik.query.filter_by(email=form.email.data).filter(Uzytkownik.id_user != user_id).first()
            if existing_user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'status': 'error', 'message': 'Ten adres e-mail jest już zarejestrowany!'}), 400
                messages = [{'category': 'error', 'content': 'Ten adres e-mail jest już zarejestrowany!'}]
                return render_template('edit_user.html', form=form, user=user, messages=messages)

            print(f"Before update: User {user.id_user} - email={user.email}, imie={user.imie}, nazwisko={user.nazwisko}, status={user.status}")
            user.email = form.email.data
            user.imie = form.imie.data
            user.nazwisko = form.nazwisko.data
            if user.status != 'admin':
                user.status = form.status.data

            db.session.commit()
            print(f"After update: User {user.id_user} - email={user.email}, imie={user.imie}, nazwisko={user.nazwisko}, status={user.status}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'success', 'message': 'Dane użytkownika zostały zaktualizowane!', 'redirect': url_for('admin')})
            messages = [{'category': 'success', 'content': 'Dane użytkownika zostały zaktualizowane!'}]
            return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(),
                                  uzytkownicy=Uzytkownik.query.all(), messages=messages, formy={u.id_user: UserForm(user_id=u.id_user, obj=u) for u in Uzytkownik.query.all()})
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Database error: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'status': 'error', 'message': f'Błąd bazy danych: {str(e)}'}), 500
            messages = [{'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'}]
            return render_template('edit_user.html', form=form, user=user, messages=messages)
    else:
        if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
            print(f"Validation errors: {errors}")
            return jsonify({'status': 'error', 'message': 'Błąd walidacji', 'errors': errors}), 400
        if request.method == 'POST':
            messages = [{'category': 'error', 'content': f'Błąd walidacji: {form.errors}'}]
        else:
            messages = []
            # Wypełnij formularz danymi użytkownika dla GET
            form.email.data = user.email
            form.imie.data = user.imie
            form.nazwisko.data = user.nazwisko
            form.status.data = user.status

    return render_template('edit_user.html', form=form, user=user, messages=messages)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.status != 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Brak uprawnień!'}), 403
        messages = [{'category': 'error', 'content': 'Brak uprawnień do usuwania użytkowników!'}]
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)

    user = Uzytkownik.query.get_or_404(user_id)

    # Nie pozwalaj na usunięcie własnego konta
    if user.id_user == current_user.id_user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Nie możesz usunąć własnego konta!'}), 400
        messages = [{'category': 'error', 'content': 'Nie możesz usunąć własnego konta!'}]
        return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(),
                               uzytkownicy=Uzytkownik.query.all(), messages=messages,
                               formy={u.id_user: UserForm(user_id=u.id_user, obj=u) for u in Uzytkownik.query.all()})

    try:
        # Weryfikacja tokenu CSRF
        csrf_token = request.json.get('csrf_token')
        validate_csrf(csrf_token)

        print(f"Deleting user {user.id_user} - email={user.email}")
        db.session.delete(user)
        db.session.commit()
        print(f"User {user.id_user} deleted successfully")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(
                {'status': 'success', 'message': 'Użytkownik został usunięty!', 'redirect': url_for('admin')})
        messages = [{'category': 'success', 'content': 'Użytkownik został usunięty!'}]
        return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(),
                               uzytkownicy=Uzytkownik.query.all(), messages=messages,
                               formy={u.id_user: UserForm(user_id=u.id_user, obj=u) for u in Uzytkownik.query.all()})
    except CSRFError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Nieprawidłowy token CSRF!'}), 400
        messages = [{'category': 'error', 'content': 'Nieprawidłowy token CSRF!'}]
        return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(),
                               uzytkownicy=Uzytkownik.query.all(), messages=messages,
                               formy={u.id_user: UserForm(user_id=u.id_user, obj=u) for u in Uzytkownik.query.all()})
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': f'Błąd bazy danych: {str(e)}'}), 500
        messages = [{'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'}]
        return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(),
                               uzytkownicy=Uzytkownik.query.all(), messages=messages,
                               formy={u.id_user: UserForm(user_id=u.id_user, obj=u) for u in Uzytkownik.query.all()})
# Endpointy - Zarządzanie Stolikami w Panelu Admina
@app.route('/admin/get_table_reservations/<int:table_id>', methods=['GET'])
@login_required
def get_table_reservations(table_id):
    if current_user.status != 'admin':
        return jsonify({'status': 'error', 'message': 'Brak uprawnień!'}), 403

    reservations = Rezerwacja.query.filter_by(id_stolika=table_id).all()
    reservations_data = [
        {
            'id_user': res.id_user,
            'data': res.data.strftime('%Y-%m-%d %H:%M'),
            'oplacony': res.oplacony
        }
        for res in reservations
    ]
    return jsonify({'status': 'success', 'reservations': reservations_data})

@app.route('/admin/edit_table', methods=['POST'])
@login_required
def edit_table():
    if current_user.status != 'admin':
        return jsonify({'status': 'error', 'message': 'Brak uprawnień!'}), 403

    table_id = request.form.get('table_id')
    seats = request.form.get('seats')

    if not table_id or not seats:
        return jsonify({'status': 'error', 'message': 'Brak wymaganych danych!'})

    try:
        seats = int(seats)
        if seats < 1:
            return jsonify({'status': 'error', 'message': 'Liczba miejsc musi być większa od 0!'})

        table = Stolik.query.get(table_id)
        if not table:
            return jsonify({'status': 'error', 'message': 'Stolik nie istnieje!'})

        table.ilosc_miejsc = seats
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Liczba miejsc została zaktualizowana!', 'redirect': url_for('admin')})
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Liczba miejsc musi być liczbą!'})
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Błąd bazy danych: {str(e)}'})

@app.route('/admin/delete_table/<int:table_id>', methods=['POST'])
@login_required
def delete_table(table_id):
    messages = []
    if current_user.status != 'admin':
        messages.append({'category': 'error', 'content': 'Brak uprawnień!'})
        return render_template('home.html', user=current_user, stoliki=Stolik.query.all(), messages=messages)

    table = Stolik.query.get_or_404(table_id)
    try:
        Rezerwacja.query.filter_by(id_stolika=table_id).delete()
        db.session.delete(table)
        db.session.commit()
        messages.append({'category': 'success', 'content': f'Stolik {table_id} został usunięty!'})
    except SQLAlchemyError as e:
        db.session.rollback()
        messages.append({'category': 'error', 'content': f'Błąd bazy danych: {str(e)}'})

    return render_template('admin.html', rezerwacje=Rezerwacja.query.all(), stoliki=Stolik.query.all(), uzytkownicy=Uzytkownik.query.all(), messages=messages)

if __name__ == '__main__':
    app.run(debug=True)