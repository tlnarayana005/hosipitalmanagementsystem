from flask import Blueprint, jsonify
from models import Doctor, Patient, Appointment, User
from sqlalchemy import func

bp = Blueprint('api', __name__)

@bp.route('/doctors')
def get_doctors():
    doctors = Doctor.query.all()
    result = []
    for doctor in doctors:
        result.append({
            'id': doctor.id,
            'username': doctor.user.username,
            'email': doctor.user.email,
            'phone': doctor.user.phone,
            'specialization': doctor.specialization,
            'rating': doctor.rating
        })
    return jsonify(result)

@bp.route('/patients')
def get_patients():
    patients = Patient.query.all()
    result = []
    for patient in patients:
        result.append({
            'id': patient.id,
            'username': patient.user.username,
            'email': patient.user.email,
            'phone': patient.user.phone,
            'medical_id': patient.medical_id
        })
    return jsonify(result)

@bp.route('/appointments')
def get_appointments():
    appointments = Appointment.query.all()
    result = []
    for appointment in appointments:
        result.append({
            'id': appointment.id,
            'doctor': appointment.doctor.user.username,
            'patient': appointment.patient.user.username,
            'date': appointment.appointment_date.isoformat(),
            'time': appointment.appointment_time.isoformat(),
            'status': appointment.status
        })
    return jsonify(result)

@bp.route('/specializations')
def get_specializations():
    specializations = Doctor.query.with_entities(
        Doctor.specialization,
        func.count(Doctor.id).label('count')
    ).group_by(Doctor.specialization).all()
    
    result = [{'specialization': s[0], 'count': s[1]} for s in specializations]
    return jsonify(result)
