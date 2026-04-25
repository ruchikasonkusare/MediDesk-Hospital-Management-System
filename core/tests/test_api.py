"""
MediDesk API Tests
===================
Run: pytest core/tests/test_api.py -v --tb=short
"""
import pytest
from datetime import date, time, timedelta
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from core.models import (
    Doctor, Patient, Appointment, Bill,
    Prescription, MedicalRecord, UserProfile,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    u = User.objects.create_superuser('api_admin', 'admin@test.com', 'pass123')
    UserProfile.objects.get_or_create(user=u, defaults={'role': 'admin'})
    return u


@pytest.fixture
def receptionist_user(db):
    u = User.objects.create_user('api_reception', 'rec@test.com', 'pass123')
    UserProfile.objects.create(user=u, role='receptionist', phone='9800000001')
    return u


@pytest.fixture
def doctor_user(db):
    u = User.objects.create_user('api_doctor', 'doc@test.com', 'pass123')
    UserProfile.objects.create(user=u, role='doctor', phone='9800000002')
    return u


@pytest.fixture
def pharmacist_user(db):
    u = User.objects.create_user('api_pharma', 'ph@test.com', 'pass123')
    UserProfile.objects.create(user=u, role='pharmacist', phone='9800000003')
    return u


@pytest.fixture
def doctor(db, doctor_user):
    d = Doctor.objects.create(
        name='Dr Test', specialization='general',
        license_number='API-DOC-001', phone='9876543210',
        email='drtest@test.com', qualification='MBBS',
        experience_years=5, consultation_fee=400,
        available_days='Mon,Tue,Wed,Thu,Fri',
        user=doctor_user,
    )
    return d


@pytest.fixture
def patient(db, admin_user):
    return Patient.objects.create(
        name='API Test Patient',
        date_of_birth=date(1990, 6, 15),
        gender='F', blood_group='A+',
        phone='9812345678',
        address='Test City',
        emergency_contact_name='EC Name',
        emergency_contact_phone='9812345679',
        registered_by=admin_user,
    )


@pytest.fixture
def appointment(db, doctor, patient):
    return Appointment.objects.create(
        patient=patient, doctor=doctor,
        appointment_date=date.today() + timedelta(days=1),
        appointment_time=time(10, 0),
        appointment_type='opd',
        status='scheduled',
        reason='Routine check',
    )


@pytest.fixture
def auth_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def auth_reception(api_client, receptionist_user):
    api_client.force_authenticate(user=receptionist_user)
    return api_client


@pytest.fixture
def auth_doctor(api_client, doctor_user):
    api_client.force_authenticate(user=doctor_user)
    return api_client


@pytest.fixture
def auth_pharmacist(api_client, pharmacist_user):
    api_client.force_authenticate(user=pharmacist_user)
    return api_client


# ─────────────────────────────────────────────────────────────────────────────
# JWT Auth Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestJWTAuth:

    def test_obtain_token_valid_credentials(self, api_client, admin_user):
        res = api_client.post('/api/token/', {
            'username': 'api_admin', 'password': 'pass123'
        })
        assert res.status_code == status.HTTP_200_OK
        assert 'access' in res.data
        assert 'refresh' in res.data

    def test_obtain_token_invalid_credentials(self, api_client):
        res = api_client.post('/api/token/', {
            'username': 'nobody', 'password': 'wrong'
        })
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_request_rejected(self, api_client):
        res = api_client.get('/api/patients/')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_used_for_auth(self, api_client, admin_user):
        res = api_client.post('/api/token/', {
            'username': 'api_admin', 'password': 'pass123'
        })
        token = res.data['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        res2 = api_client.get('/api/patients/')
        assert res2.status_code == status.HTTP_200_OK

    def test_refresh_token(self, api_client, admin_user):
        res = api_client.post('/api/token/', {
            'username': 'api_admin', 'password': 'pass123'
        })
        refresh = res.data['refresh']
        res2 = api_client.post('/api/token/refresh/', {'refresh': refresh})
        assert res2.status_code == status.HTTP_200_OK
        assert 'access' in res2.data


# ─────────────────────────────────────────────────────────────────────────────
# Patient API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPatientAPI:

    def test_list_patients_authenticated(self, auth_admin, patient):
        res = auth_admin.get('/api/patients/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['count'] >= 1

    def test_create_patient_as_receptionist(self, auth_reception):
        res = auth_reception.post('/api/patients/', {
            'name': 'New Patient',
            'date_of_birth': '1995-05-15',
            'gender': 'M',
            'phone': '9900000001',
            'address': 'Test Address',
            'emergency_contact_name': 'EC',
            'emergency_contact_phone': '9900000002',
        })
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['name'] == 'New Patient'
        assert 'patient_id' in res.data

    def test_create_patient_invalid_phone_short(self, auth_reception):
        res = auth_reception.post('/api/patients/', {
            'name': 'Bad Phone',
            'date_of_birth': '1990-01-01',
            'gender': 'M',
            'phone': '12345',  # too short
            'address': 'Test',
            'emergency_contact_name': 'EC',
            'emergency_contact_phone': '9900000001',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone' in res.data

    def test_create_patient_invalid_phone_letters(self, auth_reception):
        res = auth_reception.post('/api/patients/', {
            'name': 'Alpha Phone',
            'date_of_birth': '1990-01-01',
            'gender': 'M',
            'phone': '98AB345678',
            'address': 'Test',
            'emergency_contact_name': 'EC',
            'emergency_contact_phone': '9900000001',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_patient_future_dob_rejected(self, auth_reception):
        future = (date.today() + timedelta(days=10)).isoformat()
        res = auth_reception.post('/api/patients/', {
            'name': 'Future Person',
            'date_of_birth': future,
            'gender': 'F',
            'phone': '9900000001',
            'address': 'Test',
            'emergency_contact_name': 'EC',
            'emergency_contact_phone': '9900000002',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_patient_detail(self, auth_admin, patient):
        res = auth_admin.get(f'/api/patients/{patient.id}/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['name'] == patient.name
        assert res.data['patient_id'] == patient.patient_id

    def test_patient_history_endpoint(self, auth_admin, patient):
        res = auth_admin.get(f'/api/patients/{patient.id}/history/')
        assert res.status_code == status.HTTP_200_OK
        assert 'appointments' in res.data
        assert 'medical_records' in res.data
        assert 'prescriptions' in res.data

    def test_search_patient_by_name(self, auth_admin, patient):
        res = auth_admin.get('/api/patients/?search=API+Test')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['count'] >= 1

    def test_pharmacist_cannot_create_patient(self, auth_pharmacist):
        res = auth_pharmacist.post('/api/patients/', {
            'name': 'Test', 'date_of_birth': '1990-01-01',
            'gender': 'M', 'phone': '9900000001',
            'address': 'Test', 'emergency_contact_name': 'EC',
            'emergency_contact_phone': '9900000002',
        })
        assert res.status_code in [403, 400]


# ─────────────────────────────────────────────────────────────────────────────
# Doctor API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDoctorAPI:

    def test_list_doctors(self, auth_admin, doctor):
        res = auth_admin.get('/api/doctors/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['count'] >= 1

    def test_doctor_detail(self, auth_admin, doctor):
        res = auth_admin.get(f'/api/doctors/{doctor.id}/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['name'] == doctor.name

    def test_receptionist_cannot_create_doctor(self, auth_reception):
        res = auth_reception.post('/api/doctors/', {
            'name': 'New Doc', 'specialization': 'general',
            'license_number': 'NEW-001', 'phone': '9900000001',
            'email': 'newdoc@test.com', 'qualification': 'MBBS',
        })
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_doctor(self, auth_admin):
        res = auth_admin.post('/api/doctors/', {
            'name': 'New Doctor',
            'specialization': 'pediatrics',
            'license_number': 'NEW-DOC-999',
            'phone': '9900000001',
            'email': 'newdoc999@test.com',
            'qualification': 'MBBS DCH',
            'experience_years': 3,
            'consultation_fee': 450,
            'available_days': 'Mon,Tue,Wed',
        })
        assert res.status_code == status.HTTP_201_CREATED

    def test_doctor_stats_endpoint(self, auth_admin, doctor, appointment):
        res = auth_admin.get(f'/api/doctors/{doctor.id}/stats/')
        assert res.status_code == status.HTTP_200_OK
        assert 'total_appointments' in res.data
        assert 'no_show_rate' in res.data

    def test_filter_by_specialization(self, auth_admin, doctor):
        res = auth_admin.get('/api/doctors/?specialization=general')
        assert res.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# Appointment API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAppointmentAPI:

    def test_list_appointments(self, auth_admin, appointment):
        res = auth_admin.get('/api/appointments/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['count'] >= 1

    def test_create_appointment_future(self, auth_reception, doctor, patient):
        future = (date.today() + timedelta(days=3)).isoformat()
        res = auth_reception.post('/api/appointments/', {
            'patient': patient.id,
            'doctor': doctor.id,
            'appointment_date': future,
            'appointment_time': '14:00:00',
            'appointment_type': 'opd',
            'reason': 'Follow up visit',
        })
        assert res.status_code == status.HTTP_201_CREATED

    def test_create_appointment_in_past_rejected(self, auth_reception, doctor, patient):
        past = (date.today() - timedelta(days=1)).isoformat()
        res = auth_reception.post('/api/appointments/', {
            'patient': patient.id,
            'doctor': doctor.id,
            'appointment_date': past,
            'appointment_time': '10:00:00',
            'appointment_type': 'opd',
            'reason': 'Past appointment',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_emergency_appointment_in_past_allowed(self, auth_reception, doctor, patient):
        past = (date.today() - timedelta(days=1)).isoformat()
        res = auth_reception.post('/api/appointments/', {
            'patient': patient.id,
            'doctor': doctor.id,
            'appointment_date': past,
            'appointment_time': '10:00:00',
            'appointment_type': 'emergency',
            'reason': 'Emergency case',
        })
        assert res.status_code == status.HTTP_201_CREATED

    def test_double_booking_rejected(self, auth_reception, doctor, patient, appointment):
        res = auth_reception.post('/api/appointments/', {
            'patient': patient.id,
            'doctor': doctor.id,
            'appointment_date': appointment.appointment_date.isoformat(),
            'appointment_time': appointment.appointment_time.strftime('%H:%M:%S'),
            'appointment_type': 'opd',
            'reason': 'Duplicate',
        })
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_today_endpoint(self, auth_admin):
        res = auth_admin.get('/api/appointments/today/')
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.data, list)

    def test_update_status(self, auth_admin, appointment):
        res = auth_admin.post(
            f'/api/appointments/{appointment.id}/update_status/',
            {'status': 'confirmed'}
        )
        assert res.status_code == status.HTTP_200_OK
        appointment.refresh_from_db()
        assert appointment.status == 'confirmed'

    def test_filter_by_status(self, auth_admin, appointment):
        res = auth_admin.get('/api/appointments/?status=scheduled')
        assert res.status_code == status.HTTP_200_OK

    def test_filter_by_date(self, auth_admin, appointment):
        d = appointment.appointment_date.isoformat()
        res = auth_admin.get(f'/api/appointments/?date={d}')
        assert res.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# Bill API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBillAPI:

    def test_create_bill_as_receptionist(self, auth_reception, patient, appointment):
        res = auth_reception.post('/api/bills/', {
            'patient': patient.id,
            'appointment': appointment.id,
            'consultation_charge': '400.00',
            'lab_charge': '800.00',
        })
        assert res.status_code == status.HTTP_201_CREATED
        assert float(res.data['gross_amount']) == 1200.0
        assert float(res.data['net_amount']) == 1200.0

    def test_bill_with_discount(self, auth_reception, patient):
        res = auth_reception.post('/api/bills/', {
            'patient': patient.id,
            'consultation_charge': '1000.00',
            'discount_percent': '10',
            'discount_reason': 'Staff discount',
        })
        assert res.status_code == status.HTTP_201_CREATED
        assert float(res.data['net_amount']) == 900.0
        assert float(res.data['discount_amount']) == 100.0

    def test_add_payment(self, auth_reception, patient):
        # Create bill first
        bill_res = auth_reception.post('/api/bills/', {
            'patient': patient.id,
            'consultation_charge': '500.00',
        })
        bill_id = bill_res.data['id']

        # Add payment
        pay_res = auth_reception.post(f'/api/bills/{bill_id}/add_payment/', {
            'amount': 300,
            'payment_method': 'cash',
        })
        assert pay_res.status_code == status.HTTP_200_OK
        assert pay_res.data['payment_status'] == 'partial'
        assert float(pay_res.data['amount_paid']) == 300.0

    def test_overpayment_rejected(self, auth_reception, patient):
        bill_res = auth_reception.post('/api/bills/', {
            'patient': patient.id,
            'consultation_charge': '500.00',
        })
        bill_id = bill_res.data['id']
        pay_res = auth_reception.post(f'/api/bills/{bill_id}/add_payment/', {
            'amount': 9999,  # more than bill
            'payment_method': 'cash',
        })
        assert pay_res.status_code == status.HTTP_400_BAD_REQUEST

    def test_doctor_cannot_access_bills(self, auth_doctor):
        res = auth_doctor.get('/api/bills/')
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_filter_bills_by_status(self, auth_reception, patient):
        auth_reception.post('/api/bills/', {
            'patient': patient.id,
            'consultation_charge': '400.00',
        })
        res = auth_reception.get('/api/bills/?status=unpaid')
        assert res.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# Analytics API Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyticsAPI:

    def test_summary_endpoint(self, auth_admin):
        res = auth_admin.get('/api/analytics/summary/')
        assert res.status_code == status.HTTP_200_OK
        for key in ['total_patients', 'total_doctors', 'total_appointments',
                    'total_revenue', 'unpaid_bills']:
            assert key in res.data

    def test_charts_endpoint(self, auth_admin):
        res = auth_admin.get('/api/analytics/charts/')
        assert res.status_code == status.HTTP_200_OK
        for key in ['monthly_revenue', 'top_diagnoses', 'doctor_utilization',
                    'daily_appointments', 'status_breakdown']:
            assert key in res.data

    def test_charts_with_months_param(self, auth_admin):
        res = auth_admin.get('/api/analytics/charts/?months=3')
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data['monthly_revenue']) == 3

    def test_unauthenticated_analytics_rejected(self, api_client):
        res = api_client.get('/api/analytics/summary/')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED
