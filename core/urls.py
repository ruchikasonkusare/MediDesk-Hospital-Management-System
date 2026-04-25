from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/new/', views.patient_create, name='patient_create'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('patients/<int:pk>/edit/', views.patient_edit, name='patient_edit'),

    # Doctors
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/new/', views.doctor_create, name='doctor_create'),
    path('doctors/<int:pk>/', views.doctor_detail, name='doctor_detail'),
    path('doctors/<int:pk>/edit/', views.doctor_edit, name='doctor_edit'),

    # Appointments
    path('appointments/', views.appointment_list, name='appointment_list'),
    path('appointments/new/', views.appointment_create, name='appointment_create'),
    path('appointments/<int:pk>/edit/', views.appointment_edit, name='appointment_edit'),
    path('appointments/<int:pk>/status/', views.appointment_status_update, name='appointment_status_update'),
    path('appointments/<int:appointment_pk>/vitals/', views.vitals_create, name='vitals_create'),

    # Records
    path('records/', views.record_list, name='record_list'),
    path('records/new/', views.record_create, name='record_create'),
    path('records/<int:pk>/', views.record_detail, name='record_detail'),
    path('records/<int:pk>/edit/', views.record_edit, name='record_edit'),

    # Prescriptions
    path('prescriptions/', views.prescription_list, name='prescription_list'),
    path('prescriptions/new/', views.prescription_create, name='prescription_create'),
    path('prescriptions/<int:pk>/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:pk>/dispense/', views.prescription_dispense, name='prescription_dispense'),

    # Billing
    path('billing/', views.bill_list, name='bill_list'),
    path('billing/new/', views.bill_create, name='bill_create'),
    path('billing/<int:pk>/', views.bill_detail, name='bill_detail'),
    path('billing/<int:pk>/pay/', views.bill_add_payment, name='bill_add_payment'),

    # Staff
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/new/', views.staff_create, name='staff_create'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),

    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),

    # API
    path('api/patients/search/', views.api_patient_search, name='api_patient_search'),
    path('api/doctor-slots/', views.api_doctor_slots, name='api_doctor_slots'),
    path('api/unread-count/', views.api_unread_count, name='api_unread_count'),
]

# Analytics page
from django.contrib.auth.decorators import login_required
from django.shortcuts import render as _render

def analytics_view(request):
    from django.contrib.auth.decorators import login_required
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('/login/')
    return _render(request, 'core/analytics.html')

urlpatterns += [
    # Analytics dashboard
    path('analytics/', analytics_view, name='analytics'),

    # Excel exports
    path('export/patients/excel/', __import__('core.exports', fromlist=['export_patients_excel']).export_patients_excel, name='export_patients_excel'),
    path('export/billing/excel/', __import__('core.exports', fromlist=['export_billing_excel']).export_billing_excel, name='export_billing_excel'),

    # PDF exports
    path('export/prescription/<int:pk>/pdf/', __import__('core.exports', fromlist=['export_prescription_pdf']).export_prescription_pdf, name='export_prescription_pdf'),
    path('export/bill/<int:pk>/pdf/', __import__('core.exports', fromlist=['export_bill_pdf']).export_bill_pdf, name='export_bill_pdf'),
]
