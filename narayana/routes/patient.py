from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Patient, Doctor, Appointment, Availability, Rating, User, AuditLog
from utils.auth import role_required
from utils.notifications import create_notification
from utils.validators import check_double_booking, validate_rating
from datetime import datetime, date, timedelta

bp = Blueprint('patient', __name__)

@bp.route('/dashboard')
@role_required('patient')
def dashboard():
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    
    # Get upcoming appointments
    today = date.today()
    upcoming = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_date >= today
    ).filter(Appointment.status != 'Cancelled').order_by(Appointment.appointment_date).all()
    
    # Get recent appointments
    recent = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc()
    ).limit(5).all()
    
    return render_template('patient/dashboard.html',
                         upcoming_appointments=upcoming,
                         recent_appointments=recent)

@bp.route('/search-doctors')
@role_required('patient')
def search_doctors():
    specialization = request.args.get('specialization', '')
    
    if specialization:
        doctors = Doctor.query.filter_by(specialization=specialization).all()
    else:
        doctors = Doctor.query.all()
    
    # Get unique specializations for filter
    specializations = db.session.query(Doctor.specialization).distinct().all()
    specializations = [s[0] for s in specializations]
    
    return render_template('patient/search_doctors.html',
                         doctors=doctors,
                         specializations=specializations,
                         selected_specialization=specialization)

@bp.route('/doctors/<int:doctor_id>')
@role_required('patient')
def doctor_profile(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    
    # Get available slots for next 7 days (default 24/7 unless blocked)
    today = date.today()
    seven_days = today + timedelta(days=7)
    
    # Generate default time slots
    available_slots = get_default_time_slots(doctor.id, today, seven_days)
    
    # Get smart suggestions (next 3 optimal slots)
    suggestions = get_smart_suggestions(available_slots)
    
    # Get recent ratings
    recent_ratings = Rating.query.filter_by(doctor_id=doctor.id).order_by(
        Rating.created_at.desc()
    ).limit(5).all()
    
    return render_template('patient/doctor_profile.html',
                         doctor=doctor,
                         available_slots=available_slots,
                         suggestions=suggestions,
                         recent_ratings=recent_ratings)

def get_default_time_slots(doctor_id, start_date, end_date):
    """Generate default 24/7 time slots for a doctor"""
    from datetime import time as dt_time
    
    slots = []
    current_date = start_date
    
    # Time slots: 9 AM to 5 PM in 1-hour intervals (8 slots per day)
    time_slots = [
        (dt_time(9, 0), dt_time(10, 0)),
        (dt_time(10, 0), dt_time(11, 0)),
        (dt_time(11, 0), dt_time(12, 0)),
        (dt_time(12, 0), dt_time(13, 0)),
        (dt_time(14, 0), dt_time(15, 0)),
        (dt_time(15, 0), dt_time(16, 0)),
        (dt_time(16, 0), dt_time(17, 0)),
        (dt_time(17, 0), dt_time(18, 0)),
    ]
    
    while current_date <= end_date:
        for start_time, end_time in time_slots:
            # Check if doctor has blocked this slot
            blocked = Availability.query.filter_by(
                doctor_id=doctor_id,
                date=current_date,
                start_time=start_time,
                is_available=False
            ).first()
            
            if not blocked:
                # Check if slot is already booked
                is_booked = Appointment.query.filter_by(
                    doctor_id=doctor_id,
                    appointment_date=current_date,
                    appointment_time=start_time
                ).filter(Appointment.status.in_(['Booked', 'Completed'])).first()
                
                if not is_booked:
                    # Create a virtual slot object
                    class VirtualSlot:
                        def __init__(self, date, start_time, end_time):
                            self.date = date
                            self.start_time = start_time
                            self.end_time = end_time
                    
                    slots.append(VirtualSlot(current_date, start_time, end_time))
        
        current_date += timedelta(days=1)
    
    return slots

def get_smart_suggestions(available_slots):
    """Get smart appointment suggestions"""
    if not available_slots:
        return []
    
    today = date.today()
    three_days = today + timedelta(days=3)
    
    # Prioritize slots within next 3 days
    priority_slots = [s for s in available_slots if s.date <= three_days]
    
    if not priority_slots:
        priority_slots = available_slots
    
    # Sort by date, then by time (morning first)
    priority_slots.sort(key=lambda x: (x.date, x.start_time))
    
    return priority_slots[:3]

@bp.route('/book-appointment', methods=['POST'])
@role_required('patient')
def book_appointment():
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    
    doctor_id = request.form.get('doctor_id')
    date_str = request.form.get('date')
    time_str = request.form.get('time')
    
    appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    appointment_time = datetime.strptime(time_str, '%H:%M').time()
    
    # Check for double booking
    if check_double_booking(doctor_id, appointment_date, appointment_time):
        flash('This time slot is no longer available', 'error')
        return redirect(url_for('patient.doctor_profile', doctor_id=doctor_id))
    
    # Create appointment
    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient.id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status='Booked'
    )
    db.session.add(appointment)
    
    # Create notifications
    doctor = Doctor.query.get(doctor_id)
    create_notification(doctor.user_id,
                       f'New appointment booked by {patient.user.username} on {appointment_date}')
    create_notification(patient.user_id,
                       f'Your appointment is confirmed for {appointment_date} at {appointment_time}')
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='CREATE',
                    entity_type='Appointment', entity_id=appointment.id,
                    details=f'Booked appointment with doctor {doctor_id}')
    db.session.add(audit)
    
    db.session.commit()
    flash('Appointment booked successfully', 'success')
    return redirect(url_for('patient.appointments'))

