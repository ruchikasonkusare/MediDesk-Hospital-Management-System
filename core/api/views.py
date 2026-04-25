from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import date, timedelta, datetime

from core.models import (
    Doctor, Patient, Appointment, VitalSigns, MedicalRecord,
    Prescription, PrescriptionItem, Bill, Payment, Notification,
)
from .serializers import (
    DoctorSerializer, PatientListSerializer, PatientDetailSerializer,
    AppointmentListSerializer, AppointmentWriteSerializer,
    VitalSignsSerializer, MedicalRecordSerializer,
    PrescriptionSerializer, BillSerializer, PaymentSerializer,
    NotificationSerializer,
)
from .permissions import IsAdminRole, IsAdminOrReceptionist, get_role


# ── Doctor ViewSet ─────────────────────────────────────────────────────────────

class DoctorViewSet(viewsets.ModelViewSet):
    """
    GET    /api/doctors/           — list doctors (all authenticated)
    POST   /api/doctors/           — create (admin only)
    GET    /api/doctors/{id}/      — detail
    PUT    /api/doctors/{id}/      — update (admin only)
    DELETE /api/doctors/{id}/      — delete (admin only)
    GET    /api/doctors/{id}/appointments/ — doctor's appointments
    GET    /api/doctors/{id}/stats/        — performance stats
    """
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'specialization', 'license_number', 'email']
    ordering_fields = ['name', 'experience_years', 'consultation_fee']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Doctor.objects.all()
        if self.request.query_params.get('specialization'):
            qs = qs.filter(specialization=self.request.query_params['specialization'])
        if self.request.query_params.get('available'):
            qs = qs.filter(is_available=self.request.query_params['available'] == 'true')
        return qs

    @action(detail=True, methods=['get'])
    def appointments(self, request, pk=None):
        doctor = self.get_object()
        qs = doctor.appointments.select_related('patient').order_by(
            '-appointment_date', 'appointment_time')
        if request.query_params.get('date'):
            qs = qs.filter(appointment_date=request.query_params['date'])
        if request.query_params.get('status'):
            qs = qs.filter(status=request.query_params['status'])
        return Response(AppointmentListSerializer(qs[:50], many=True).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        doctor = self.get_object()
        total = doctor.appointments.count()
        completed = doctor.appointments.filter(status='completed').count()
        no_show = doctor.appointments.filter(status='no_show').count()
        total_patients = Patient.objects.filter(
            appointments__doctor=doctor).distinct().count()
        return Response({
            'total_appointments': total,
            'completed': completed,
            'no_show': no_show,
            'no_show_rate': round(no_show / total * 100, 1) if total else 0,
            'total_patients': total_patients,
        })


# ── Patient ViewSet ────────────────────────────────────────────────────────────

class PatientViewSet(viewsets.ModelViewSet):
    """
    GET    /api/patients/               — list
    POST   /api/patients/               — create (admin/receptionist)
    GET    /api/patients/{id}/          — detail
    PUT    /api/patients/{id}/          — update
    GET    /api/patients/{id}/history/  — full clinical history
    GET    /api/patients/{id}/risk_score/ — ML readmission risk
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'patient_id', 'phone', 'email', 'city']
    ordering_fields = ['name', 'registered_at', 'date_of_birth']

    def get_serializer_class(self):
        if self.action in ['list']:
            return PatientListSerializer
        return PatientDetailSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrReceptionist()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Patient.objects.all()
        role = get_role(self.request.user)
        if role == 'doctor':
            try:
                qs = qs.filter(
                    appointments__doctor=self.request.user.doctor_profile
                ).distinct()
            except Exception:
                return qs.none()
        for param in ['blood_group', 'gender', 'city']:
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{f'{param}__icontains' if param == 'city' else param: val})
        return qs

    def perform_create(self, serializer):
        serializer.save(registered_by=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        patient = self.get_object()
        return Response({
            'patient': PatientDetailSerializer(patient).data,
            'appointments': AppointmentListSerializer(
                patient.appointments.all()[:20], many=True).data,
            'medical_records': MedicalRecordSerializer(
                patient.medical_records.all()[:20], many=True).data,
            'prescriptions': PrescriptionSerializer(
                patient.prescriptions.prefetch_related('items').all()[:20], many=True).data,
            'vitals': VitalSignsSerializer(
                patient.vitals.all()[:10], many=True).data,
            'bills': BillSerializer(
                patient.bills.prefetch_related('payments').all()[:10], many=True).data,
        })

    @action(detail=True, methods=['get'])
    def risk_score(self, request, pk=None):
        patient = self.get_object()
        try:
            from core.ml.risk_model import predict_risk
            score, factors = predict_risk(patient)
        except Exception as e:
            score, factors = None, [str(e)]
        level = 'Unknown'
        if score is not None:
            level = 'High' if score >= 0.7 else 'Medium' if score >= 0.4 else 'Low'
        return Response({
            'patient_id': patient.patient_id,
            'patient_name': patient.name,
            'risk_score': score,
            'risk_level': level,
            'risk_factors': factors,
        })


# ── Appointment ViewSet ────────────────────────────────────────────────────────

class AppointmentViewSet(viewsets.ModelViewSet):
    """
    GET    /api/appointments/           — list (filtered by role)
    POST   /api/appointments/           — create (admin/receptionist)
    GET    /api/appointments/{id}/      — detail
    PUT    /api/appointments/{id}/      — update (admin/receptionist)
    GET    /api/appointments/today/     — today's schedule
    POST   /api/appointments/{id}/update_status/ — quick status change
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['patient__name', 'doctor__name', 'reason']
    ordering_fields = ['appointment_date', 'appointment_time']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AppointmentWriteSerializer
        return AppointmentListSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrReceptionist()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Appointment.objects.select_related('patient', 'doctor').all()
        role = get_role(self.request.user)
        if role == 'doctor':
            try:
                qs = qs.filter(doctor=self.request.user.doctor_profile)
            except Exception:
                return qs.none()
        for param, field in [('date','appointment_date'), ('status','status'),
                              ('doctor','doctor_id'), ('patient','patient_id')]:
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})
        return qs

    def perform_create(self, serializer):
        serializer.save(booked_by=self.request.user)

    @action(detail=False, methods=['get'])
    def today(self, request):
        qs = self.get_queryset().filter(appointment_date=date.today())
        return Response(AppointmentListSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        appt = self.get_object()
        new_status = request.data.get('status')
        valid = dict(Appointment.STATUS_CHOICES)
        if new_status not in valid:
            return Response(
                {'error': f'Invalid status. Choices: {list(valid.keys())}'},
                status=status.HTTP_400_BAD_REQUEST)
        appt.status = new_status
        appt.save()
        return Response({'message': f'Status updated to {appt.get_status_display()}'})


# ── VitalSigns ViewSet ────────────────────────────────────────────────────────

class VitalSignsViewSet(viewsets.ModelViewSet):
    queryset = VitalSigns.objects.select_related('patient', 'appointment').all()
    serializer_class = VitalSignsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)


