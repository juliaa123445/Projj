from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Prosta baza danych w pamięci
users_db = {
    'admin': {'password': 'adminpass', 'role': 'admin'},  # Przykładowy użytkownik admin
    'user1': {'password': 'userpass', 'role': 'user'}  # Przykładowy użytkownik zwykły
}

surveys_db = {}  # Przechowuje ankiety (survey_id: {title, description, start_time, end_time, scale, votes})


# Funkcja do sprawdzania, czy użytkownik jest adminem
def is_admin():
    return session.get('username') and users_db.get(session['username'], {}).get('role') == 'admin'


# Główna strona, która pokazuje ankiety
@app.route('/')
def main():
    if 'username' in session:
        return render_template('main.html', username=session['username'], surveys=surveys_db)
    return render_template('main.html', surveys=surveys_db)


# Logowanie
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users_db and users_db[username]['password'] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('main'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')


# Rejestracja nowego użytkownika
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = 'admin' in request.form  # Sprawdza, czy pole "admin" jest zaznaczone

        if username in users_db:
            flash('User already exists', 'error')
        else:
            role = 'admin' if is_admin else 'user'
            users_db[username] = {'password': password, 'role': role}
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


# Wylogowanie
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main'))


# Tworzenie ankiety (tylko dla admina)
@app.route('/create_survey', methods=['GET', 'POST'])
def create_survey():
    if not is_admin():
        flash('Only admins can create surveys!', 'error')
        return redirect(url_for('main'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        scale = int(request.form['scale'])

        try:
            start_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
            end_time_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            current_time = datetime.now()

            # Sprawdzenie, czy data zakończenia nie jest wcześniejsza niż data rozpoczęcia
            if end_time_dt <= start_time_dt:
                flash('Error: End time must be later than start time. Please select a valid end date.', 'error')
                return redirect(url_for('create_survey'))

            # Sprawdzenie, czy data zakończenia nie jest w przeszłości
            if end_time_dt <= current_time:
                flash('Error: End time must be in the future. Please select a future end date.', 'error')
                return redirect(url_for('create_survey'))

            if title and start_time and end_time and scale:
                survey_id = len(surveys_db) + 1
                surveys_db[survey_id] = {
                    'title': title,
                    'description': description,
                    'start_time': start_time_dt,
                    'end_time': end_time_dt,
                    'scale': scale,
                    'votes': {i: 0 for i in range(1, scale + 1)}
                }
                flash('Survey created successfully!', 'success')
                return redirect(url_for('main'))
            else:
                flash('Please provide all required information!', 'error')

        except ValueError:
            flash('Invalid date or time format. Please use the correct format.', 'error')
            return redirect(url_for('create_survey'))

    return render_template('create_survey.html')


@app.route('/vote/<int:survey_id>', methods=['POST'])
def vote(survey_id):
    if 'username' not in session:
        flash('Please log in to vote!', 'error')
        return redirect(url_for('login'))

    survey = surveys_db.get(survey_id)
    if not survey:
        flash('Survey not found!', 'error')
        return redirect(url_for('main'))

    current_time = datetime.now()
    if not (survey['start_time'] <= current_time <= survey['end_time']):
        flash('This survey is not active!', 'error')
        return redirect(url_for('main'))

    try:
        score = int(request.form['score'])
        if score < 1 or score > survey['scale']:
            flash('Invalid score!', 'error')
            return redirect(url_for('main'))
        survey['votes'][score] += 1

        # Dodanie ankiety do listy ankiet, w których użytkownik brał udział
        if 'participated_surveys' not in session:
            session['participated_surveys'] = []

        if survey_id not in session['participated_surveys']:
            session['participated_surveys'].append(survey_id)
            session.modified = True

        flash('Your vote has been recorded!', 'success')
    except ValueError:
        flash('Invalid input!', 'error')

    return redirect(url_for('main'))


# Generowanie raportu
@app.route('/report/<int:survey_id>')
def report(survey_id):
    if not is_admin():
        flash('Only admins can generate reports!', 'error')
        return redirect(url_for('main'))

    survey = surveys_db.get(survey_id)
    if not survey:
        flash('Survey not found!', 'error')
        return redirect(url_for('main'))

    # Generowanie raportu tekstowego
    report_data = f"Survey Report: {survey['title']}\n\nDescription: {survey['description']}\n\n"
    report_data += f"Time: {survey['start_time']} to {survey['end_time']}\n\nScale: 1-{survey['scale']}\n\n"
    report_data += "Results:\n"
    for score, count in survey['votes'].items():
        report_data += f"Score {score}: {count} votes\n"

    response = make_response(report_data)
    response.headers["Content-Disposition"] = f"attachment; filename=report_{survey_id}.txt"
    return response


# Endpoint API do zwracania danych dla wykresu
@app.route('/survey_data')
def survey_data():
    labels = []
    votes = []

    for survey_id, survey in surveys_db.items():
        labels.append(f"{survey['title']} (Ends: {survey['end_time'].strftime('%H:%M')})")
        total_votes = sum(survey['votes'].values())
        votes.append(total_votes)

    return jsonify(labels=labels, votes=votes)


# Dodanie funkcji pomocniczej do kontekstu szablonów
@app.context_processor
def inject_is_admin():
    return dict(is_admin=is_admin)


if __name__ == '__main__':
    app.run(debug=True)
