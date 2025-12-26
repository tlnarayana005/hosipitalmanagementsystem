from flask import Flask, render_template, session
from models import db, User, Doctor, Patient
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-for-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Import routes
from routes import admin, doctor, patient, api, shared

# Register blueprints
app.register_blueprint(shared.bp)
app.register_blueprint(admin.bp, url_prefix='/admin')
app.register_blueprint(doctor.bp, url_prefix='/doctor')
app.register_blueprint(patient.bp, url_prefix='/patient')
app.register_blueprint(api.bp, url_prefix='/api')

@app.context_processor
def inject_notifications():
    """Make notification count available to all templates"""
    if 'user_id' in session:
        from utils.notifications import get_unread_count
        return {'unread_count': get_unread_count(session['user_id'])}
    return {'unread_count': 0}

@app.route('/')
def index():
    from flask import redirect, url_for
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif role == 'patient':
            return redirect(url_for('patient.dashboard'))
    return redirect(url_for('shared.login'))

def init_database():
    """Initialize database with tables and seed data"""
    with app.app_context():
        db.create_all()
        
        # Check if already initialized
        if User.query.first():
            return
        
        # Create admin
        admin = User(username='admin', email='admin@hospital.com', phone='1234567890', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create doctors
        doctors_data = [
            {'username': 'dr_smith', 'email': 'smith@hospital.com', 'phone': '1111111111', 
             'password': 'doctor123', 'specialization': 'Cardiology'},
            {'username': 'dr_jones', 'email': 'jones@hospital.com', 'phone': '2222222222',
             'password': 'doctor123', 'specialization': 'Neurology'},
            {'username': 'dr_brown', 'email': 'brown@hospital.com', 'phone': '3333333333',
             'password': 'doctor123', 'specialization': 'Pediatrics'}
        ]
        
        for doc_data in doctors_data:
            user = User(username=doc_data['username'], email=doc_data['email'], 
                       phone=doc_data['phone'], role='doctor')
            user.set_password(doc_data['password'])
            db.session.add(user)
            db.session.flush()
            
            doctor = Doctor(user_id=user.id, specialization=doc_data['specialization'])
            db.session.add(doctor)
        
        # Create patients
        patients_data = [
            {'username': 'patient1', 'email': 'patient1@email.com', 'phone': '4444444444',
             'password': 'patient123', 'medical_id': 'MED001'},
            {'username': 'patient2', 'email': 'patient2@email.com', 'phone': '5555555555',
             'password': 'patient123', 'medical_id': 'MED002'},
            {'username': 'patient3', 'email': 'patient3@email.com', 'phone': '6666666666',
             'password': 'patient123', 'medical_id': 'MED003'}
        ]
        
        for pat_data in patients_data:
            user = User(username=pat_data['username'], email=pat_data['email'],
                       phone=pat_data['phone'], role='patient')
            user.set_password(pat_data['password'])
            db.session.add(user)
            db.session.flush()
            
            patient = Patient(user_id=user.id, medical_id=pat_data['medical_id'])
            db.session.add(patient)
        
        db.session.commit()
        print('Database initialized with seed data')

if __name__ == '__main__':
    init_database()
    app.run(debug=True)
