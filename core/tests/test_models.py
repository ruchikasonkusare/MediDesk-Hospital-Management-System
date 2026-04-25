"""
MediDesk Model Tests
=====================
Run:  pytest core/tests/ -v --tb=short
      pytest core/tests/ -v --cov=core --cov-report=term-missing
"""
import pytest
from datetime import date, timedelta, time
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from core.models import (
    Doctor, Patient, Appointment, Bill, Prescription,
    MedicalRecord, UserProfile, VitalSigns,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def doctor(db):
    return Doctor.objects.create(
        name='Priya Sharma',
        specialization='cardiology',
        license_number='TEST-DOC-001',
        phone='9876543210',
        email='priya@test.com',
        qualification='MBBS MD',
        experience_years=10,
        consultation_fee=500,
        available_days='Mon,Tue,Wed',
    )


@pytest.fixture
def patient(db):
    return Patient.objects.create(
        name='Test Patient',
        date_of_birth=date(1990, 1, 1),
        gender='M',
        blood_group='O+',
        phone='9812345678',
        address='123 Test Street, Indore',
        emergency_contact_name='Emergency Contact',
        emergency_contact_phone='9812345679',
    )


@pytest.fixture
def appointment(db, doctor, patient):
    tomorrow = date.today() + timedelta(days=1)
    return Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment_date=tomorrow,
        appointment_time=time(10, 0),
        appointment_type='opd',
        status='scheduled',
        reason='Routine checkup',
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='testadmin', password='testpass123', email='admin@test.com')


