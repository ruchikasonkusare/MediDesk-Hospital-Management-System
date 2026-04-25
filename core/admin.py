from django.contrib import admin
from .models import Patient, Doctor, Appointment, MedicalRecord, Prescription, PrescriptionItem, Bill, Payment, UserProfile, VitalSigns, Notification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone', 'is_active_staff']
    list_filter = ['role', 'is_active_staff']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'name', 'age', 'gender', 'blood_group', 'phone', 'registered_at']
    search_fields = ['name', 'patient_id', 'phone']
    list_filter = ['gender', 'blood_group']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialization', 'license_number', 'phone', 'consultation_fee', 'is_available']
    list_filter = ['specialization', 'is_available']
    search_fields = ['name', 'license_number']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['token_number', 'patient', 'doctor', 'appointment_date', 'appointment_time', 'appointment_type', 'status']
    list_filter = ['status', 'appointment_type', 'appointment_date']
    search_fields = ['patient__name', 'doctor__name']

@admin.register(VitalSigns)
class VitalsAdmin(admin.ModelAdmin):
    list_display = ['patient', 'recorded_at', 'bp_display', 'pulse_bpm', 'temperature_f']

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'prescribed_date', 'status']
    inlines = [PrescriptionItemInline]
    list_filter = ['status']

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'visit_date', 'diagnosis']
    search_fields = ['patient__name', 'diagnosis']

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'patient', 'bill_date', 'net_amount', 'amount_paid', 'payment_status']
    list_filter = ['payment_status', 'bill_date']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['bill', 'amount', 'payment_method', 'paid_at']
