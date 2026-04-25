from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from datetime import date, timedelta, datetime
from functools import wraps

from .models import (Patient, Doctor, Appointment, MedicalRecord, Prescription,
                     PrescriptionItem, Bill, Payment, UserProfile, VitalSigns, Notification)
from .forms import (LoginForm, PatientForm, DoctorForm, AppointmentForm,
                    MedicalRecordForm, PrescriptionForm, PrescriptionItemForm,
                    BillForm, PaymentForm, UserProfileForm, VitalSignsForm)


# ─── Role helpers ──────────────────────────────────────────────────────────────

def get_role(user):
    try:
        return user.profile.role
    except Exception:
        return 'admin' if user.is_superuser else 'receptionist'

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            r = get_role(request.user)
            if r not in roles and not request.user.is_superuser:
                messages.error(request, f'Access denied. You need role: {", ".join(roles)}.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def can(user, action):
    """Returns True if user has permission for the given action."""
    role = get_role(user)
    if user.is_superuser or role == 'admin':
        return True
    perms = {
        'receptionist': ['view_patients', 'add_patient', 'edit_patient',
                         'view_appointments', 'add_appointment', 'edit_appointment',
                         'view_bills', 'add_bill', 'add_payment'],
        'doctor': ['view_patients', 'view_appointments', 'add_record', 'edit_record',
                   'view_records', 'add_prescription', 'view_prescriptions',
                   'add_vitals', 'view_bills'],
        'nurse': ['view_patients', 'view_appointments', 'add_vitals', 'view_records'],
        'pharmacist': ['view_prescriptions', 'dispense_prescription'],
    }
    return action in perms.get(role, [])

def notify(user, title, message, notif_type='system', link=''):
    Notification.objects.create(user=user, title=title, message=message,
                                notif_type=notif_type, link=link)


# ─── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = date.today()
    role = get_role(request.user)

    # Doctor sees only their own stats
    if role == 'doctor':
        try:
            doctor = request.user.doctor_profile
        except Exception:
            doctor = None

        today_appts = Appointment.objects.filter(doctor=doctor, appointment_date=today).order_by('appointment_time') if doctor else []
        pending_appts = Appointment.objects.filter(doctor=doctor, appointment_date__gte=today, status__in=['scheduled','confirmed']).select_related('patient').order_by('appointment_date','appointment_time')[:8] if doctor else []
        my_patients = Patient.objects.filter(appointments__doctor=doctor).distinct().count() if doctor else 0
        pending_rx = Prescription.objects.filter(doctor=doctor, status='active').count() if doctor else 0
        context = {
            'role': role, 'today': today,
            'today_appts': today_appts, 'pending_appts': pending_appts,
            'my_patients': my_patients, 'pending_rx': pending_rx,
            'today_count': len(list(today_appts)),
        }
        return render(request, 'core/dashboard.html', context)

    # Pharmacist dashboard
    if role == 'pharmacist':
        pending_rx = Prescription.objects.filter(status='active').select_related('patient','doctor').order_by('-prescribed_date')[:10]
        context = {'role': role, 'today': today, 'pending_rx': pending_rx, 'pending_count': Prescription.objects.filter(status='active').count()}
        return render(request, 'core/dashboard.html', context)

    # Admin / receptionist / nurse full dashboard
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.filter(is_available=True).count()
    today_appointments = Appointment.objects.filter(appointment_date=today).count()
    pending_appointments = Appointment.objects.filter(status__in=['scheduled','confirmed'], appointment_date__gte=today).count()
    active_prescriptions = Prescription.objects.filter(status='active').count()
    unpaid_bills = Bill.objects.filter(payment_status__in=['unpaid','partial']).count()
    total_revenue_today = Bill.objects.filter(bill_date=today).aggregate(s=Sum('amount_paid'))['s'] or 0
    total_revenue_month = Bill.objects.filter(bill_date__month=today.month, bill_date__year=today.year).aggregate(s=Sum('amount_paid'))['s'] or 0

    recent_appointments = Appointment.objects.select_related('patient','doctor').order_by('-created_at')[:8]
    upcoming = Appointment.objects.select_related('patient','doctor').filter(
        appointment_date__gte=today, status__in=['scheduled','confirmed']
    ).order_by('appointment_date','appointment_time')[:6]
    recent_patients = Patient.objects.order_by('-registered_at')[:5]
    unpaid_bill_list = Bill.objects.filter(payment_status__in=['unpaid','partial']).select_related('patient').order_by('-created_at')[:5]

    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = Appointment.objects.filter(appointment_date=d).count()
        chart_data.append({'date': d.strftime('%a'), 'count': count})

    context = {
        'role': role, 'today': today,
        'total_patients': total_patients, 'total_doctors': total_doctors,
        'today_appointments': today_appointments, 'pending_appointments': pending_appointments,
        'active_prescriptions': active_prescriptions, 'unpaid_bills': unpaid_bills,
        'total_revenue_today': total_revenue_today, 'total_revenue_month': total_revenue_month,
        'recent_appointments': recent_appointments, 'upcoming': upcoming,
        'recent_patients': recent_patients, 'unpaid_bill_list': unpaid_bill_list,
        'chart_data': chart_data,
    }
    return render(request, 'core/dashboard.html', context)


# ─── Patients ─────────────────────────────────────────────────────────────────

@login_required
def patient_list(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.all()
    role = get_role(request.user)
    if role == 'doctor':
        try:
            doc = request.user.doctor_profile
            patients = patients.filter(appointments__doctor=doc).distinct()
        except Exception:
            pass
    if q:
        patients = patients.filter(Q(name__icontains=q) | Q(patient_id__icontains=q) | Q(phone__icontains=q))
    return render(request, 'core/patient_list.html', {'patients': patients, 'q': q, 'role': role})

@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    role = get_role(request.user)
    if role == 'doctor':
        try:
            doc = request.user.doctor_profile
            if not patient.appointments.filter(doctor=doc).exists():
                messages.error(request, 'You can only view your own patients.')
                return redirect('patient_list')
        except Exception:
            pass
    appointments = patient.appointments.select_related('doctor').order_by('-appointment_date')[:10]
    records = patient.medical_records.select_related('doctor').order_by('-visit_date')[:10]
    prescriptions = patient.prescriptions.select_related('doctor').prefetch_related('items').order_by('-prescribed_date')[:10]
    bills = patient.bills.order_by('-bill_date')[:10]
    vitals = patient.vitals.order_by('-recorded_at')[:5]
    total_billed = patient.bills.aggregate(s=Sum('amount_paid'))['s'] or 0
    outstanding = sum(b.balance_due for b in patient.bills.all())
    return render(request, 'core/patient_detail.html', {
        'patient': patient, 'appointments': appointments, 'records': records,
        'prescriptions': prescriptions, 'bills': bills, 'vitals': vitals,
        'total_billed': total_billed, 'outstanding': outstanding, 'role': role,
    })

@login_required
@role_required('admin', 'receptionist')
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.registered_by = request.user
            p.save()
            messages.success(request, f'Patient {p.name} ({p.patient_id}) registered successfully!')
            return redirect('patient_detail', pk=p.pk)
    else:
        form = PatientForm()
    return render(request, 'core/patient_form.html', {'form': form, 'title': 'Register New Patient'})

@login_required
@role_required('admin', 'receptionist')
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient record updated.')
            return redirect('patient_detail', pk=pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'core/patient_form.html', {'form': form, 'title': 'Edit Patient', 'patient': patient})


# ─── Doctors ─────────────────────────────────────────────────────────────────

@login_required
def doctor_list(request):
    q = request.GET.get('q', '')
    spec = request.GET.get('spec', '')
    doctors = Doctor.objects.all()
    if q:
        doctors = doctors.filter(Q(name__icontains=q) | Q(specialization__icontains=q))
    if spec:
        doctors = doctors.filter(specialization=spec)
    specializations = Doctor.SPECIALIZATIONS
    return render(request, 'core/doctor_list.html', {'doctors': doctors, 'q': q, 'spec': spec, 'specializations': specializations})

@login_required
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    appointments = doctor.appointments.select_related('patient').order_by('-appointment_date')[:10]
    records = doctor.medical_records.select_related('patient').order_by('-visit_date')[:5]
    total_patients = Patient.objects.filter(appointments__doctor=doctor).distinct().count()
    total_completed = doctor.appointments.filter(status='completed').count()
    return render(request, 'core/doctor_detail.html', {
        'doctor': doctor, 'appointments': appointments, 'records': records,
        'total_patients': total_patients, 'total_completed': total_completed,
    })

@login_required
@role_required('admin')
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            doc = form.save()
            messages.success(request, f'Dr. {doc.name} added successfully!')
            return redirect('doctor_detail', pk=doc.pk)
    else:
        form = DoctorForm()
    return render(request, 'core/doctor_form.html', {'form': form, 'title': 'Add New Doctor'})

@login_required
@role_required('admin')
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor profile updated.')
            return redirect('doctor_detail', pk=pk)
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'core/doctor_form.html', {'form': form, 'title': 'Edit Doctor', 'doctor': doctor})


# ─── Appointments ─────────────────────────────────────────────────────────────

@login_required
def appointment_list(request):
    role = get_role(request.user)
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    appointments = Appointment.objects.select_related('patient', 'doctor').all()
    if role == 'doctor':
        try:
            appointments = appointments.filter(doctor=request.user.doctor_profile)
        except Exception:
            pass
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
    appointments = appointments.order_by('-appointment_date', 'appointment_time')
    return render(request, 'core/appointment_list.html', {
        'appointments': appointments, 'status_filter': status_filter,
        'date_filter': date_filter, 'status_choices': Appointment.STATUS_CHOICES, 'role': role,
    })

@login_required
@role_required('admin', 'receptionist')
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.booked_by = request.user
            appt.full_clean()
            appt.save()
            # Notify doctor
            try:
                doc_user = appt.doctor.user
                if doc_user:
                    notify(doc_user, 'New Appointment', f'{appt.patient.name} booked for {appt.appointment_date} at {appt.appointment_time}', 'appointment', f'/appointments/')
            except Exception:
                pass
            messages.success(request, f'Appointment scheduled! Token #{appt.token_number}')
            return redirect('appointment_list')
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f'{e}')
    else:
        form = AppointmentForm()
        if request.GET.get('patient'):
            form.fields['patient'].initial = request.GET['patient']
        if request.GET.get('doctor'):
            form.fields['doctor'].initial = request.GET['doctor']
    return render(request, 'core/appointment_form.html', {'form': form, 'title': 'Schedule Appointment'})

