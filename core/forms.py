from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from datetime import datetime, date
from .models import (Patient, Doctor, Appointment, MedicalRecord, Prescription,
                     PrescriptionItem, Bill, Payment, UserProfile, VitalSigns)


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username', 'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password'}))


class PatientForm(forms.ModelForm):
    date_of_birth = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    insurance_validity = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))

    class Meta:
        model = Patient
        exclude = ['patient_id', 'registered_at', 'updated_at', 'registered_by']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'marital_status': forms.Select(attrs={'class': 'form-input'}),
            'blood_group': forms.Select(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '10-digit mobile number', 'maxlength': '10', 'pattern': '[0-9]{10}'}),
            'alternate_phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Optional alternate number', 'maxlength': '10', 'pattern': '[0-9]{10}'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'pincode': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '6-digit pincode', 'maxlength': '6', 'pattern': '[0-9]{6}'}),
            'occupation': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-input'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '10', 'pattern': '[0-9]{10}'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Spouse, Parent'}),
            'allergies': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'chronic_conditions': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'current_medications': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'past_surgeries': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'family_history': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'insurance_provider': forms.TextInput(attrs={'class': 'form-input'}),
            'insurance_number': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and not phone.isdigit():
            raise ValidationError('Phone must contain digits only.')
        if phone and len(phone) != 10:
            raise ValidationError('Phone number must be exactly 10 digits.')
        return phone

    def clean_alternate_phone(self):
        phone = self.cleaned_data.get('alternate_phone', '')
        if phone:
            if not phone.isdigit() or len(phone) != 10:
                raise ValidationError('Alternate phone must be exactly 10 digits.')
        return phone

    def clean_emergency_contact_phone(self):
        phone = self.cleaned_data.get('emergency_contact_phone', '')
        if phone and (not phone.isdigit() or len(phone) != 10):
            raise ValidationError('Emergency contact phone must be exactly 10 digits.')
        return phone


class DoctorForm(forms.ModelForm):
    morning_start = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}))
    morning_end = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}))
    evening_start = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}))
    evening_end = forms.TimeField(required=False, widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}))

    class Meta:
        model = Doctor
        exclude = ['user', 'created_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'specialization': forms.Select(attrs={'class': 'form-input'}),
            'license_number': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '10', 'pattern': '[0-9]{10}'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'qualification': forms.TextInput(attrs={'class': 'form-input'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'consultation_fee': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '0.01'}),
            'available_days': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Mon,Tue,Wed,Thu,Fri'}),
            'slot_duration_minutes': forms.NumberInput(attrs={'class': 'form-input', 'min': '5'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if not phone.isdigit() or len(phone) != 10:
            raise ValidationError('Phone number must be exactly 10 digits.')
        return phone


class AppointmentForm(forms.ModelForm):
    appointment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    appointment_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-input'}))

    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'appointment_date', 'appointment_time',
                  'appointment_type', 'reason', 'notes', 'status']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-input'}),
            'doctor': forms.Select(attrs={'class': 'form-input'}),
            'appointment_type': forms.Select(attrs={'class': 'form-input'}),
            'reason': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        appt_date = cleaned.get('appointment_date')
        appt_time = cleaned.get('appointment_time')
        appt_type = cleaned.get('appointment_type')
        doctor = cleaned.get('doctor')

        if appt_date and appt_time:
            appt_dt = datetime.combine(appt_date, appt_time)
            if appt_type != 'emergency' and appt_dt < datetime.now():
                raise ValidationError('Appointment date and time cannot be in the past.')

            if doctor:
                qs = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=appt_date,
                    appointment_time=appt_time,
                ).exclude(status='cancelled')
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise ValidationError(f'Dr. {doctor.name} already has an appointment at this date and time. Please choose a different slot.')
        return cleaned


class VitalSignsForm(forms.ModelForm):
    class Meta:
        model = VitalSigns
        fields = ['weight_kg', 'height_cm', 'temperature_f', 'bp_systolic', 'bp_diastolic',
                  'pulse_bpm', 'spo2_percent', 'respiratory_rate', 'blood_sugar_mgdl', 'notes']
        widgets = {f: forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}) for f in
                   ['weight_kg', 'height_cm', 'temperature_f', 'spo2_percent', 'blood_sugar_mgdl']}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['bp_systolic', 'bp_diastolic', 'pulse_bpm', 'respiratory_rate']:
            self.fields[f].widget = forms.NumberInput(attrs={'class': 'form-input'})
        self.fields['notes'].widget = forms.Textarea(attrs={'class': 'form-input', 'rows': 2})


