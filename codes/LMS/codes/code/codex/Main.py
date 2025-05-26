from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
DATABASE = 'students.db'

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                id_number TEXT UNIQUE NOT NULL,
                school_name TEXT NOT NULL,
                standard TEXT NOT NULL
            )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course TEXT,
            status TEXT,
            UNIQUE(student_id, course),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
);

''')


# @app.route('/')
# def home():
#     return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if data['password'] != data['confirm_password']:
            flash("Passwords do not match!", 'danger')
            return render_template('register.html')

        hashed_pw = generate_password_hash(data['password'])

        try:
            with sqlite3.connect(DATABASE) as conn:
                conn.execute('''
                    INSERT INTO students 
                    (first_name, last_name, phone, email, password, id_number, school_name, standard)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['first_name'], data['last_name'], data['phone'],
                    data['email'], hashed_pw, data['id_number'],
                    data['school_name'], data['standard']
                ))
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email or ID number already registered!', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect(DATABASE) as conn:
            cur = conn.execute('SELECT * FROM students WHERE email = ?', (email,))
            student = cur.fetchone()
            
            if student and check_password_hash(student[5], password):
                session['student'] = {
    'id': student[0],
    'first_name': student[1],
    'last_name': student[2],
    'phone': student[3],                # ✅ Added phone
    'email': student[4],
    'id_number': student[6],
    'school_name': student[7],         # ✅ Added school_name
    'standard': student[8]
}
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password!', 'danger')
    return render_template('login.html')







@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.execute('SELECT * FROM students WHERE email = ?', (email,))
            user = cur.fetchone()
            if user:
                session['reset_email'] = email
                flash('Account found! Please set your new password.', 'success')
                return redirect(url_for('reset_password'))
            else:
                flash('Email not found in our records.', 'danger')
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('reset_password.html')

        hashed_pw = generate_password_hash(new_password)

        with sqlite3.connect(DATABASE) as conn:
            conn.execute('UPDATE students SET password = ? WHERE email = ?', (hashed_pw, session['reset_email']))
            conn.commit()

        session.pop('reset_email', None)
        flash('Password reset successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')



@app.route('/dashboard')
def dashboard():
    if 'student' not in session:
        return redirect(url_for('login'))

    student_id = session['student']['id']
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute('''
            SELECT date, course, status 
            FROM attendance 
            WHERE student_id = ? 
            ORDER BY date DESC
        ''', (student_id,))
        attendance_records = [
            {'date': row[0], 'subject': row[1], 'status': row[2]} for row in cur.fetchall()
        ]

    return render_template("dashboard.html", student=session['student'], attendance_records=attendance_records)

@app.route('/')
def home_page():
    return render_template('home.html')

@app.route('/puzzle')
def puzzle():
    return render_template('puzzle.html')


@app.route('/home_pages')
def home_pages():
    if 'student' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', student=session['student'])

@app.route('/courses')
def courses():
    if 'student' not in session:
        return redirect(url_for('login'))
    return render_template('courses.html', student=session['student'])






@app.route('/tutorials/html')
def tutorial_html():
    if 'student' not in session:
        return redirect(url_for('login'))

    student_id = session['student']['id']
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute('''
            SELECT course, status
            FROM attendance
            WHERE student_id = ?
        ''', (student_id,))
        completed_courses = [row[0] for row in cur.fetchall() if row[1] == 'Present']

    return render_template(
        'tutorial_html.html',
        student=session['student'],
        completed_courses=completed_courses
    )


@app.route('/tutorials/css')
def tutorial_css():
    if 'student' not in session:
        return redirect(url_for('login'))

    student_id = session['student']['id']
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.execute('''
            SELECT course, status
            FROM attendance
            WHERE student_id = ?
        ''', (student_id,))
        completed_courses = [row[0] for row in cur.fetchall() if row[1] == 'Present']
        print(completed_courses)

    return render_template(
        'tutorial_css.html',
        student=session['student'],
        completed_courses=completed_courses
    )

@app.route('/tutorials/javascript')
def tutorial_js():
    return render_template('tutorial_js.html')


