from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from datetime import date, datetime


phone_validator = RegexValidator(regex=r'^\d{10}$', message='Phone number must be exactly 10 digits.')
pincode_validator = RegexValidator(r'^\d{6}$', 'Pincode must be exactly 6 digits.')


def validate_dob(value):
    if value >= date.today():
        raise ValidationError('Date of birth must be in the past.')
    if (date.today() - value).days // 365 > 120:
        raise ValidationError('Please enter a valid date of birth.')


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'), ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'), ('pharmacist', 'Pharmacist'), ('nurse', 'Nurse'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='receptionist')
    phone = models.CharField(max_length=10, validators=[phone_validator], blank=True)
    is_active_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    def is_admin(self): return self.role == 'admin'
    def is_doctor(self): return self.role == 'doctor'
    def is_receptionist(self): return self.role == 'receptionist'
    def is_pharmacist(self): return self.role == 'pharmacist'
    def is_nurse(self): return self.role == 'nurse'


class Doctor(models.Model):
    SPECIALIZATIONS = [
        ('general', 'General Physician'), ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'), ('orthopedics', 'Orthopedics'),
        ('pediatrics', 'Pediatrics'), ('dermatology', 'Dermatology'),
        ('gynecology', 'Gynecology & Obstetrics'), ('psychiatry', 'Psychiatry'),
        ('ophthalmology', 'Ophthalmology'), ('ent', 'ENT'),
        ('oncology', 'Oncology'), ('radiology', 'Radiology'),
        ('urology', 'Urology'), ('nephrology', 'Nephrology'),
        ('gastroenterology', 'Gastroenterology'), ('endocrinology', 'Endocrinology'),
        ('pulmonology', 'Pulmonology'), ('rheumatology', 'Rheumatology'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='doctor_profile')
    name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=50, choices=SPECIALIZATIONS)
    license_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    email = models.EmailField(unique=True)
    qualification = models.CharField(max_length=300)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=500.00)
    available_days = models.CharField(max_length=200, default='Mon,Tue,Wed,Thu,Fri')
    slot_duration_minutes = models.PositiveIntegerField(default=15)
    morning_start = models.TimeField(null=True, blank=True)
    morning_end = models.TimeField(null=True, blank=True)
    evening_start = models.TimeField(null=True, blank=True)
    evening_end = models.TimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.name} ({self.get_specialization_display()})"

    class Meta:
        ordering = ['name']


class Patient(models.Model):
    BLOOD_GROUPS = [('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('O+','O+'),('O-','O-'),('AB+','AB+'),('AB-','AB-')]
    GENDER_CHOICES = [('M','Male'),('F','Female'),('O','Other')]
    MARITAL_STATUS = [('single','Single'),('married','Married'),('divorced','Divorced'),('widowed','Widowed')]

    patient_id = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    date_of_birth = models.DateField(validators=[validate_dob])
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS, blank=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUPS, blank=True)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    alternate_phone = models.CharField(max_length=10, validators=[phone_validator], blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=6, blank=True, validators=[pincode_validator])
    occupation = models.CharField(max_length=100, blank=True)
    emergency_contact_name = models.CharField(max_length=200)
    emergency_contact_phone = models.CharField(max_length=10, validators=[phone_validator])
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    allergies = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    past_surgeries = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    insurance_provider = models.CharField(max_length=200, blank=True)
    insurance_number = models.CharField(max_length=100, blank=True)
    insurance_validity = models.DateField(null=True, blank=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_patients')
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.patient_id:
            last = Patient.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.patient_id = f'PAT{num:05d}'
        super().save(*args, **kwargs)

    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def __str__(self):
        return f"{self.name} ({self.patient_id})"

    class Meta:
        ordering = ['-registered_at']


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled','Scheduled'), ('confirmed','Confirmed'), ('in_progress','In Progress'),
        ('completed','Completed'), ('cancelled','Cancelled'), ('no_show','No Show'),
    ]
    TYPE_CHOICES = [
        ('opd','OPD Consultation'), ('follow_up','Follow-up'), ('emergency','Emergency'),
        ('procedure','Procedure'), ('teleconsult','Teleconsultation'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='opd')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    reason = models.TextField()
    notes = models.TextField(blank=True)
    token_number = models.PositiveIntegerField(null=True, blank=True)
    booked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='booked_appointments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.appointment_date and self.appointment_time:
            appt_dt = datetime.combine(self.appointment_date, self.appointment_time)
            # Allow emergencies in the past
            if self.appointment_type != 'emergency' and appt_dt < datetime.now():
                raise ValidationError('Appointment date and time cannot be in the past.')
        if self.doctor_id and self.appointment_date and self.appointment_time:
            qs = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                appointment_time=self.appointment_time,
            ).exclude(pk=self.pk).exclude(status='cancelled')
            if qs.exists():
                raise ValidationError(f'Dr. {self.doctor.name} already has an appointment at this time.')

    def save(self, *args, **kwargs):
        if not self.token_number:
            existing = Appointment.objects.filter(
                doctor=self.doctor, appointment_date=self.appointment_date
            ).exclude(pk=self.pk).count()
            self.token_number = existing + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token #{self.token_number} – {self.patient.name} → Dr. {self.doctor.name}"

    class Meta:
        ordering = ['-appointment_date', 'appointment_time']


class VitalSigns(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='vitals', null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_vitals')
    recorded_at = models.DateTimeField(default=timezone.now)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    temperature_f = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    bp_systolic = models.PositiveIntegerField(null=True, blank=True)
    bp_diastolic = models.PositiveIntegerField(null=True, blank=True)
    pulse_bpm = models.PositiveIntegerField(null=True, blank=True)
    spo2_percent = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    blood_sugar_mgdl = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)

    @property
    def bmi(self):
        if self.weight_kg and self.height_cm and self.height_cm > 0:
            h = float(self.height_cm) / 100
            return round(float(self.weight_kg) / (h * h), 1)
        return None

    @property
    def bp_display(self):
        if self.bp_systolic and self.bp_diastolic:
            return f"{self.bp_systolic}/{self.bp_diastolic}"
        return '—'

    def __str__(self):
        return f"Vitals: {self.patient.name} @ {self.recorded_at.strftime('%d %b %Y')}"

    class Meta:
        ordering = ['-recorded_at']


class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='medical_records')
    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_record')
    visit_date = models.DateField(default=date.today)
    chief_complaint = models.TextField()
    history_of_present_illness = models.TextField(blank=True)
    examination_findings = models.TextField(blank=True)
    diagnosis = models.TextField()
    icd_code = models.CharField(max_length=20, blank=True)
    treatment_plan = models.TextField()
    lab_tests_ordered = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    is_confidential = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Record: {self.patient.name} – {self.visit_date}"

    class Meta:
        ordering = ['-visit_date']


