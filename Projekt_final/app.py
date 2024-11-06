from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator  # Używane do pełnych liczb na osiach
from models import db, User, Survey, Vote  # Importujemy modele z models.py

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Funkcje pomocnicze
def is_admin():
    """Sprawdza, czy użytkownik jest administratorem."""
    username = session.get('username')
    if not username:
        return False
    user = User.query.filter_by(username=username).first()
    return user is not None and user.role == 'admin'

# Trasa główna
@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        if 'login' in request.form:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()

            if user is None:
                flash('User does not exist. Please register first.', 'error')
            elif not user.check_password(password):
                flash('Incorrect password. Please try again.', 'error')
            else:
                session['username'] = username
                return redirect(url_for('create_survey') if user.role == 'admin' else url_for('vote'))

        elif 'register' in request.form:
            username = request.form.get('username')
            password = request.form.get('password')

            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please choose a different username.', 'error')
            else:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('main'))

    return render_template('main.html')

# Wylogowanie
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main'))

# Tworzenie ankiety
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
        scale = int(request.form['scale'])  # Maksymalny poziom skali

        try:
            start_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
            end_time_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")

            if end_time_dt <= start_time_dt:
                flash('Invalid end time. Please ensure it is after the start time.', 'error')
                return render_template('create_survey.html')

            survey = Survey(title=title, description=description, start_time=start_time_dt, end_time=end_time_dt, scale=scale)
            db.session.add(survey)
            db.session.commit()

            flash('Survey created successfully!', 'success')
            return redirect(url_for('create_survey'))
        except ValueError:
            flash('Invalid date or time format.', 'error')

    return render_template('create_survey.html', surveys=Survey.query.all())

# Głosowanie
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'username' not in session:
        flash('Please log in to vote.', 'error')
        return redirect(url_for('main'))

    user = User.query.filter_by(username=session['username']).first()
    if request.method == 'POST':
        survey_id = int(request.form['survey_id'])
        score = int(request.form['score'])
        survey = Survey.query.get(survey_id)

        if survey:
            if Vote.query.filter_by(user_id=user.id, survey_id=survey_id).first():
                flash('You have already voted in this survey.', 'error')
            else:
                vote = Vote(user_id=user.id, survey_id=survey_id, score=score)
                db.session.add(vote)
                db.session.commit()
                flash('Your vote has been submitted!', 'success')
        else:
            flash('Invalid survey.', 'error')

    return render_template('vote.html', surveys=Survey.query.all())

# Generowanie raportu PDF
@app.route('/report/<int:survey_id>')
def report(survey_id):
    if not is_admin():
        flash('Only admins can generate reports!', 'error')
        return redirect(url_for('main'))

    survey = Survey.query.get(survey_id)
    if not survey:
        flash('Survey not found!', 'error')
        return redirect(url_for('create_survey'))

    # Zliczanie głosów na każdym poziomie skali
    vote_counts = {i: 0 for i in range(1, survey.scale + 1)}
    all_votes = Vote.query.filter_by(survey_id=survey_id).all()
    for vote in all_votes:
        if 1 <= vote.score <= survey.scale:
            vote_counts[vote.score] += 1

    # Generowanie wykresu z pełnymi liczbami na osiach
    img = BytesIO()
    plt.figure()
    plt.bar(vote_counts.keys(), vote_counts.values())
    plt.xlabel('Skala Głosowania')
    plt.ylabel('Liczba Głosów')
    plt.title(f'Wyniki głosowania: {survey.title}')
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # Inicjalizacja bufora PDF
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Tytuł i opis ankiety
    elements.append(Paragraph(f"Raport głosowania: {survey.title}", styles['Title']))
    elements.append(Paragraph(f"Opis: {survey.description}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Lista użytkowników i ich głosów
    elements.append(Paragraph("Lista głosów:", styles['Heading2']))
    votes_table_data = [["Użytkownik", "Głos"]]
    for vote in all_votes:
        username = User.query.get(vote.user_id).username
        votes_table_data.append([username, vote.score])

    table = Table(votes_table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # Dodanie wykresu do raportu
    elements.append(Paragraph("Wykres głosów:", styles['Heading2']))
    elements.append(Image(img, width=400, height=200))

    # Generowanie PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    response = make_response(pdf_buffer.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=report_{survey_id}.pdf"
    response.headers["Content-Type"] = "application/pdf"
    return response


@app.route('/delete_survey/<int:survey_id>')
def delete_survey(survey_id):
    if not is_admin():
        flash('Only admins can delete surveys!', 'error')
        return redirect(url_for('main'))

    survey = Survey.query.get(survey_id)
    if survey:
        # Usuwanie powiązanych głosów
        Vote.query.filter_by(survey_id=survey.id).delete()
        db.session.delete(survey)
        db.session.commit()
        flash('Survey deleted successfully!', 'success')
    else:
        flash('Survey not found.', 'error')

    return redirect(url_for('create_survey'))


# API do głosów
@app.route('/api/votes')
def api_votes():
    data = []
    surveys = Survey.query.all()

    for survey in surveys:
        vote_counts = {i: 0 for i in range(1, survey.scale + 1)}
        votes = Vote.query.filter_by(survey_id=survey.id).all()
        for vote in votes:
            vote_counts[vote.score] += 1

        survey_data = {
            'survey_id': survey.id,
            'title': survey.title,
            'votes': [{'score': score, 'count': count} for score, count in vote_counts.items()]
        }
        data.append(survey_data)

    return jsonify(data)


# Uruchomienie aplikacji
if __name__ == '__main__':
    app.run(debug=True)