class MedicalRecordForm(forms.ModelForm):
    visit_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    follow_up_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))

    class Meta:
        model = MedicalRecord
        fields = ['patient', 'doctor', 'appointment', 'visit_date', 'chief_complaint',
                  'history_of_present_illness', 'examination_findings', 'diagnosis', 'icd_code',
                  'treatment_plan', 'lab_tests_ordered', 'follow_up_date', 'follow_up_notes', 'is_confidential']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-input'}),
            'doctor': forms.Select(attrs={'class': 'form-input'}),
            'appointment': forms.Select(attrs={'class': 'form-input'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'history_of_present_illness': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'examination_findings': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'icd_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. E11.9'}),
            'treatment_plan': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'lab_tests_ordered': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'follow_up_notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class PrescriptionForm(forms.ModelForm):
    prescribed_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))
    valid_until = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))

    class Meta:
        model = Prescription
        fields = ['medical_record', 'patient', 'doctor', 'prescribed_date', 'valid_until', 'status', 'notes']
        widgets = {
            'medical_record': forms.Select(attrs={'class': 'form-input'}),
            'patient': forms.Select(attrs={'class': 'form-input'}),
            'doctor': forms.Select(attrs={'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }


class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine_name', 'generic_name', 'dosage', 'route', 'frequency',
                  'timing', 'duration_days', 'quantity', 'instructions']
        widgets = {
            'medicine_name': forms.TextInput(attrs={'class': 'form-input'}),
            'generic_name': forms.TextInput(attrs={'class': 'form-input'}),
            'dosage': forms.TextInput(attrs={'class': 'form-input'}),
            'route': forms.Select(attrs={'class': 'form-input'}),
            'frequency': forms.Select(attrs={'class': 'form-input'}),
            'timing': forms.Select(attrs={'class': 'form-input'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'instructions': forms.Textarea(attrs={'class': 'form-input', 'rows': 1}),
        }


class BillForm(forms.ModelForm):
    bill_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}))

    class Meta:
        model = Bill
        fields = ['patient', 'appointment', 'bill_date', 'consultation_charge', 'procedure_charge',
                  'medicine_charge', 'lab_charge', 'room_charge', 'other_charge', 'other_charge_label',
                  'discount_percent', 'discount_reason', 'tax_percent', 'payment_status',
                  'payment_method', 'amount_paid', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-input'}),
            'appointment': forms.Select(attrs={'class': 'form-input'}),
            'consultation_charge': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'procedure_charge': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'medicine_charge': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'lab_charge': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'room_charge': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'other_charge': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'other_charge_label': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Description'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100'}),
            'discount_reason': forms.TextInput(attrs={'class': 'form-input'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'payment_status': forms.Select(attrs={'class': 'form-input'}),
            'payment_method': forms.Select(attrs={'class': 'form-input'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
        }

    def clean(self):
        cleaned = super().clean()
        net = 0
        for f in ['consultation_charge', 'procedure_charge', 'medicine_charge', 'lab_charge', 'room_charge', 'other_charge']:
            net += float(cleaned.get(f) or 0)
        disc = float(cleaned.get('discount_percent') or 0)
        tax = float(cleaned.get('tax_percent') or 0)
        net = net * (1 - disc / 100) * (1 + tax / 100)
        paid = float(cleaned.get('amount_paid') or 0)
        if paid > net + 0.01:
            raise ValidationError(f'Amount paid (₹{paid:.2f}) cannot exceed net bill amount (₹{net:.2f}).')
        return cleaned


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-input'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'UPI ref / card last 4 / cheque no.'}),
            'notes': forms.TextInput(attrs={'class': 'form-input'}),
        }


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-input'}))

    class Meta:
        model = UserProfile
        fields = ['role', 'phone', 'is_active_staff']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '10', 'pattern': '[0-9]{10}'}),
            'is_active_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
