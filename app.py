from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    option1 = db.Column(db.String(100), nullable=False)
    option2 = db.Column(db.String(100), nullable=False)
    option3 = db.Column(db.String(100), nullable=False)
    option4 = db.Column(db.String(100), nullable=False)
    correct_option = db.Column(db.String(100), nullable=False)

@app.route('/')
def home():
    city = request.args.get('city', 'New York')
    weather_data = get_weather(city)
    return render_template('home.html', weather_data=weather_data, city=city)

def get_weather(city):
    api_key = 'your_weather_api_key'
    url = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&units=metric&appid={api_key}'
    response = requests.get(url).json()
    forecast = []
    if response.get('list'):
        for i in [0, 8, 16]:  # Today, Tomorrow, Day after Tomorrow
            forecast.append({
                'date': response['list'][i]['dt_txt'].split()[0],
                'temp_day': response['list'][i]['main']['temp'],
                'temp_night': response['list'][i+4]['main']['temp'] if i+4 < len(response['list']) else 'N/A'
            })
    return forecast

# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         hashed_password = generate_password_hash(password, method='sha256')
#         user = User(username=username, password=hashed_password)
#         db.session.add(user)
#         db.session.commit()
#         return redirect(url_for('login'))
#     return render_template('register.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Use pbkdf2:sha256 for password hashing
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Store user session
            session['answered_questions'] = []  # Reset answered questions
            print("Session Data:", session)  # Debugging
            return redirect(url_for('quiz'))  # Redirect to quiz

    return render_template('login.html')


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if session is missing

    user = User.query.get(session['user_id'])
    questions = Question.query.all()

    if not questions:
        return "⚠️ No questions available. Please contact the admin."

    if 'answered_questions' not in session:
        session['answered_questions'] = []

    # Remove already answered questions
    remaining_questions = [q for q in questions if q.id not in session['answered_questions']]

    if not remaining_questions:
        return redirect(url_for('leaderboard'))  # Redirect if all questions are answered

    question = random.choice(remaining_questions)

    if request.method == 'POST':
        selected_option = request.form.get('option')  # Get user-selected option

        if selected_option and selected_option == question.correct_option:
            user.score += 10  # Increase score if correct
            db.session.commit()

        # Mark this question as answered
        session['answered_questions'].append(question.id)
        session.modified = True  # Ensure the session is updated

        return render_template('quiz.html', question=question, score=user.score)  # Stay on the same page with updated score

    return render_template('quiz.html', question=question, score=user.score)




@app.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.score.desc()).all()
    return render_template('leaderboard.html', users=users)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Make sure tables exist

        # Delete old questions first
        Question.query.delete()
        db.session.commit()

        # Insert new questions
        sample_questions = [
            Question(
                question="What is the primary purpose of using NumPy in AI development?",
                option1="To create user interfaces",
                option2="To store and manipulate large datasets efficiently",
                option3="To build deep learning models",
                option4="To visualize data",
                correct_option="To store and manipulate large datasets efficiently"
            ),
            Question(
                question="Which library is most commonly used for deep learning in Python?",
                option1="Pandas",
                option2="TensorFlow",
                option3="Matplotlib",
                option4="Flask",
                correct_option="TensorFlow"
            ),
            Question(
                question="What is the role of a loss function in training an AI model?",
                option1="To improve data visualization",
                option2="To monitor hardware performance",
                option3="To measure the difference between predicted and actual values",
                option4="To store training data",
                correct_option="To measure the difference between predicted and actual values"
            ),
            Question(
                question="Which step is necessary before training a machine learning model?",
                option1="To delete missing values randomly",
                option2="To preprocess and clean the data",
                option3="To run the model without data",
                option4="To ignore data distribution",
                correct_option="To preprocess and clean the data"
            )
        ]

        # Add the new questions
        for q in sample_questions:
            db.session.add(q)

        db.session.commit()


    app.run(debug=True)