# ── MedicalRecord ViewSet ─────────────────────────────────────────────────────

class MedicalRecordViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalRecordSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['patient__name', 'diagnosis', 'icd_code']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = MedicalRecord.objects.select_related('patient', 'doctor').all()
        role = get_role(self.request.user)
        if role == 'doctor':
            try:
                qs = qs.filter(doctor=self.request.user.doctor_profile)
            except Exception:
                return qs.none()
        elif role == 'nurse':
            qs = qs.filter(is_confidential=False)
        elif role == 'pharmacist':
            return qs.none()
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs


# ── Prescription ViewSet ──────────────────────────────────────────────────────

class PrescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Prescription.objects.select_related(
            'patient', 'doctor').prefetch_related('items').all()
        role = get_role(self.request.user)
        if role == 'doctor':
            try:
                qs = qs.filter(doctor=self.request.user.doctor_profile)
            except Exception:
                return qs.none()
        for param, field in [('status','status'), ('patient','patient_id')]:
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})
        return qs

    @action(detail=True, methods=['post'])
    def dispense(self, request, pk=None):
        rx = self.get_object()
        if get_role(request.user) not in ('admin', 'pharmacist'):
            return Response({'error': 'Only pharmacist can dispense.'}, status=403)
        rx.status = 'dispensed'
        rx.dispensed_by = request.user
        rx.dispensed_at = timezone.now()
        rx.items.all().update(is_dispensed=True)
        rx.save()
        return Response({'message': 'Prescription dispensed.'})


# ── Bill ViewSet ──────────────────────────────────────────────────────────────

