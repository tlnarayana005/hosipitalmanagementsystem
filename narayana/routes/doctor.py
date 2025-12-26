from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Doctor, Appointment, Availability, Treatment, User, Patient, AuditLog
from utils.auth import role_required
from utils.notifications import create_notification
from datetime import datetime, date, time, timedelta

bp = Blueprint('doctor', __name__)

@bp.route('/dashboard')
@role_required('doctor')
def dashboard():
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    # Get today's appointments
    today = date.today()
    today_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id,
        appointment_date=today
    ).filter(Appointment.status != 'Cancelled').all()
    
    # Get upcoming appointments
    upcoming = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date > today
    ).filter(Appointment.status != 'Cancelled').order_by(Appointment.appointment_date).limit(5).all()
    
    return render_template('doctor/dashboard.html', 
                         today_appointments=today_appointments,
                         upcoming_appointments=upcoming,
                         doctor=doctor)

@bp.route('/availability', methods=['GET', 'POST'])
@role_required('doctor')
def availability():
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    if request.method == 'POST':
        action = request.form.get('action', 'block')
        date_str = request.form.get('date')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        
        avail_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Check if already exists
        existing = Availability.query.filter_by(
            doctor_id=doctor.id,
            date=avail_date,
            start_time=start_time
        ).first()
        
        if action == 'block':
            # Block this time slot
            if existing:
                existing.is_available = False
                flash('Time slot blocked successfully', 'success')
            else:
                availability = Availability(
                    doctor_id=doctor.id,
                    date=avail_date,
                    start_time=start_time,
                    end_time=end_time,
                    is_available=False
                )
                db.session.add(availability)
                flash('Time slot blocked successfully', 'success')
            
            # Audit log
            audit = AuditLog(user_id=session['user_id'], action='CREATE',
                           entity_type='Availability', entity_id=doctor.id,
                           details=f'Blocked time slot for {avail_date} at {start_time}')
            db.session.add(audit)
        
        db.session.commit()
        return redirect(url_for('doctor.availability'))
    
    # Get blocked slots
    today = date.today()
    blocked_slots = Availability.query.filter(
        Availability.doctor_id == doctor.id,
        Availability.date >= today,
        Availability.is_available == False
    ).order_by(Availability.date, Availability.start_time).all()
    
    return render_template('doctor/availability.html', 
                         blocked_slots=blocked_slots,
                         doctor=doctor)

@bp.route('/availability/<int:availability_id>/unblock', methods=['POST'])
@role_required('doctor')
def unblock_availability(availability_id):
    availability = Availability.query.get_or_404(availability_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    if availability.doctor_id != doctor.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('doctor.availability'))
    
    # Remove the block (delete the availability record)
    db.session.delete(availability)
    db.session.commit()
    flash('Time slot unblocked successfully', 'success')
    return redirect(url_for('doctor.availability'))

@bp.route('/appointments')
@role_required('doctor')
def appointments():
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc()
    ).all()
    
    return render_template('doctor/appointments.html', appointments=appointments)

@bp.route('/appointments/<int:appointment_id>/complete', methods=['POST'])
@role_required('doctor')
def complete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if appointment.status != 'Booked':
        flash('Only booked appointments can be completed', 'error')
        return redirect(url_for('doctor.appointments'))
    
    appointment.status = 'Completed'
    
    # Create notifications
    create_notification(appointment.patient.user_id, 
                       f'Your appointment on {appointment.appointment_date} has been completed')
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='UPDATE',
                    entity_type='Appointment', entity_id=appointment.id,
                    details=f'Marked appointment as completed')
    db.session.add(audit)
    
    db.session.commit()
    flash('Appointment marked as completed', 'success')
    return redirect(url_for('doctor.add_treatment', appointment_id=appointment_id))

@bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@role_required('doctor')
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if appointment.status not in ['Booked']:
        flash('Only booked appointments can be cancelled', 'error')
        return redirect(url_for('doctor.appointments'))
    
    appointment.status = 'Cancelled'
    
    # Create notification
    create_notification(appointment.patient.user_id,
                       f'Your appointment on {appointment.appointment_date} has been cancelled by the doctor')
    
    # Audit log
    audit = AuditLog(user_id=session['user_id'], action='UPDATE',
                    entity_type='Appointment', entity_id=appointment.id,
                    details=f'Cancelled appointment')
    db.session.add(audit)
    
    db.session.commit()
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('doctor.appointments'))