@bp.route('/appointments')
@role_required('patient')
def appointments():
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('patient/appointments.html', appointments=appointments)

@bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@role_required('patient')
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    
    if appointment.patient_id != patient.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('patient.appointments'))
    
    if appointment.status != 'Booked':
        flash('Only booked appointments can be cancelled', 'error')
        return redirect(url_for('patient.appointments'))
    
    appointment.status = 'Cancelled'
    
    # Create notification
    create_notification(appointment.doctor.user_id,
                       f'Appointment on {appointment.appointment_date} was cancelled by patient')
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='UPDATE',
                    entity_type='Appointment', entity_id=appointment.id,
                    details=f'Cancelled appointment')
    db.session.add(audit)
    
    db.session.commit()
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('patient.appointments'))

@bp.route('/appointments/<int:appointment_id>/rate', methods=['GET', 'POST'])
@role_required('patient')
def rate_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    
    if appointment.patient_id != patient.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('patient.appointments'))
    
    if appointment.status != 'Completed':
        flash('Only completed appointments can be rated', 'error')
        return redirect(url_for('patient.appointments'))
    
    if request.method == 'POST':
        rating_value = request.form.get('rating')
        feedback = request.form.get('feedback')
        
        if not validate_rating(rating_value):
            flash('Rating must be between 1 and 5', 'error')
            return render_template('patient/rate_appointment.html', appointment=appointment)
        
        if appointment.rating:
            # Update existing rating
            appointment.rating.rating = int(rating_value)
            appointment.rating.feedback = feedback
        else:
            # Create new rating
            rating = Rating(
                appointment_id=appointment.id,
                doctor_id=appointment.doctor_id,
                patient_id=patient.id,
                rating=int(rating_value),
                feedback=feedback
            )
            db.session.add(rating)
        
        # Update doctor's average rating
        doctor = appointment.doctor
        avg_rating = db.session.query(db.func.avg(Rating.rating)).filter_by(
            doctor_id=doctor.id
        ).scalar()
        doctor.rating = round(avg_rating, 2) if avg_rating else 0.0
        
        # Audit log
        audit = AuditLog(user_id=session['user_id'], action='CREATE',
                        entity_type='Rating', entity_id=appointment.id,
                        details=f'Rated appointment {appointment.id}')
        db.session.add(audit)
        
        db.session.commit()
        flash('Rating submitted successfully', 'success')
        return redirect(url_for('patient.appointments'))
    
    return render_template('patient/rate_appointment.html', appointment=appointment)

@bp.route('/medical-history')
@role_required('patient')
def medical_history():
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    
    # Get all completed appointments with treatments
    appointments = Appointment.query.filter_by(
        patient_id=patient.id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('patient/medical_history.html', appointments=appointments)

@bp.route('/bills')
@role_required('patient')
def bills():
    from models import Bill
    
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    bills = Bill.query.filter_by(patient_id=patient.id).order_by(Bill.created_at.desc()).all()
    
    # Calculate totals
    total_billed = sum(bill.total_amount for bill in bills)
    total_paid = sum(bill.total_amount for bill in bills if bill.payment_status == 'Paid')
    total_pending = sum(bill.total_amount for bill in bills if bill.payment_status == 'Pending')
    
    return render_template('patient/bills.html', 
                         bills=bills,
                         total_billed=total_billed,
                         total_paid=total_paid,
                         total_pending=total_pending)

@bp.route('/bills/<int:bill_id>')
@role_required('patient')
def view_bill(bill_id):
    from models import Bill
    
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    bill = Bill.query.get_or_404(bill_id)
    
    if bill.patient_id != patient.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('patient.bills'))
    
    return render_template('patient/view_bill.html', bill=bill)

@bp.route('/bills/<int:bill_id>/pay', methods=['POST'])
@role_required('patient')
def pay_bill(bill_id):
    from models import Bill
    
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    bill = Bill.query.get_or_404(bill_id)
    
    if bill.patient_id != patient.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('patient.bills'))
    
    if bill.payment_status == 'Paid':
        flash('Bill already paid', 'warning')
        return redirect(url_for('patient.bills'))
    
    payment_method = request.form.get('payment_method')
    
    # Simulate payment processing
    bill.payment_status = 'Paid'
    bill.payment_method = payment_method
    bill.payment_date = datetime.now()
    bill.transaction_id = f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}{bill.id}'
    
    # Create notification
    create_notification(bill.doctor.user_id,
                       f'Payment received for appointment on {bill.appointment.appointment_date}')
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='UPDATE',
                    entity_type='Bill', entity_id=bill.id,
                    details=f'Paid bill {bill.id} via {payment_method}')
    db.session.add(audit)
    
    db.session.commit()
    flash('Payment successful!', 'success')
    return redirect(url_for('patient.view_bill', bill_id=bill.id))
