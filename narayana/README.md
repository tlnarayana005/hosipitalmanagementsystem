# MediCare Hospital Management System

A comprehensive, production-ready web application for streamlining hospital operations with modern UI, complete billing system, and 24/7 availability management.

## ✨ Key Features

### 💰 Complete Billing System
- **Itemized Bills**: Consultation, lab tests, medicines, procedures
- **Automatic Tax**: 5% tax calculation
- **Multiple Payment Methods**: Cash, Card, Insurance, Online
- **Professional Invoices**: Print-ready with hospital branding
- **Revenue Analytics**: Track payments and pending amounts

### 🕐 24/7 Default Availability
- **Always Available**: Doctors available 9 AM - 6 PM by default
- **Flexible Blocking**: Block specific time slots when unavailable
- **No Setup Required**: Immediate availability for new doctors
- **Smart Scheduling**: 1-hour time slots throughout the day

### 🆕 Patient Self-Registration
- **Easy Signup**: Patients can register themselves
- **Comprehensive Form**: Personal, medical, and emergency information
- **Auto Medical ID**: Automatic unique ID generation
- **Instant Access**: Login immediately after registration

### 👤 Enhanced User Profiles
- **Extended Information**: Full name, DOB, gender, address
- **Medical Details**: Blood group, allergies, chronic conditions
- **Professional Info**: Doctor qualifications, experience, bio
- **Profile Management**: Update information anytime

### 📅 Smart Appointment System
- **Intelligent Suggestions**: Top 3 optimal time slots
- **Double-Booking Prevention**: Automatic conflict detection
- **Appointment Lifecycle**: Booked → Completed → Cancelled
- **Easy Cancellation**: Free up slots for rebooking

### 📊 Comprehensive Analytics
- **Admin Dashboard**: Revenue, appointments, doctor performance
- **Financial Tracking**: Total revenue, pending payments
- **Trend Analysis**: 30-day appointment trends
- **Performance Metrics**: Doctor ratings and completion rates

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: Bootstrap 5, Jinja2 templates
- **Authentication**: Session-based with hashed passwords

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The application will automatically create the database and seed it with demo data on first run.

## Demo Accounts

- **Admin**: username: `admin`, password: `admin123`
- **Doctor**: username: `dr_smith`, password: `doctor123`
- **Patient**: username: `patient1`, password: `patient123`

## API Endpoints

- `GET /api/doctors` - List all doctors
- `GET /api/patients` - List all patients
- `GET /api/appointments` - List all appointments
- `GET /api/specializations` - List specializations with counts

## Project Structure

```
/
├── app.py                      # Main Flask application
├── models.py                   # Database models
├── routes/                     # Route handlers by role
│   ├── admin.py
│   ├── doctor.py
│   ├── patient.py
│   ├── api.py
│   └── shared.py
├── templates/                  # HTML templates
│   ├── admin/
│   ├── doctor/
│   ├── patient/
│   └── shared/
├── utils/                      # Helper functions
│   ├── auth.py
│   ├── validators.py
│   └── notifications.py
└── database.db                 # SQLite database (auto-generated)
```

## Key Business Rules

- Appointments cannot be double-booked
- Appointments cannot be modified once Completed or Cancelled
- Availability windows limited to 7-day periods
- Smart suggestions prioritize next 3 days, morning slots preferred
- Cancelled appointments free up time slots for rebooking
- Audit logs are append-only (no updates/deletes)

## License

MIT