@login_required
@role_required('admin', 'receptionist')
def appointment_edit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated.')
            return redirect('appointment_list')
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, e)
    else:
        form = AppointmentForm(instance=appt)
    return render(request, 'core/appointment_form.html', {'form': form, 'title': 'Edit Appointment', 'appt': appt})

@login_required
@require_POST
def appointment_status_update(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(Appointment.STATUS_CHOICES):
        appt.status = new_status
        appt.save()
        messages.success(request, f'Status updated to {appt.get_status_display()}')
    return redirect(request.POST.get('next', 'appointment_list'))


# ─── Vitals ───────────────────────────────────────────────────────────────────

@login_required
@role_required('admin', 'doctor', 'nurse')
def vitals_create(request, appointment_pk):
    appt = get_object_or_404(Appointment, pk=appointment_pk)
    existing = VitalSigns.objects.filter(appointment=appt).first()
    if request.method == 'POST':
        form = VitalSignsForm(request.POST, instance=existing)
        if form.is_valid():
            v = form.save(commit=False)
            v.patient = appt.patient
            v.appointment = appt
            v.recorded_by = request.user
            v.save()
            messages.success(request, 'Vital signs recorded.')
            return redirect('appointment_list')
    else:
        form = VitalSignsForm(instance=existing)
    return render(request, 'core/vitals_form.html', {'form': form, 'appt': appt, 'existing': existing})


# ─── Medical Records ──────────────────────────────────────────────────────────

@login_required
def record_list(request):
    role = get_role(request.user)
    q = request.GET.get('q', '')
    records = MedicalRecord.objects.select_related('patient', 'doctor').all()
    if role == 'doctor':
        try:
            records = records.filter(doctor=request.user.doctor_profile)
        except Exception:
            pass
    elif role not in ('admin', 'receptionist', 'nurse'):
        records = records.none()
    if q:
        records = records.filter(Q(patient__name__icontains=q) | Q(diagnosis__icontains=q))
    records = records.filter(is_confidential=False) if role == 'nurse' else records
    return render(request, 'core/record_list.html', {'records': records.order_by('-visit_date'), 'q': q, 'role': role})

@login_required
@role_required('admin', 'doctor')
def record_create(request):
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            rec = form.save()
            messages.success(request, 'Medical record created.')
            return redirect('record_detail', pk=rec.pk)
    else:
        form = MedicalRecordForm()
        if request.GET.get('patient'):
            form.fields['patient'].initial = request.GET['patient']
        if request.GET.get('appointment'):
            form.fields['appointment'].initial = request.GET['appointment']
        role = get_role(request.user)
        if role == 'doctor':
            try:
                form.fields['doctor'].initial = request.user.doctor_profile.pk
            except Exception:
                pass
    return render(request, 'core/record_form.html', {'form': form, 'title': 'New Medical Record'})

@login_required
def record_detail(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    role = get_role(request.user)
    if role == 'doctor':
        try:
            if record.doctor != request.user.doctor_profile:
                messages.error(request, 'Access denied.')
                return redirect('record_list')
        except Exception:
            pass
    if record.is_confidential and role not in ('admin', 'doctor'):
        messages.error(request, 'This record is confidential.')
        return redirect('record_list')
    prescriptions = record.prescriptions.prefetch_related('items').all()
    return render(request, 'core/record_detail.html', {'record': record, 'prescriptions': prescriptions, 'role': role})

@login_required
@role_required('admin', 'doctor')
def record_edit(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Record updated.')
            return redirect('record_detail', pk=pk)
    else:
        form = MedicalRecordForm(instance=record)
    return render(request, 'core/record_form.html', {'form': form, 'title': 'Edit Medical Record', 'record': record})


# ─── Prescriptions ────────────────────────────────────────────────────────────

@login_required
def prescription_list(request):
    role = get_role(request.user)
    status_filter = request.GET.get('status', '')
    rxs = Prescription.objects.select_related('patient', 'doctor').prefetch_related('items').order_by('-prescribed_date')
    if role == 'doctor':
        try:
            rxs = rxs.filter(doctor=request.user.doctor_profile)
        except Exception:
            pass
    if status_filter:
        rxs = rxs.filter(status=status_filter)
    return render(request, 'core/prescription_list.html', {'prescriptions': rxs, 'status_filter': status_filter, 'role': role})

@login_required
@role_required('admin', 'doctor')
def prescription_create(request):
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        if form.is_valid():
            rx = form.save()
            med_names = request.POST.getlist('medicine_name')
            dosages = request.POST.getlist('dosage')
            generics = request.POST.getlist('generic_name')
            routes = request.POST.getlist('route')
            freqs = request.POST.getlist('frequency')
            timings = request.POST.getlist('timing')
            durations = request.POST.getlist('duration_days')
            quantities = request.POST.getlist('quantity')
            instr_list = request.POST.getlist('instructions')
            for i, name in enumerate(med_names):
                if name.strip():
                    PrescriptionItem.objects.create(
                        prescription=rx,
                        medicine_name=name,
                        generic_name=generics[i] if i < len(generics) else '',
                        dosage=dosages[i] if i < len(dosages) else '',
                        route=routes[i] if i < len(routes) else 'oral',
                        frequency=freqs[i] if i < len(freqs) else 'once_daily',
                        timing=timings[i] if i < len(timings) else '',
                        duration_days=int(durations[i]) if i < len(durations) and durations[i] else 7,
                        quantity=int(quantities[i]) if i < len(quantities) and quantities[i] else 1,
                        instructions=instr_list[i] if i < len(instr_list) else '',
                    )
            messages.success(request, 'Prescription saved.')
            return redirect('prescription_detail', pk=rx.pk)
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, e)
    else:
        form = PrescriptionForm()
        if request.GET.get('patient'):
            form.fields['patient'].initial = request.GET['patient']
        if request.GET.get('record'):
            form.fields['medical_record'].initial = request.GET['record']
    return render(request, 'core/prescription_form.html', {
        'form': form, 'title': 'New Prescription',
        'frequency_choices': PrescriptionItem.FREQUENCY_CHOICES,
        'timing_choices': PrescriptionItem.TIMING_CHOICES,
        'route_choices': PrescriptionItem.ROUTE_CHOICES,
    })

@login_required
def prescription_detail(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    role = get_role(request.user)
    return render(request, 'core/prescription_detail.html', {'prescription': rx, 'role': role})

@login_required
@role_required('admin', 'pharmacist')
@require_POST
def prescription_dispense(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    rx.status = 'dispensed'
    rx.dispensed_by = request.user
    rx.dispensed_at = timezone.now()
    rx.items.all().update(is_dispensed=True)
    rx.save()
    messages.success(request, f'Prescription {rx} marked as dispensed.')
    return redirect('prescription_detail', pk=pk)


# ─── Billing ──────────────────────────────────────────────────────────────────

@login_required
@role_required('admin', 'receptionist')
def bill_list(request):
    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    bills = Bill.objects.select_related('patient').order_by('-bill_date', '-created_at')
    if status_filter:
        bills = bills.filter(payment_status=status_filter)
    if q:
        bills = bills.filter(Q(patient__name__icontains=q) | Q(bill_number__icontains=q))
    total_collected = bills.aggregate(s=Sum('amount_paid'))['s'] or 0
    return render(request, 'core/bill_list.html', {
        'bills': bills, 'status_filter': status_filter, 'q': q,
        'status_choices': Bill.PAYMENT_STATUS, 'total_collected': total_collected,
    })

@login_required
@role_required('admin', 'receptionist')
def bill_create(request):
    if request.method == 'POST':
        form = BillForm(request.POST)
        if form.is_valid():
            bill = form.save(commit=False)
            bill.generated_by = request.user
            bill.save()
            # Auto-update payment status
            _refresh_bill_status(bill)
            messages.success(request, f'Bill {bill.bill_number} created.')
            return redirect('bill_detail', pk=bill.pk)
        else:
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, e)
    else:
        form = BillForm()
        if request.GET.get('patient'):
            form.fields['patient'].initial = request.GET['patient']
        if request.GET.get('appointment'):
            apt_pk = request.GET['appointment']
            form.fields['appointment'].initial = apt_pk
            try:
                appt = Appointment.objects.get(pk=apt_pk)
                form.fields['consultation_charge'].initial = appt.doctor.consultation_fee
                form.fields['patient'].initial = appt.patient.pk
            except Exception:
                pass
    return render(request, 'core/bill_form.html', {'form': form, 'title': 'Generate Bill'})

@login_required
@role_required('admin', 'receptionist')
def bill_detail(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    payments = bill.payments.all()
    payment_form = PaymentForm()
    return render(request, 'core/bill_detail.html', {
        'bill': bill, 'payments': payments, 'payment_form': payment_form,
    })

@login_required
@role_required('admin', 'receptionist')
@require_POST
def bill_add_payment(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    form = PaymentForm(request.POST)
    if form.is_valid():
        amount = form.cleaned_data['amount']
        if amount > bill.balance_due + 0.01:
            messages.error(request, f'Payment ₹{amount} exceeds balance due ₹{bill.balance_due:.2f}')
        else:
            payment = form.save(commit=False)
            payment.bill = bill
            payment.received_by = request.user
            payment.save()
            bill.amount_paid = (bill.amount_paid or 0) + amount
            if bill.amount_paid >= bill.net_amount:
                bill.payment_status = 'paid'
                bill.paid_at = timezone.now()
            elif bill.amount_paid > 0:
                bill.payment_status = 'partial'
            bill.payment_method = form.cleaned_data['payment_method']
            bill.save()
            messages.success(request, f'Payment of ₹{amount} recorded.')
    else:
        for field, errs in form.errors.items():
            for e in errs:
                messages.error(request, e)
    return redirect('bill_detail', pk=pk)

def _refresh_bill_status(bill):
    if bill.amount_paid >= bill.net_amount:
        bill.payment_status = 'paid'
        bill.paid_at = timezone.now()
    elif bill.amount_paid > 0:
        bill.payment_status = 'partial'
    else:
        bill.payment_status = 'unpaid'
    bill.save()


# ─── Staff Management ─────────────────────────────────────────────────────────

@login_required
@role_required('admin')
def staff_list(request):
    profiles = UserProfile.objects.select_related('user').all().order_by('role', 'user__first_name')
    return render(request, 'core/staff_list.html', {'profiles': profiles})

@login_required
@role_required('admin')
def staff_create(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'receptionist')
        phone = request.POST.get('phone', '').strip()

        errors = []
        if not username:
            errors.append('Username is required.')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already taken.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if phone and (not phone.isdigit() or len(phone) != 10):
            errors.append('Phone must be exactly 10 digits.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            user = User.objects.create_user(username=username, password=password,
                                            first_name=first_name, last_name=last_name, email=email)
            UserProfile.objects.create(user=user, role=role, phone=phone)
            messages.success(request, f'Staff member {user.get_full_name() or username} created.')
            return redirect('staff_list')
    roles = UserProfile.ROLE_CHOICES
    return render(request, 'core/staff_form.html', {'title': 'Add Staff Member', 'roles': roles})

@login_required
@role_required('admin')
def staff_edit(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            user = profile.user
            user.first_name = form.cleaned_data.get('first_name', user.first_name)
            user.last_name = form.cleaned_data.get('last_name', user.last_name)
            user.email = form.cleaned_data.get('email', user.email)
            user.save()
            form.save()
            messages.success(request, 'Staff profile updated.')
            return redirect('staff_list')
    else:
        form = UserProfileForm(instance=profile, initial={
            'first_name': profile.user.first_name,
            'last_name': profile.user.last_name,
            'email': profile.user.email,
        })
    return render(request, 'core/staff_edit.html', {'form': form, 'profile': profile})


# ─── Notifications ────────────────────────────────────────────────────────────

@login_required
def notifications_view(request):
    notifs = request.user.notifications.all()
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifs})

@login_required
@require_POST
def mark_notification_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save()
    return JsonResponse({'ok': True})


# ─── API ──────────────────────────────────────────────────────────────────────

@login_required
def api_patient_search(request):
    q = request.GET.get('q', '')
    patients = Patient.objects.filter(
        Q(name__icontains=q) | Q(patient_id__icontains=q) | Q(phone__icontains=q)
    ).values('id', 'name', 'patient_id', 'phone')[:10]
    return JsonResponse({'results': list(patients)})

@login_required
def api_doctor_slots(request):
    doctor_id = request.GET.get('doctor_id')
    appt_date = request.GET.get('date')
    if not doctor_id or not appt_date:
        return JsonResponse({'slots': []})
    booked = list(Appointment.objects.filter(
        doctor_id=doctor_id, appointment_date=appt_date
    ).exclude(status='cancelled').values_list('appointment_time', flat=True))
    booked_str = [t.strftime('%H:%M') for t in booked]
    return JsonResponse({'booked_slots': booked_str})

@login_required
def api_unread_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})
