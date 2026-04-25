from rest_framework import serializers
from django.contrib.auth.models import User
from core.models import (
    Doctor, Patient, Appointment, VitalSigns,
    MedicalRecord, Prescription, PrescriptionItem,
    Bill, Payment, UserProfile, Notification,
)


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'role']
    def get_role(self, obj):
        try:
            return obj.profile.role
        except Exception:
            return 'admin' if obj.is_superuser else 'staff'


# ── Doctor ────────────────────────────────────────────────────────────────────

class DoctorSerializer(serializers.ModelSerializer):
    specialization_display = serializers.CharField(source='get_specialization_display', read_only=True)
    total_appointments = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'specialization', 'specialization_display',
            'license_number', 'phone', 'email', 'qualification',
            'experience_years', 'consultation_fee', 'available_days',
            'slot_duration_minutes', 'morning_start', 'morning_end',
            'evening_start', 'evening_end', 'is_available',
            'total_appointments', 'created_at',
        ]

    def get_total_appointments(self, obj):
        return obj.appointments.count()

    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError('Phone must be exactly 10 digits.')
        return value


# ── Patient ───────────────────────────────────────────────────────────────────

class PatientListSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'name', 'date_of_birth', 'age',
            'gender', 'gender_display', 'blood_group', 'phone',
            'email', 'city', 'chronic_conditions', 'allergies',
            'insurance_provider', 'registered_at',
        ]


class PatientDetailSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    registered_by = UserSerializer(read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'

    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError('Phone must be exactly 10 digits.')
        return value

    def validate_emergency_contact_phone(self, value):
        if value and (not value.isdigit() or len(value) != 10):
            raise serializers.ValidationError('Emergency contact phone must be 10 digits.')
        return value

    def validate_alternate_phone(self, value):
        if value and (not value.isdigit() or len(value) != 10):
            raise serializers.ValidationError('Alternate phone must be 10 digits.')
        return value

    def validate_date_of_birth(self, value):
        from datetime import date
        if value >= date.today():
            raise serializers.ValidationError('Date of birth must be in the past.')
        return value


# ── Appointment ───────────────────────────────────────────────────────────────

class AppointmentListSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_pid  = serializers.CharField(source='patient.patient_id', read_only=True)
    doctor_name  = serializers.CharField(source='doctor.name', read_only=True)
    doctor_spec  = serializers.CharField(source='doctor.get_specialization_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display   = serializers.CharField(source='get_appointment_type_display', read_only=True)
    has_bill   = serializers.SerializerMethodField()
    has_vitals = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_pid',
            'doctor', 'doctor_name', 'doctor_spec',
            'appointment_date', 'appointment_time',
            'appointment_type', 'type_display',
            'status', 'status_display',
            'reason', 'notes', 'token_number',
            'has_bill', 'has_vitals', 'created_at',
        ]

    def get_has_bill(self, obj):
        return hasattr(obj, 'bill') and obj.bill is not None

    def get_has_vitals(self, obj):
        return hasattr(obj, 'vitals') and obj.vitals is not None


class AppointmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'patient', 'doctor', 'appointment_date', 'appointment_time',
            'appointment_type', 'reason', 'notes', 'status',
        ]

    def validate(self, data):
        from datetime import datetime
        appt_date = data.get('appointment_date')
        appt_time = data.get('appointment_time')
        appt_type = data.get('appointment_type', 'opd')
        doctor    = data.get('doctor')

        if appt_date and appt_time:
            appt_dt = datetime.combine(appt_date, appt_time)
            if appt_type != 'emergency' and appt_dt < datetime.now():
                raise serializers.ValidationError(
                    'Appointment date/time cannot be in the past.')
            if doctor:
                qs = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=appt_date,
                    appointment_time=appt_time,
                ).exclude(status='cancelled')
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        f'Dr. {doctor.name} already has an appointment at this slot.')
        return data


# ── VitalSigns ────────────────────────────────────────────────────────────────

class VitalSignsSerializer(serializers.ModelSerializer):
    bmi        = serializers.FloatField(read_only=True)
    bp_display = serializers.CharField(read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)

    class Meta:
        model = VitalSigns
        fields = [
            'id', 'appointment', 'patient', 'patient_name', 'recorded_at',
            'weight_kg', 'height_cm', 'bmi', 'temperature_f',
            'bp_systolic', 'bp_diastolic', 'bp_display',
            'pulse_bpm', 'spo2_percent', 'respiratory_rate',
            'blood_sugar_mgdl', 'notes',
        ]
        read_only_fields = ['recorded_at']


# ── Medical Record ────────────────────────────────────────────────────────────

class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    doctor_name  = serializers.CharField(source='doctor.name', read_only=True)

    class Meta:
        model = MedicalRecord
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment', 'visit_date', 'chief_complaint',
            'history_of_present_illness', 'examination_findings',
            'diagnosis', 'icd_code', 'treatment_plan',
            'lab_tests_ordered', 'follow_up_date', 'follow_up_notes',
            'is_confidential', 'created_at', 'updated_at',
        ]


# ── Prescription ──────────────────────────────────────────────────────────────

class PrescriptionItemSerializer(serializers.ModelSerializer):
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    timing_display    = serializers.CharField(source='get_timing_display',    read_only=True)
    route_display     = serializers.CharField(source='get_route_display',     read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = [
            'id', 'medicine_name', 'generic_name', 'dosage',
            'route', 'route_display', 'frequency', 'frequency_display',
            'timing', 'timing_display', 'duration_days', 'quantity',
            'instructions', 'is_dispensed',
        ]


class PrescriptionSerializer(serializers.ModelSerializer):
    items        = PrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    doctor_name  = serializers.CharField(source='doctor.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'medical_record', 'prescribed_date', 'valid_until',
            'status', 'status_display', 'notes',
            'dispensed_at', 'created_at', 'items',
        ]


# ── Bill & Payment ────────────────────────────────────────────────────────────

class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'payment_method', 'transaction_id',
            'paid_at', 'received_by', 'received_by_name', 'notes',
        ]


class BillSerializer(serializers.ModelSerializer):
    payments       = PaymentSerializer(many=True, read_only=True)
    patient_name   = serializers.CharField(source='patient.name', read_only=True)
    gross_amount   = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_amount= serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    net_amount     = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    balance_due    = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    class Meta:
        model = Bill
        fields = [
            'id', 'bill_number', 'patient', 'patient_name', 'appointment',
            'bill_date', 'consultation_charge', 'procedure_charge',
            'medicine_charge', 'lab_charge', 'room_charge',
            'other_charge', 'other_charge_label',
            'discount_percent', 'discount_reason', 'tax_percent',
            'gross_amount', 'discount_amount', 'net_amount',
            'payment_status', 'status_display', 'payment_method',
            'amount_paid', 'balance_due', 'paid_at',
            'notes', 'payments', 'created_at',
        ]


# ── Notification ──────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notif_type', 'link', 'is_read', 'created_at']
        read_only_fields = ['created_at']
