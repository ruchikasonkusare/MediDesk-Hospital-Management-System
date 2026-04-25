# MediDesk — Advanced Healthcare Management System

Full-stack Django healthcare platform with REST API, ML risk scoring, Celery async tasks, analytics dashboard, and Excel/PDF exports.

## Tech Stack
- **Backend**: Python 3.10+, Django 4.2+
- **REST API**: Django REST Framework + JWT + Swagger UI
- **Async**: Celery + Redis
- **ML**: scikit-learn (readmission risk scoring)
- **Database**: SQLite (swap to PostgreSQL for production)
- **Exports**: openpyxl (Excel), reportlab (PDF)
- **Tests**: pytest + pytest-django + pytest-cov

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv && source venv/bin/activate

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Run migrations + seed demo data
python manage.py migrate
python setup_and_seed.py

# 4. Train ML risk model
python manage.py shell -c "from core.ml.risk_model import train_and_save; train_and_save()"

# 5. Start server
python manage.py runserver
```

## URLs

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/ | Main app |
| http://127.0.0.1:8000/analytics/ | Analytics dashboard |
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/docs/redoc/ | ReDoc |
| http://127.0.0.1:8000/api/token/ | Get JWT token |
| http://127.0.0.1:8000/admin/ | Django admin |

## Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Receptionist | reception1 | reception123 |
| Nurse | nurse1 | nurse123 |
| Pharmacist | pharmacist1 | pharma123 |
| Doctor (Cardiology) | dr_priya | doctor123 |
| Doctor (General) | dr_anita | doctor123 |
| Doctor (Ortho) | dr_vikram | doctor123 |

## REST API Usage

### Get JWT Token
```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### Use Token
```bash
curl http://127.0.0.1:8000/api/patients/ \
  -H "Authorization: Bearer <access_token>"
```

### Key Endpoints
```
GET/POST  /api/patients/
GET       /api/patients/{id}/history/
GET       /api/patients/{id}/risk_score/
GET/POST  /api/appointments/
GET       /api/appointments/today/
POST      /api/appointments/{id}/update_status/
GET/POST  /api/bills/
POST      /api/bills/{id}/add_payment/
GET       /api/analytics/summary/
GET       /api/analytics/charts/?months=6
POST      /api/prescriptions/{id}/dispense/
```

## Running Tests
```bash
# Run all tests
pytest -v

# With coverage report
pytest --cov=core --cov-report=term-missing --cov-report=html

# Run specific test class
pytest core/tests/test_models.py::TestPatientModel -v
pytest core/tests/test_api.py::TestJWTAuth -v
```

## Celery (Async Tasks)
```bash
# Start Redis (required)
redis-server

# Start Celery worker
celery -A medidesk worker --loglevel=info

# Start Celery Beat (periodic tasks)
celery -A medidesk beat --loglevel=info

# Test a task manually
python manage.py shell -c "
from core.tasks import schedule_appointment_reminders
result = schedule_appointment_reminders.delay()
print(result.get())
"
```

## Export URLs
```
/export/patients/excel/           — Download all patients as Excel
/export/billing/excel/            — Download billing summary as Excel
/export/prescription/<id>/pdf/    — Download prescription as PDF
/export/bill/<id>/pdf/            — Download invoice as PDF
```
