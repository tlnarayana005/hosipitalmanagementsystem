from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Doctor, Patient, Appointment, AuditLog
from utils.auth import role_required
from datetime import datetime, timedelta
from sqlalchemy import func

bp = Blueprint('admin', __name__)

@bp.route('/dashboard')
@role_required('admin')
def dashboard():
    # Get counts
    doctor_count = Doctor.query.count()
    patient_count = Patient.query.count()
    appointment_count = Appointment.query.count()
    
    # Get appointment trends (last 30 days)
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    appointments_by_date = db.session.query(
        Appointment.appointment_date,
        func.count(Appointment.id)
    ).filter(
        Appointment.appointment_date >= thirty_days_ago
    ).group_by(Appointment.appointment_date).all()
    
    # Get appointments by specialization
    appointments_by_spec = db.session.query(
        Doctor.specialization,
        func.count(Appointment.id)
    ).join(Appointment).group_by(Doctor.specialization).all()
    
    # Get doctor performance
    doctor_performance = db.session.query(
        User.username,
        Doctor.specialization,
        func.count(Appointment.id).label('total_appointments'),
        func.avg(Doctor.rating).label('avg_rating')
    ).join(Doctor, User.id == Doctor.user_id).outerjoin(
        Appointment, Doctor.id == Appointment.doctor_id
    ).group_by(User.id).all()
    
    return render_template('admin/dashboard.html',
                         doctor_count=doctor_count,
                         patient_count=patient_count,
                         appointment_count=appointment_count,
                         appointments_by_date=appointments_by_date,
                         appointments_by_spec=appointments_by_spec,
                         doctor_performance=doctor_performance)

@bp.route('/doctors')
@role_required('admin')
def doctors():
    search = request.args.get('search', '')
    if search:
        doctors = Doctor.query.join(User).filter(
            (User.username.contains(search)) | (Doctor.specialization.contains(search))
        ).all()
    else:
        doctors = Doctor.query.all()
    
    return render_template('admin/doctors.html', doctors=doctors, search=search)

@bp.route('/doctors/create', methods=['GET', 'POST'])
@role_required('admin')
def create_doctor():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        specialization = request.form.get('specialization')
        
        # Check if username or email exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('admin/create_doctor.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('admin/create_doctor.html')
        
        user = User(username=username, email=email, phone=phone, role='doctor')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        doctor = Doctor(user_id=user.id, specialization=specialization)
        db.session.add(doctor)
        
        # Audit log
        audit = AuditLog(user_id=session['user_id'], action='CREATE', 
                        entity_type='Doctor', entity_id=user.id,
                        details=f'Created doctor: {username}')
        db.session.add(audit)
        
        db.session.commit()
        flash('Doctor created successfully', 'success')
        return redirect(url_for('admin.doctors'))
    
    return render_template('admin/create_doctor.html')

@bp.route('/patients')
@role_required('admin')
def patients():
    search = request.args.get('search', '')
    if search:
        patients = Patient.query.join(User).filter(
            (User.username.contains(search)) | 
            (User.email.contains(search)) |
            (Patient.medical_id.contains(search))
        ).all()
    else:
        patients = Patient.query.all()
    
    return render_template('admin/patients.html', patients=patients, search=search)

@bp.route('/patients/create', methods=['GET', 'POST'])
@role_required('admin')
def create_patient():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        medical_id = request.form.get('medical_id')
        
        # Check if username or email exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('admin/create_patient.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('admin/create_patient.html')
        
        if Patient.query.filter_by(medical_id=medical_id).first():
            flash('Medical ID already exists', 'error')
            return render_template('admin/create_patient.html')
        
        user = User(username=username, email=email, phone=phone, role='patient')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        patient = Patient(user_id=user.id, medical_id=medical_id)
        db.session.add(patient)
        
        # Audit log
        audit = AuditLog(user_id=session['user_id'], action='CREATE',
                        entity_type='Patient', entity_id=user.id,
                        details=f'Created patient: {username}')
        db.session.add(audit)
        
        db.session.commit()
        flash('Patient created successfully', 'success')
        return redirect(url_for('admin.patients'))
    
    return render_template('admin/create_patient.html')

@bp.route('/audit-logs')
@role_required('admin')
def audit_logs():
    filter_action = request.args.get('action', '')
    filter_user = request.args.get('user', '')
    
    query = AuditLog.query
    
    if filter_action:
        query = query.filter_by(action=filter_action)
    if filter_user:
        query = query.join(User).filter(User.username.contains(filter_user))
    
    logs = query.order_by(AuditLog.created_at.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)

@bp.route('/appointments')
@role_required('admin')
def appointments_list():
    status_filter = request.args.get('status', '')
    
    query = Appointment.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    
    # Get statistics
    total_appointments = Appointment.query.count()
    booked = Appointment.query.filter_by(status='Booked').count()
    completed = Appointment.query.filter_by(status='Completed').count()
    cancelled = Appointment.query.filter_by(status='Cancelled').count()
    
    return render_template('admin/appointments.html',
                         appointments=appointments,
                         total_appointments=total_appointments,
                         booked=booked,
                         completed=completed,
                         cancelled=cancelled,
                         status_filter=status_filter)

@bp.route('/doctors/<int:doctor_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_doctor_status(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user = doctor.user
    
    user.is_active = not user.is_active
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='UPDATE',
                    entity_type='Doctor', entity_id=doctor.id,
                    details=f'{"Activated" if user.is_active else "Deactivated"} doctor: {user.username}')
    db.session.add(audit)
    
    db.session.commit()
    flash(f'Doctor {"activated" if user.is_active else "deactivated"} successfully', 'success')
    return redirect(url_for('admin.doctors'))

@bp.route('/patients/<int:patient_id>/toggle-status', methods=['POST'])
@role_required('admin')
def toggle_patient_status(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    user = patient.user
    
    user.is_active = not user.is_active
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='UPDATE',
                    entity_type='Patient', entity_id=patient.id,
                    details=f'{"Activated" if user.is_active else "Deactivated"} patient: {user.username}')
    db.session.add(audit)
    
    db.session.commit()
    flash(f'Patient {"activated" if user.is_active else "deactivated"} successfully', 'success')
    return redirect(url_for('admin.patients'))

@bp.route('/billing')
@role_required('admin')
def billing():
    from models import Bill
    
    status_filter = request.args.get('status', '')
    
    query = Bill.query
    if status_filter:
        query = query.filter_by(payment_status=status_filter)
    
    bills = query.order_by(Bill.created_at.desc()).all()
    
    # Calculate statistics
    total_revenue = db.session.query(func.sum(Bill.total_amount)).filter_by(payment_status='Paid').scalar() or 0
    pending_amount = db.session.query(func.sum(Bill.total_amount)).filter_by(payment_status='Pending').scalar() or 0
    total_bills = Bill.query.count()
    paid_bills = Bill.query.filter_by(payment_status='Paid').count()
    
    return render_template('admin/billing.html',
                         bills=bills,
                         total_revenue=total_revenue,
                         pending_amount=pending_amount,
                         total_bills=total_bills,
                         paid_bills=paid_bills,
                         status_filter=status_filter)
