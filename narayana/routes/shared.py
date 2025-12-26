from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User, Patient
from datetime import datetime

bp = Blueprint('shared', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            elif user.role == 'patient':
                return redirect(url_for('patient.dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('shared/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        date_of_birth = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        address = request.form.get('address')
        emergency_contact = request.form.get('emergency_contact')
        blood_group = request.form.get('blood_group')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('shared/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('shared/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('shared/register.html')
        
        # Generate medical ID
        patient_count = Patient.query.count()
        medical_id = f'MED{str(patient_count + 1).zfill(6)}'
        
        # Create user
        user = User(
            username=username,
            email=email,
            phone=phone,
            role='patient',
            full_name=full_name,
            date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None,
            gender=gender,
            address=address
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Create patient profile
        patient = Patient(
            user_id=user.id,
            medical_id=medical_id,
            emergency_contact=emergency_contact,
            blood_group=blood_group
        )
        db.session.add(patient)
        db.session.commit()
        
        flash('Registration successful! Please login with your credentials.', 'success')
        return redirect(url_for('shared.login'))
    
    return render_template('shared/register.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('shared.login'))

@bp.route('/notifications')
def notifications():
    from utils.auth import login_required
    from models import Notification
    
    if 'user_id' not in session:
        return redirect(url_for('shared.login'))
    
    notifications = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).all()
    return render_template('shared/notifications.html', notifications=notifications)

@bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    from utils.notifications import mark_as_read
    
    if 'user_id' not in session:
        return redirect(url_for('shared.login'))
    
    mark_as_read(notification_id)
    return redirect(url_for('shared.notifications'))

@bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('shared.login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.email = request.form.get('email')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        # Update role-specific info
        if user.role == 'patient':
            user.patient_profile.emergency_contact = request.form.get('emergency_contact')
            user.patient_profile.blood_group = request.form.get('blood_group')
        elif user.role == 'doctor':
            user.doctor_profile.bio = request.form.get('bio')
            user.doctor_profile.qualifications = request.form.get('qualifications')
            user.doctor_profile.experience_years = request.form.get('experience_years')
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('shared.profile'))
    
    return render_template('shared/profile.html', user=user)
