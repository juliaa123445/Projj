from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Przykładowa baza użytkowników
users_db = {
    'admin': {'password': 'adminpass', 'role': 'admin'},
    'user1': {'password': 'userpass', 'role': 'user'}
}

surveys_db = {}

def is_admin():
    return session.get('username') and users_db.get(session['username'], {}).get('role') == 'admin'

@app.route('/', methods=['GET', 'POST'])
def main():
    username_valid = None  # Brak błędu na starcie

    if request.method == 'POST':
        if 'login' in request.form:
            # Logowanie
            username = request.form['username']
            password = request.form['password']

            if username not in users_db:
                flash('User does not exist. Please register first.', 'error')
            elif users_db[username]['password'] != password:
                flash('Incorrect password. Please try again.', 'error')
            else:
                session['username'] = username
                return redirect(url_for('create_survey') if is_admin() else url_for('vote'))

        elif 'register' in request.form:
            # Rejestracja
            username = request.form.get('username')
            password = request.form.get('password')

            if username in users_db:
                flash('Username already exists. Please choose a different username.', 'error')
            else:
                users_db[username] = {'password': password, 'role': 'user'}
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('main'))

    return render_template('main.html', username_valid=username_valid)


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
        # Retrieve form data
        title = request.form['title']
        description = request.form['description']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        scale = int(request.form['scale'])

        try:
            # Convert start and end times to datetime objects
            start_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
            end_time_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            current_time = datetime.now()

            # Check if end time is valid
            if end_time_dt <= start_time_dt or end_time_dt <= current_time:
                flash('Invalid end time. Please ensure it is after the start time and in the future.', 'error')
                return redirect(url_for('create_survey'))

            # Define a new survey entry in surveys_db with a unique ID
            survey_id = len(surveys_db) + 1
            surveys_db[survey_id] = {
                'title': title,
                'description': description,
                'start_time': start_time_dt,
                'end_time': end_time_dt,
                'scale': scale,
                'votes': {i: 0 for i in range(1, scale + 1)},
                'voters': []  # Initialize the list for tracking voters
            }
            flash('Survey created successfully!', 'success')
            return redirect(url_for('create_survey'))
        except ValueError:
            flash('Invalid date or time format.', 'error')

    return render_template('create_survey.html', surveys=surveys_db)



# Strona głosowania
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'username' not in session:
        flash('Please log in to vote.', 'error')
        return redirect(url_for('main'))

    if request.method == 'POST':
        survey_id = int(request.form['survey_id'])
        score = int(request.form['score'])
        survey = surveys_db.get(survey_id)

        if survey and 1 <= score <= survey['scale']:
            # Debugging: print current survey's voter list
            print("Voters list before voting:", survey['voters'])
            print("Current user:", session['username'])

            # Check if user has already voted
            if session['username'] in survey['voters']:
                flash('You have already voted in this survey.', 'error')
            else:
                survey['votes'][score] += 1  # Count the vote
                survey['voters'].append(session['username'])  # Record the user as having voted
                flash('Your vote has been submitted!', 'success')

            # Debugging: print updated survey's voter list
            print("Voters list after voting:", survey['voters'])
        else:
            flash('Invalid vote. Please try again.', 'error')

    return render_template('vote.html', surveys=surveys_db)



# Generowanie raportu
@app.route('/report/<int:survey_id>')
def report(survey_id):
    if not is_admin():
        flash('Only admins can generate reports!', 'error')
        return redirect(url_for('main'))

    survey = surveys_db.get(survey_id)
    if not survey:
        flash('Survey not found!', 'error')
        return redirect(url_for('create_survey'))

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