@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    if 'student' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    data = request.json
    course = data.get('course')
    status = data.get('status', 'Present')

    if not course:
        return jsonify({'status': 'error', 'message': 'Course is required'}), 400

    student_id = session['student']['id']

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()

            # Check if already marked
            cursor.execute('''
                SELECT 1 FROM attendance WHERE student_id = ? AND course = ?
            ''', (student_id, course))
            if cursor.fetchone():
                return jsonify({'status': 'error', 'message': 'Attendance already marked for this course'}), 409

            # Insert attendance
            cursor.execute('''
                INSERT INTO attendance (student_id, course, status)
                VALUES (?, ?, ?)
            ''', (student_id, course, status))
            conn.commit()

        return jsonify({'status': 'success', 'message': 'Attendance marked'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500




########################################
from flask import Flask, render_template, request, redirect, session, url_for
import google.generativeai as genai
import re

# API/SkillSet.py
from flask import Blueprint, render_template

# # Create a Blueprint for SkillSet
# skillset_blueprint = Blueprint('skillset', __name__)

# Configure Gemini API
genai.configure(api_key="AIzaSyClwCo8aIpV8gieeDQ5HsjiASODhGkxt-0")

# Model configuration
generation_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="Generate 25 MCQs based on skill set. Each question must have options (a-d) and clearly state the correct answer like 'Answer: b'"
)

@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        skill_set = request.form['skill']
        chat = model.start_chat()
        response = chat.send_message(
            f"My skill set is: {skill_set}. Please create 25 MCQ questions with 4 options (a to d) and include the correct answer like 'Answer: b' after each question."
        )
        raw_quiz = response.text
        lines = raw_quiz.splitlines()

        questions = []
        answer_key = []
        current_question = None

        for line in lines:
            line = line.strip()
            if re.match(r"^\d+\.", line):
                if current_question:
                    questions.append(current_question)
                current_question = {"question": line, "options": []}
            elif re.match(r"^[a-dA-D]\)", line):
                if current_question:
                    current_question["options"].append(line)
            elif line.lower().startswith("answer:"):
                answer = line.split(":")[1].strip().lower()
                answer_key.append(answer)

        if current_question:
            questions.append(current_question)

        session['questions'] = questions[:25]
        session['answer_key'] = answer_key[:25]
        session['user_answers'] = []
        session['current_q'] = 0

        return redirect(url_for('quiz'))

    return render_template('skill_index.html')


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'questions' not in session or 'current_q' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        answer = request.form.get('answer', '').lower()
        if answer in ['a', 'b', 'c', 'd']:
            session['user_answers'].append(answer)
            session['current_q'] += 1

    current_q_index = session['current_q']
    if current_q_index >= len(session['questions']):
        return redirect(url_for('result'))

    question = session['questions'][current_q_index]
    return render_template('skill_quiz.html', index=current_q_index + 1, question=question)


@app.route('/result')
def result():
    questions = session.get('questions', [])
    user_answers = session.get('user_answers', [])
    answer_key = session.get('answer_key', [])
    score = 0
    results = []

    for i, (user, correct) in enumerate(zip(user_answers, answer_key)):
        is_correct = user == correct
        if is_correct:
            score += 1
        results.append({
            'q_num': i + 1,
            'your_answer': user,
            'correct_answer': correct,
            'is_correct': is_correct
        })

    return render_template('skill_result.html', results=results, score=score, total=len(questions))




##########################################

@app.route('/projects')
def projects():
    return render_template('projects.html')


@app.route('/services/hosting')
def hosting():
    return render_template('hosting.html')

@app.route('/services/certification', methods=['GET', 'POST'])
def certification():
    if request.method == 'POST':
        student_name = request.form.get('student_name')
        course_name = request.form.get('course_name')
        return render_template('certificate_display.html', student_name=student_name, course_name=course_name)
    return render_template('certification.html')



@app.route('/mathematics')
def math_page():
    return render_template('math.html')

@app.route('/physics')
def physics_page():
    return render_template('physics.html')

@app.route('/chemistry')
def chemistry_page():
    return render_template('chemistry.html')

@app.route('/biology')
def biology_page():
    return render_template('biology.html')
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))



###################################
import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

# Configure API key for Google Generative AI
genai.configure(api_key="AIzaSyClwCo8aIpV8gieeDQ5HsjiASODhGkxt-0")

# Create the model with configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction="student tutoring\nFor example, if I ask 'Explain Pythagoras' Theorem', it should respond with a clear explanation like 'The Pythagorean theorem states that in a right-angled triangle, the square of the length of the hypotenuse is equal to the sum of the squares of the lengths of the other two sides.'\n\n",
)

# Start Flask app

# Start a new chat session
chat_session = model.start_chat(
    history=[
        {
            "role": "user",
            "parts": [
                "Hi\n",  # Student greeting the tutor
            ],
        },
        {
            "role": "model",
            "parts": [
                "Hello! How can I assist you with your studies today?\n",  # Model response as a tutor
            ],
        },
    ]
)


# Route for handling user input and AI response
@app.route('/ask', methods=['POST'])
def ask():
    # Get the user input from the form
    user_input = request.form['user_input']
    
    if user_input.lower() == 'exit':
        return jsonify({"response": "Exiting chat... Goodbye!"})
    
    # Send the user's message to the model
    response = chat_session.send_message(user_input)
    
    # Return the model's response
    return jsonify({"response": response.text})


########################################
# Home route
@app.route('/chat')
def chat():
    return render_template('chat.html')

if __name__ == '__main__':
    # if not os.path.exists(DATABASE):
    init_db()
    app.run(debug=True)