class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [IsAdminOrReceptionist]
    filter_backends = [filters.SearchFilter]
    search_fields = ['bill_number', 'patient__name']

    def get_queryset(self):
        qs = Bill.objects.select_related('patient').prefetch_related('payments').all()
        for param, field in [('status','payment_status'), ('patient','patient_id')]:
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})
        return qs

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def add_payment(self, request, pk=None):
        bill = self.get_object()
        try:
            amount = float(request.data.get('amount', 0))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount.'}, status=400)

        method = request.data.get('payment_method', 'cash')
        txn    = request.data.get('transaction_id', '')

        if amount <= 0:
            return Response({'error': 'Amount must be positive.'}, status=400)
        if amount > float(bill.balance_due) + 0.01:
            return Response(
                {'error': f'Amount ₹{amount} exceeds balance ₹{bill.balance_due:.2f}'},
                status=400)

        Payment.objects.create(
            bill=bill, amount=amount, payment_method=method,
            transaction_id=txn, received_by=request.user,
        )
        bill.amount_paid = float(bill.amount_paid) + amount
        if float(bill.amount_paid) >= float(bill.net_amount):
            bill.payment_status = 'paid'
            bill.paid_at = timezone.now()
        elif float(bill.amount_paid) > 0:
            bill.payment_status = 'partial'
        bill.payment_method = method
        bill.save()
        return Response(BillSerializer(bill).data)


# ── Notification ViewSet ──────────────────────────────────────────────────────

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response({'status': 'marked read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all notifications marked read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(is_read=False).count()})


# ── Analytics Views ────────────────────────────────────────────────────────────

class AnalyticsSummaryView(APIView):
    """GET /api/analytics/summary/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        total_appts = Appointment.objects.count()
        no_show = Appointment.objects.filter(status='no_show').count()
        total_revenue = Bill.objects.aggregate(s=Sum('amount_paid'))['s'] or 0
        pending_rev = sum(
            float(b.balance_due)
            for b in Bill.objects.filter(payment_status__in=['unpaid', 'partial'])
        )
        return Response({
            'total_patients':           Patient.objects.count(),
            'new_patients_today':       Patient.objects.filter(registered_at__date=today).count(),
            'total_doctors':            Doctor.objects.filter(is_available=True).count(),
            'total_appointments':       total_appts,
            'today_appointments':       Appointment.objects.filter(appointment_date=today).count(),
            'completed_appointments':   Appointment.objects.filter(status='completed').count(),
            'no_show_rate':             round(no_show / total_appts * 100, 1) if total_appts else 0,
            'total_revenue':            float(total_revenue),
            'pending_revenue':          round(pending_rev, 2),
            'active_prescriptions':     Prescription.objects.filter(status='active').count(),
            'unpaid_bills':             Bill.objects.filter(payment_status__in=['unpaid','partial']).count(),
        })


class AnalyticsChartsView(APIView):
    """GET /api/analytics/charts/?months=6"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today  = date.today()
        months = int(request.query_params.get('months', 6))

        # Monthly revenue
        monthly_revenue = []
        for i in range(months - 1, -1, -1):
            d = (today.replace(day=1) - timedelta(days=i * 30))
            rev = Bill.objects.filter(
                bill_date__year=d.year, bill_date__month=d.month,
            ).aggregate(s=Sum('amount_paid'))['s'] or 0
            monthly_revenue.append({'month': d.strftime('%b %Y'), 'revenue': float(rev)})

        # Top 10 diagnoses
        top_diagnoses = list(
            MedicalRecord.objects.exclude(diagnosis='')
            .values('diagnosis')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Doctor utilization
        doc_util = list(
            Appointment.objects.values('doctor__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Daily appointments — last 30 days
        daily_appts = []
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            daily_appts.append({
                'date':  d.strftime('%d %b'),
                'count': Appointment.objects.filter(appointment_date=d).count(),
            })

        # Status breakdown
        status_breakdown = list(
            Appointment.objects.values('status')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # No-show rate by doctor
        nsr = []
        for row in (Appointment.objects
                    .values('doctor__name')
                    .annotate(total=Count('id'),
                              no_show=Count('id', filter=Q(status='no_show')))
                    .order_by('-no_show')[:8]):
            row['no_show_rate'] = round(
                row['no_show'] / row['total'] * 100, 1) if row['total'] else 0
            nsr.append(row)

        # Revenue by payment method
        rev_by_method = list(
            Bill.objects.exclude(payment_method='')
            .values('payment_method')
            .annotate(total=Sum('amount_paid'))
            .order_by('-total')
        )

        # New patients per month
        monthly_patients = []
        for i in range(months - 1, -1, -1):
            d = (today.replace(day=1) - timedelta(days=i * 30))
            monthly_patients.append({
                'month': d.strftime('%b %Y'),
                'count': Patient.objects.filter(
                    registered_at__year=d.year,
                    registered_at__month=d.month,
                ).count(),
            })

        return Response({
            'monthly_revenue':    monthly_revenue,
            'top_diagnoses':      top_diagnoses,
            'doctor_utilization': doc_util,
            'daily_appointments': daily_appts,
            'status_breakdown':   status_breakdown,
            'no_show_by_doctor':  nsr,
            'revenue_by_method':  rev_by_method,
            'monthly_patients':   monthly_patients,
        })