# ─────────────────────────────────────────────────────────────────────────────
# Patient Model Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPatientModel:

    def test_patient_id_auto_generated(self, db, patient):
        """Patient ID should be auto-generated in PAT00001 format."""
        assert patient.patient_id.startswith('PAT')
        assert len(patient.patient_id) == 8

    def test_patient_age_calculated_correctly(self, db):
        """Age property returns correct age based on date_of_birth."""
        dob = date.today() - timedelta(days=365 * 30)
        p = Patient.objects.create(
            name='Age Test', date_of_birth=dob, gender='F',
            phone='9000000001', address='Test',
            emergency_contact_name='EC', emergency_contact_phone='9000000002',
        )
        assert p.age in (29, 30)  # accounts for leap year variance

    def test_patient_phone_must_be_10_digits(self, db):
        """Phone validator should reject non-10-digit numbers."""
        p = Patient(
            name='Bad Phone', date_of_birth=date(1990, 1, 1), gender='M',
            phone='123',  # too short
            address='Test', emergency_contact_name='EC',
            emergency_contact_phone='9000000001',
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_patient_phone_must_be_digits_only(self, db):
        """Phone containing letters should fail validation."""
        p = Patient(
            name='Alpha Phone', date_of_birth=date(1990, 1, 1), gender='M',
            phone='98ABCD5678',
            address='Test', emergency_contact_name='EC',
            emergency_contact_phone='9000000001',
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_patient_dob_cannot_be_future(self, db):
        """Date of birth in the future should fail validation."""
        p = Patient(
            name='Future Born', date_of_birth=date.today() + timedelta(days=1),
            gender='M', phone='9000000001',
            address='Test', emergency_contact_name='EC',
            emergency_contact_phone='9000000002',
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_patient_dob_today_invalid(self, db):
        """Date of birth set to today should fail validation."""
        p = Patient(
            name='Born Today', date_of_birth=date.today(),
            gender='M', phone='9000000001',
            address='Test', emergency_contact_name='EC',
            emergency_contact_phone='9000000002',
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_patient_valid_blood_groups(self, db):
        """All valid blood groups should be accepted."""
        for bg in ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']:
            p = Patient(
                name=f'Patient {bg}', date_of_birth=date(1990, 1, 1),
                gender='M', phone='9000000001', blood_group=bg,
                address='Test', emergency_contact_name='EC',
                emergency_contact_phone='9000000002',
            )
            p.full_clean()  # should not raise

    def test_patient_str_representation(self, db, patient):
        assert patient.name in str(patient)
        assert patient.patient_id in str(patient)

    def test_multiple_patients_get_unique_ids(self, db):
        """Each patient should get a unique patient_id."""
        p1 = Patient.objects.create(
            name='P1', date_of_birth=date(1990, 1, 1), gender='M',
            phone='9111111111', address='A',
            emergency_contact_name='EC', emergency_contact_phone='9111111112',
        )
        p2 = Patient.objects.create(
            name='P2', date_of_birth=date(1991, 2, 2), gender='F',
            phone='9222222222', address='B',
            emergency_contact_name='EC', emergency_contact_phone='9222222223',
        )
        assert p1.patient_id != p2.patient_id


# ─────────────────────────────────────────────────────────────────────────────
# Doctor Model Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDoctorModel:

    def test_doctor_str(self, db, doctor):
        assert 'Dr.' in str(doctor)
        assert doctor.name in str(doctor)

    def test_doctor_phone_must_be_10_digits(self, db):
        d = Doctor(
            name='Bad Phone Doc', specialization='general',
            license_number='BAD-001', phone='123456',
            email='bad@test.com', qualification='MBBS',
        )
        with pytest.raises(ValidationError):
            d.full_clean()

    def test_doctor_license_must_be_unique(self, db, doctor):
        with pytest.raises(Exception):  # IntegrityError
            Doctor.objects.create(
                name='Duplicate', specialization='general',
                license_number=doctor.license_number,  # duplicate!
                phone='9000000001', email='dup@test.com',
                qualification='MBBS',
            )

    def test_doctor_consultation_fee_default(self, db, doctor):
        assert doctor.consultation_fee == 500

    def test_doctor_ordering_by_name(self, db):
        Doctor.objects.create(
            name='Zara', specialization='general',
            license_number='Z-001', phone='9000000001',
            email='zara@test.com', qualification='MBBS',
        )
        Doctor.objects.create(
            name='Aisha', specialization='general',
            license_number='A-001', phone='9000000002',
            email='aisha@test.com', qualification='MBBS',
        )
        names = list(Doctor.objects.values_list('name', flat=True))
        assert names == sorted(names)


# ─────────────────────────────────────────────────────────────────────────────
# Appointment Model Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAppointmentModel:

    def test_appointment_past_datetime_rejected(self, db, doctor, patient):
        """Appointment in the past must raise ValidationError."""
        past = date.today() - timedelta(days=1)
        appt = Appointment(
            patient=patient, doctor=doctor,
            appointment_date=past,
            appointment_time=time(10, 0),
            appointment_type='opd',
            reason='Test',
        )
        with pytest.raises(ValidationError):
            appt.full_clean()

    def test_emergency_appointment_allows_past(self, db, doctor, patient):
        """Emergency appointments should be allowed even in the past."""
        past = date.today() - timedelta(days=1)
        appt = Appointment(
            patient=patient, doctor=doctor,
            appointment_date=past,
            appointment_time=time(10, 0),
            appointment_type='emergency',
            reason='Emergency case',
        )
        # Should not raise
        appt.full_clean()

    def test_double_booking_rejected(self, db, doctor, patient, appointment):
        """Same doctor, same date, same time should raise ValidationError."""
        duplicate = Appointment(
            patient=patient, doctor=doctor,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            appointment_type='opd',
            reason='Duplicate booking',
        )
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_different_time_same_doctor_allowed(self, db, doctor, patient, appointment):
        """Same doctor, same date, different time should be fine."""
        different_time = Appointment(
            patient=patient, doctor=doctor,
            appointment_date=appointment.appointment_date,
            appointment_time=time(11, 0),  # different time
            appointment_type='opd',
            reason='Different slot',
        )
        different_time.full_clean()  # should not raise

    def test_token_number_auto_assigned(self, db, appointment):
        """Token number should be auto-assigned on save."""
        assert appointment.token_number is not None
        assert appointment.token_number >= 1

    def test_appointment_status_choices(self, db, appointment):
        """Status should default to 'scheduled'."""
        assert appointment.status == 'scheduled'

    def test_appointment_str(self, db, appointment):
        s = str(appointment)
        assert appointment.patient.name in s or str(appointment.token_number) in s


# ─────────────────────────────────────────────────────────────────────────────
# Bill Model Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestBillModel:

    def test_bill_number_auto_generated(self, db, patient):
        bill = Bill.objects.create(
            patient=patient, consultation_charge=500,
        )
        assert bill.bill_number.startswith('BILL')

    def test_bill_gross_amount(self, db, patient):
        bill = Bill.objects.create(
            patient=patient,
            consultation_charge=500,
            procedure_charge=200,
            medicine_charge=150,
            lab_charge=300,
        )
        assert float(bill.gross_amount) == 1150.0

    def test_bill_discount_calculation(self, db, patient):
        bill = Bill.objects.create(
            patient=patient,
            consultation_charge=1000,
            discount_percent=10,
        )
        assert float(bill.discount_amount) == 100.0
        assert float(bill.net_amount) == 900.0

    def test_bill_balance_due(self, db, patient):
        bill = Bill.objects.create(
            patient=patient,
            consultation_charge=1000,
            amount_paid=400,
        )
        assert float(bill.balance_due) == 600.0

    def test_bill_zero_balance_when_fully_paid(self, db, patient):
        bill = Bill.objects.create(
            patient=patient,
            consultation_charge=500,
            amount_paid=500,
            payment_status='paid',
        )
        assert float(bill.balance_due) == 0.0

    def test_bill_net_amount_with_tax(self, db, patient):
        bill = Bill.objects.create(
            patient=patient,
            consultation_charge=1000,
            tax_percent=18,
        )
        assert float(bill.net_amount) == 1180.0


# ─────────────────────────────────────────────────────────────────────────────
# UserProfile Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestUserProfile:

    def test_profile_role_defaults_to_receptionist(self, db, admin_user):
        profile = UserProfile.objects.create(user=admin_user)
        assert profile.role == 'receptionist'

    def test_profile_role_helpers(self, db, admin_user):
        profile = UserProfile.objects.create(user=admin_user, role='doctor')
        assert profile.is_doctor() is True
        assert profile.is_admin() is False
        assert profile.is_receptionist() is False

    def test_profile_str(self, db, admin_user):
        profile = UserProfile.objects.create(user=admin_user, role='admin')
        assert 'Administrator' in str(profile)


# ─────────────────────────────────────────────────────────────────────────────
# VitalSigns Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestVitalSigns:

    def test_bmi_calculated(self, db, patient):
        v = VitalSigns.objects.create(
            patient=patient, weight_kg=70, height_cm=175,
        )
        assert v.bmi == pytest.approx(22.9, abs=0.2)

    def test_bmi_none_when_missing_data(self, db, patient):
        v = VitalSigns.objects.create(patient=patient, weight_kg=70)
        assert v.bmi is None

    def test_bp_display(self, db, patient):
        v = VitalSigns.objects.create(
            patient=patient, bp_systolic=120, bp_diastolic=80,
        )
        assert v.bp_display == '120/80'

    def test_bp_display_dash_when_missing(self, db, patient):
        v = VitalSigns.objects.create(patient=patient)
        assert v.bp_display == '—'