@bp.route('/appointments/<int:appointment_id>/treatment', methods=['GET', 'POST'])
@role_required('doctor')
def add_treatment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if appointment.status != 'Completed':
        flash('Treatment can only be added to completed appointments', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        
        if appointment.treatment:
            # Update existing treatment
            appointment.treatment.diagnosis = diagnosis
            appointment.treatment.prescription = prescription
            appointment.treatment.notes = notes
        else:
            # Create new treatment
            treatment = Treatment(
                appointment_id=appointment.id,
                diagnosis=diagnosis,
                prescription=prescription,
                notes=notes
            )
            db.session.add(treatment)
        
        # Create notification
        create_notification(appointment.patient.user_id,
                           f'Treatment record added for your appointment on {appointment.appointment_date}')
        
        # Audit log
        audit = AuditLog(user_id=session['user_id'], action='CREATE',
                        entity_type='Treatment', entity_id=appointment.id,
                        details=f'Added treatment for appointment {appointment.id}')
        db.session.add(audit)
        
        db.session.commit()
        flash('Treatment record saved successfully', 'success')
        return redirect(url_for('doctor.appointments'))
    
    return render_template('doctor/add_treatment.html', appointment=appointment)

@bp.route('/patients/<int:patient_id>/history')
@role_required('doctor')
def patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all completed appointments with treatments
    appointments = Appointment.query.filter_by(
        patient_id=patient.id,
        status='Completed'
    ).order_by(Appointment.appointment_date.desc()).all()
    
    return render_template('doctor/patient_history.html', 
                         patient=patient,
                         appointments=appointments)

@bp.route('/patients')
@role_required('doctor')
def patients_list():
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    # Get unique patients who have appointments with this doctor
    patients = db.session.query(Patient).join(Appointment).filter(
        Appointment.doctor_id == doctor.id
    ).distinct().all()
    
    return render_template('doctor/patients_list.html', patients=patients)

@bp.route('/appointments/<int:appointment_id>/billing', methods=['GET', 'POST'])
@role_required('doctor')
def create_bill(appointment_id):
    from models import Bill
    
    appointment = Appointment.query.get_or_404(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    
    if appointment.doctor_id != doctor.id:
        flash('Unauthorized action', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if appointment.status != 'Completed':
        flash('Bills can only be created for completed appointments', 'error')
        return redirect(url_for('doctor.appointments'))
    
    if request.method == 'POST':
        consultation_fee = float(request.form.get('consultation_fee', 0))
        lab_charges = float(request.form.get('lab_charges', 0))
        medicine_charges = float(request.form.get('medicine_charges', 0))
        procedure_charges = float(request.form.get('procedure_charges', 0))
        other_charges = float(request.form.get('other_charges', 0))
        discount_amount = float(request.form.get('discount_amount', 0))
        notes = request.form.get('notes', '')
        
        # Calculate totals
        subtotal = consultation_fee + lab_charges + medicine_charges + procedure_charges + other_charges
        tax_amount = subtotal * 0.05  # 5% tax
        total_amount = subtotal + tax_amount - discount_amount
        
        # Check if bill already exists
        existing_bill = Bill.query.filter_by(appointment_id=appointment.id).first()
        
        if existing_bill:
            # Update existing bill
            existing_bill.consultation_fee = consultation_fee
            existing_bill.lab_charges = lab_charges
            existing_bill.medicine_charges = medicine_charges
            existing_bill.procedure_charges = procedure_charges
            existing_bill.other_charges = other_charges
            existing_bill.subtotal = subtotal
            existing_bill.tax_amount = tax_amount
            existing_bill.discount_amount = discount_amount
            existing_bill.total_amount = total_amount
            existing_bill.notes = notes
        else:
            # Create new bill
            bill = Bill(
                appointment_id=appointment.id,
                patient_id=appointment.patient_id,
                doctor_id=doctor.id,
                consultation_fee=consultation_fee,
                lab_charges=lab_charges,
                medicine_charges=medicine_charges,
                procedure_charges=procedure_charges,
                other_charges=other_charges,
                subtotal=subtotal,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                notes=notes
            )
            db.session.add(bill)
        
        # Create notification
        create_notification(appointment.patient.user_id,
                           f'Bill generated for your appointment on {appointment.appointment_date}. Amount: ${total_amount:.2f}')
        
        # Audit log
        audit = AuditLog(user_id=session['user_id'], action='CREATE',
                        entity_type='Bill', entity_id=appointment.id,
                        details=f'Created bill for appointment {appointment.id}')
        db.session.add(audit)
        
        db.session.commit()
        flash('Bill created successfully', 'success')
        return redirect(url_for('doctor.appointments'))
    
    # Get existing bill if any
    existing_bill = Bill.query.filter_by(appointment_id=appointment.id).first()
    
    return render_template('doctor/create_bill.html', 
                         appointment=appointment, 
                         doctor=doctor,
                         existing_bill=existing_bill)
