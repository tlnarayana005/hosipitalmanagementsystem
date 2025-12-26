from datetime import datetime, date, time, timedelta
from models import Appointment

def validate_email(email):
    """Basic email validation"""
    return '@' in email and '.' in email

def validate_phone(phone):
    """Basic phone validation"""
    return phone and len(phone) >= 10

def validate_rating(rating):
    """Validate rating is between 1 and 5"""
    try:
        rating_int = int(rating)
        return 1 <= rating_int <= 5
    except (ValueError, TypeError):
        return False

def check_double_booking(doctor_id, appointment_date, appointment_time, exclude_appointment_id=None):
    """Check if doctor has conflicting appointment"""
    query = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time
    ).filter(Appointment.status.in_(['Booked', 'Completed']))
    
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)
    
    return query.first() is not None

def is_within_7_days(target_date):
    """Check if date is within next 7 days"""
    today = date.today()
    seven_days_later = today + timedelta(days=7)
    return today <= target_date <= seven_days_later