class Prescription(models.Model):
    STATUS_CHOICES = [
        ('active','Active'), ('dispensed','Dispensed'),
        ('completed','Completed'), ('cancelled','Cancelled'),
    ]
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    prescribed_date = models.DateField(default=date.today)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_prescriptions')
    dispensed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rx: {self.patient.name} – Dr. {self.doctor.name} – {self.prescribed_date}"

    class Meta:
        ordering = ['-prescribed_date']


class PrescriptionItem(models.Model):
    FREQUENCY_CHOICES = [
        ('once_daily','Once Daily (OD)'), ('twice_daily','Twice Daily (BD)'),
        ('thrice_daily','Thrice Daily (TDS)'), ('four_times','Four Times (QID)'),
        ('every_6h','Every 6 Hours'), ('every_8h','Every 8 Hours'),
        ('every_12h','Every 12 Hours'), ('as_needed','As Needed (SOS)'),
        ('weekly','Weekly'), ('alternate_day','Alternate Day'), ('stat','Immediately (STAT)'),
    ]
    TIMING_CHOICES = [
        ('before_food','Before Food'), ('after_food','After Food'), ('with_food','With Food'),
        ('bedtime','At Bedtime'), ('empty_stomach','Empty Stomach'),
        ('morning','Morning'), ('evening','Evening'),
    ]
    ROUTE_CHOICES = [
        ('oral','Oral'), ('iv','IV'), ('im','IM'), ('sc','SC'),
        ('topical','Topical'), ('inhaled','Inhaled'), ('sublingual','Sublingual'),
        ('nasal','Nasal'), ('ophthalmic','Ophthalmic'),
    ]
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200, blank=True)
    dosage = models.CharField(max_length=100)
    route = models.CharField(max_length=20, choices=ROUTE_CHOICES, default='oral')
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    timing = models.CharField(max_length=20, choices=TIMING_CHOICES, blank=True)
    duration_days = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True)
    is_dispensed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.medicine_name} – {self.dosage}"


class Bill(models.Model):
    PAYMENT_STATUS = [
        ('unpaid','Unpaid'), ('partial','Partially Paid'),
        ('paid','Paid'), ('waived','Waived'), ('refunded','Refunded'),
    ]
    PAYMENT_METHOD = [
        ('cash','Cash'), ('card','Debit/Credit Card'), ('upi','UPI'),
        ('netbanking','Net Banking'), ('insurance','Insurance'), ('cheque','Cheque'),
    ]

    bill_number = models.CharField(max_length=20, unique=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='bills')
    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='bill')
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_bills')
    bill_date = models.DateField(default=date.today)
    consultation_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    procedure_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medicine_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lab_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    room_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_charge_label = models.CharField(max_length=100, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=200, blank=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.bill_number:
            last = Bill.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.bill_number = f'BILL{num:06d}'
        super().save(*args, **kwargs)

    @property
    def gross_amount(self):
        return (self.consultation_charge + self.procedure_charge + self.medicine_charge +
                self.lab_charge + self.room_charge + self.other_charge)

    @property
    def discount_amount(self):
        return round(self.gross_amount * self.discount_percent / 100, 2)

    @property
    def taxable_amount(self):
        return self.gross_amount - self.discount_amount

    @property
    def tax_amount(self):
        return round(self.taxable_amount * self.tax_percent / 100, 2)

    @property
    def net_amount(self):
        return self.taxable_amount + self.tax_amount

    @property
    def balance_due(self):
        return max(self.net_amount - self.amount_paid, 0)

    def __str__(self):
        return f"{self.bill_number} – {self.patient.name}"

    class Meta:
        ordering = ['-bill_date', '-created_at']


class Payment(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Bill.PAYMENT_METHOD)
    transaction_id = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_payments')
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"₹{self.amount} for {self.bill.bill_number}"

    class Meta:
        ordering = ['-paid_at']


class Notification(models.Model):
    TYPE_CHOICES = [
        ('appointment','Appointment'), ('billing','Billing'),
        ('record','Medical Record'), ('prescription','Prescription'), ('system','System'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
