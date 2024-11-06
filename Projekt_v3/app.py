from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User, Survey, Option, Vote
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
import matplotlib.pyplot as plt
from io import BytesIO
from models import db


app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)


def is_admin():
    """Check if the logged-in user is an admin."""
    username = session.get('username')
    if not username:
        return False
    user = User.query.filter_by(username=username).first()
    return user is not None and user.role == 'admin'


@app.route('/', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        if 'login' in request.form:
            # Logowanie
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
            # Rejestracja
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
    print(db.metadata.tables)  # This will list tables and their columns
    return render_template('main.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main'))


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
        scale = int(request.form['scale'])  # Number of options (2, 5, or 10)

        try:
            start_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M")
            end_time_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M")
            current_time = datetime.now()

            if end_time_dt <= start_time_dt or end_time_dt <= current_time:
                flash('Invalid end time. Please ensure it is after the start time and in the future.', 'error')
                return render_template('create_survey.html')

            # Save the survey with a fixed number of options
            survey = Survey(title=title, description=description, start_time=start_time_dt, end_time=end_time_dt, scale=scale)
            db.session.add(survey)
            db.session.commit()

            # Generate fixed options based on the scale
            for i in range(1, scale + 1):
                option = Option(position=i, survey_id=survey.id)
                db.session.add(option)
            db.session.commit()

            flash('Survey created successfully with predefined options!', 'success')
            return redirect(url_for('create_survey'))
        except ValueError:
            flash('Invalid date or time format.', 'error')
            return render_template('create_survey.html')

    return render_template('create_survey.html', surveys=Survey.query.all())



@app.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'username' not in session:
        flash('Please log in to vote.', 'error')
        return redirect(url_for('main'))

    user = User.query.filter_by(username=session['username']).first()
    if request.method == 'POST':
        survey_id = int(request.form['survey_id'])
        option_id = int(request.form['score'])
        survey = Survey.query.get(survey_id)

        if survey:
            current_time = datetime.now()
            if current_time < survey.start_time:
                flash(f"The survey will start on {survey.start_time}.", 'error')
            elif Vote.query.filter_by(user_id=user.id, survey_id=survey_id).first():
                flash('You have already voted in this survey.', 'error')
            else:
                vote = Vote(user_id=user.id, survey_id=survey_id, option_id=option_id)
                db.session.add(vote)
                db.session.commit()
                flash('Your vote has been submitted!', 'success')
        else:
            flash('Invalid survey.', 'error')

    return render_template('vote.html', surveys=Survey.query.all())


@app.route('/report/<int:survey_id>')
def report(survey_id):
    if not is_admin():
        flash('Only admins can generate reports!', 'error')
        return redirect(url_for('main'))

    survey = Survey.query.get(survey_id)
    if not survey:
        flash('Survey not found!', 'error')
        return redirect(url_for('create_survey'))

    # 1. Prepare vote summary and individual vote list
    options_results = []
    all_votes = Vote.query.filter_by(survey_id=survey_id).all()
    for option in survey.options:
        vote_count = Vote.query.filter_by(survey_id=survey.id, option_id=option.id).count()
        options_results.append((option.position, vote_count))

    votes_data = []
    for vote in all_votes:
        option = Option.query.get(vote.option_id)  # Retrieve the option safely
        if option:  # Check if option exists
            vote_info = [
                User.query.get(vote.user_id).username,
                option.position,
                vote.timestamp if hasattr(vote, 'timestamp') else "N/A"
            ]
        else:  # Handle missing options
            vote_info = [
                User.query.get(vote.user_id).username,
                "Unknown Option",
                vote.timestamp if hasattr(vote, 'timestamp') else "N/A"
            ]
        votes_data.append(vote_info)

    # 2. Create the time-based vote graph
    timestamps = [vote.timestamp for vote in all_votes if hasattr(vote, 'timestamp')]
    img = BytesIO()
    if timestamps:
        plt.figure()
        plt.hist(timestamps, bins=10)  # Adjust bins as needed
        plt.xlabel('Time')
        plt.ylabel('Number of Votes')
        plt.title('Votes Over Time')
        plt.savefig(img, format='png')
        img.seek(0)
        plt.close()
    img_path = img if timestamps else None

    # 3. Generate the PDF report
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Report title
    elements.append(Paragraph(f"Survey Report: {survey.title}", styles['Title']))
    elements.append(Paragraph(f"Description: {survey.description}", styles['Normal']))
    elements.append(Paragraph(f"Time: {survey.start_time} to {survey.end_time}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Results Summary
    elements.append(Paragraph("Results Summary:", styles['Heading2']))
    results_table_data = [["Option", "Votes"]] + options_results
    table = Table(results_table_data)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                               ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                               ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                               ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                               ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                               ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                               ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    # List of All Votes
    elements.append(Paragraph("All Votes:", styles['Heading2']))
    votes_table_data = [["Username", "Option", "Timestamp"]] + votes_data
    votes_table = Table(votes_table_data)
    votes_table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                     ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                     ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                     ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                     ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                     ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                     ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(votes_table)
    elements.append(Spacer(1, 12))

    # Votes Over Time Graph
    if img_path:
        elements.append(Paragraph("Votes Over Time:", styles['Heading2']))
        elements.append(Image(img_path, width=400, height=200))

    # Build PDF
    doc.build(elements)

    # Return PDF as a downloadable response
    pdf_buffer.seek(0)
    response = make_response(pdf_buffer.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=report_{survey_id}.pdf"
    response.headers["Content-Type"] = "application/pdf"
    return response



@app.route('/api/votes')
def api_votes():
    data = []
    surveys = Survey.query.all()

    for survey in surveys:
        for option in survey.options:
            vote_count = Vote.query.filter_by(survey_id=survey.id, option_id=option.id).count()
            data.append({
                'survey_id': survey.id,
                'score': option.position,
                'votes': vote_count
            })
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
