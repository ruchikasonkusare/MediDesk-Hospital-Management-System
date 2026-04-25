#!/usr/bin/env python
"""MediDesk Setup & Seed — run once after pip install -r requirements.txt"""
import os, sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medidesk.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()   # MUST be before any Django/model imports

from django.core.management import call_command
print("📦 Running migrations...")
call_command('migrate', verbosity=0)
print("✅ Migrations done.\n")

from datetime import date, time, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import (Doctor, Patient, Appointment, VitalSigns, MedicalRecord,
                         Prescription, PrescriptionItem, Bill, Payment, UserProfile, Notification)

today = date.today()

# ── Superuser ─────────────────────────────────────────────────────────────────
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@medidesk.local', 'admin123')
    admin.first_name = 'Admin'; admin.last_name = 'User'; admin.save()
    UserProfile.objects.get_or_create(user=admin, defaults={'role':'admin','phone':'9999999999'})
    print("👤 Superuser: admin / admin123")
else:
    admin = User.objects.get(username='admin')
    UserProfile.objects.get_or_create(user=admin, defaults={'role':'admin'})
    print("👤 Superuser already exists.")

# ── Staff ─────────────────────────────────────────────────────────────────────
staff_list = [
    ('reception1','reception123','Meena','Sharma','meena@medidesk.local','receptionist','9800000001'),
    ('nurse1','nurse123','Pooja','Verma','pooja@medidesk.local','nurse','9800000002'),
    ('pharmacist1','pharma123','Rakesh','Gupta','rakesh@medidesk.local','pharmacist','9800000003'),
]
for uname,pwd,fn,ln,email,role,phone in staff_list:
    if not User.objects.filter(username=uname).exists():
        u = User.objects.create_user(username=uname, password=pwd, email=email, first_name=fn, last_name=ln)
        UserProfile.objects.create(user=u,role=role,phone=phone)
        print(f"   ➕ {role}: {uname} / {pwd}")

# ── Doctors ───────────────────────────────────────────────────────────────────
doctors_data = [
    dict(username='dr_priya',pw='doctor123',fn='Priya',ln='Sharma',
         name='Priya Sharma',specialization='cardiology',license_number='DL-CARD-001',
         phone='9876543210',email='priya.sharma@medidesk.local',
         qualification='MBBS, MD (Cardiology), DM – AIIMS Delhi',experience_years=14,
         consultation_fee=800,available_days='Mon,Tue,Wed,Thu,Fri',
         morning_start=time(9,0),morning_end=time(13,0),evening_start=time(17,0),evening_end=time(20,0)),
    dict(username='dr_rahul',pw='doctor123',fn='Rahul',ln='Mehta',
         name='Rahul Mehta',specialization='neurology',license_number='DL-NEURO-002',
         phone='9876543211',email='rahul.mehta@medidesk.local',
         qualification='MBBS, MD (Neurology), DM – KEM Mumbai',experience_years=10,
         consultation_fee=700,available_days='Mon,Wed,Fri',
         morning_start=time(10,0),morning_end=time(14,0),evening_start=None,evening_end=None),
    dict(username='dr_anita',pw='doctor123',fn='Anita',ln='Patel',
         name='Anita Patel',specialization='general',license_number='DL-GEN-003',
         phone='9876543212',email='anita.patel@medidesk.local',
         qualification='MBBS, MD (General Medicine) – MGM Indore',experience_years=8,
         consultation_fee=400,available_days='Mon,Tue,Wed,Thu,Fri,Sat',
         morning_start=time(8,30),morning_end=time(13,30),evening_start=time(16,0),evening_end=time(20,0)),
    dict(username='dr_vikram',pw='doctor123',fn='Vikram',ln='Singh',
         name='Vikram Singh',specialization='orthopedics',license_number='DL-ORTH-004',
         phone='9876543213',email='vikram.singh@medidesk.local',
         qualification='MBBS, MS (Orthopaedics) – SGPGI Lucknow',experience_years=12,
         consultation_fee=600,available_days='Tue,Thu,Sat',
         morning_start=time(9,0),morning_end=time(13,0),evening_start=None,evening_end=None),
    dict(username='dr_deepa',pw='doctor123',fn='Deepa',ln='Nair',
         name='Deepa Nair',specialization='pediatrics',license_number='DL-PED-005',
         phone='9876543214',email='deepa.nair@medidesk.local',
         qualification='MBBS, MD (Pediatrics), DCH – CMC Vellore',experience_years=9,
         consultation_fee=500,available_days='Mon,Tue,Wed,Thu,Fri',
         morning_start=time(9,30),morning_end=time(13,0),evening_start=time(16,30),evening_end=time(19,30)),
]
doctors = []
for d in doctors_data:
    du,_ = User.objects.get_or_create(username=d['username'],defaults={'first_name':d['fn'],'last_name':d['ln'],'email':d['email']})
    if _: du.set_password(d['pw']); du.save(); UserProfile.objects.get_or_create(user=du,defaults={'role':'doctor'})
    doc_fields = {k:v for k,v in d.items() if k not in ('username','pw','fn','ln')}
    obj,created = Doctor.objects.get_or_create(license_number=d['license_number'],defaults=doc_fields)
    if created: obj.user=du; obj.save(); print(f"🩺 Doctor: {obj.name}  ({d['username']} / {d['pw']})")
    doctors.append(obj)

# ── Patients ──────────────────────────────────────────────────────────────────
patients_data = [
    dict(name='Amit Kumar',date_of_birth=date(1985,3,15),gender='M',blood_group='O+',
         phone='9812345001',email='amit@example.com',address='12 MG Road',city='Indore',pincode='452001',
         occupation='Engineer',marital_status='married',emergency_contact_name='Sunita Kumar',
         emergency_contact_phone='9812345002',emergency_contact_relation='Spouse',
         allergies='Penicillin',chronic_conditions='Hypertension',current_medications='Amlodipine 5mg OD',
         insurance_provider='Star Health',insurance_number='SH-2024-001',insurance_validity=date(2025,12,31)),
    dict(name='Sunita Verma',date_of_birth=date(1992,7,22),gender='F',blood_group='A+',
         phone='9812345003',email='sunita@example.com',address='45 Civil Lines',city='Bhopal',pincode='462001',
         occupation='Teacher',marital_status='married',emergency_contact_name='Raj Verma',
         emergency_contact_phone='9812345004',emergency_contact_relation='Husband',
         allergies='',chronic_conditions=''),
    dict(name='Ravi Patel',date_of_birth=date(1975,11,8),gender='M',blood_group='B+',
         phone='9812345005',email='',address='78 Station Road',city='Ujjain',pincode='456001',
         occupation='Businessman',marital_status='married',emergency_contact_name='Meena Patel',
         emergency_contact_phone='9812345006',emergency_contact_relation='Wife',
         allergies='Sulfa drugs',chronic_conditions='Diabetes Type 2, Hypertension',
         current_medications='Metformin 500mg BD, Atenolol 50mg OD'),
    dict(name='Kavita Singh',date_of_birth=date(2001,4,30),gender='F',blood_group='AB+',
         phone='9812345007',email='kavita@example.com',address='23 Vijay Nagar',city='Indore',pincode='452010',
         occupation='Student',marital_status='single',emergency_contact_name='Mohan Singh',
         emergency_contact_phone='9812345008',emergency_contact_relation='Father',
         allergies='',chronic_conditions='Asthma'),
    dict(name='Suresh Gupta',date_of_birth=date(1960,9,12),gender='M',blood_group='O-',
         phone='9812345009',email='',address='9 Palasia',city='Indore',pincode='452001',
         occupation='Retired',marital_status='married',emergency_contact_name='Lata Gupta',
         emergency_contact_phone='9812345010',emergency_contact_relation='Wife',
         allergies='NSAIDs',chronic_conditions='Arthritis, Diabetes Type 2',
         current_medications='Glimepiride 2mg OD, Calcium+D3'),
    dict(name='Priya Joshi',date_of_birth=date(1998,1,5),gender='F',blood_group='B-',
         phone='9812345011',email='priyaj@example.com',address='56 Bhanwarkuan',city='Indore',pincode='452015',
         occupation='Software Developer',marital_status='single',emergency_contact_name='Anil Joshi',
         emergency_contact_phone='9812345012',emergency_contact_relation='Father',
         allergies='',chronic_conditions=''),
    dict(name='Ramesh Tiwari',date_of_birth=date(1955,6,20),gender='M',blood_group='A-',
         phone='9812345013',email='',address='3 Rajendra Nagar',city='Bhopal',pincode='462001',
         occupation='Retired Teacher',marital_status='widowed',emergency_contact_name='Suresh Tiwari',
         emergency_contact_phone='9812345014',emergency_contact_relation='Son',
         allergies='Aspirin',chronic_conditions='Coronary Artery Disease, COPD',
         current_medications='Clopidogrel 75mg OD, Atorvastatin 40mg ON'),
]
patients = []
for p in patients_data:
    obj,created = Patient.objects.get_or_create(phone=p['phone'],defaults=p)
    if created: obj.registered_by=admin; obj.save(); print(f"👤 Patient: {obj.name}  ({obj.patient_id})")
    patients.append(obj)

# ── Appointments ──────────────────────────────────────────────────────────────
reception_user = User.objects.filter(username='reception1').first() or admin
appts_data = [
    (patients[0],doctors[0],today,time(9,0),'confirmed','opd','Routine cardiac checkup – BP and ECG review'),
    (patients[1],doctors[2],today,time(10,30),'scheduled','opd','Fever and body ache for 3 days'),
    (patients[2],doctors[2],today,time(11,0),'completed','follow_up','Diabetes follow-up – HbA1c review'),
    (patients[3],doctors[4],today-timedelta(2),time(14,0),'completed','opd','Asthma – wheezing and breathlessness'),
    (patients[4],doctors[3],today-timedelta(5),time(10,0),'completed','opd','Right knee pain and stiffness'),
    (patients[5],doctors[1],today+timedelta(2),time(15,0),'scheduled','opd','Recurring headaches and dizziness'),
    (patients[0],doctors[2],today-timedelta(10),time(9,30),'completed','opd','Seasonal flu – fever, cough, cold'),
    (patients[2],doctors[0],today+timedelta(7),time(11,30),'scheduled','follow_up','Hypertension monitoring'),
    (patients[6],doctors[0],today-timedelta(3),time(9,0),'completed','opd','Chest discomfort on exertion'),
    (patients[1],doctors[4],today+timedelta(1),time(16,0),'scheduled','opd','Vaccination consultation'),
]
appointments = []
for pat,doc,adate,atime,status,atype,reason in appts_data:
    obj,_ = Appointment.objects.get_or_create(
        doctor=doc,appointment_date=adate,appointment_time=atime,
        defaults=dict(patient=pat,status=status,appointment_type=atype,reason=reason,booked_by=reception_user))
    appointments.append(obj)
print(f"📅 {len(appts_data)} appointments seeded.")

# ── Vital Signs ───────────────────────────────────────────────────────────────
nurse_user = User.objects.filter(username='nurse1').first() or admin
vitals_data = [
    dict(appointment=appointments[2],patient=patients[2],weight_kg=82,height_cm=170,
         temperature_f=98.6,bp_systolic=148,bp_diastolic=92,pulse_bpm=82,spo2_percent=98,blood_sugar_mgdl=214),
    dict(appointment=appointments[3],patient=patients[3],weight_kg=52,height_cm=162,
         temperature_f=99.2,bp_systolic=110,bp_diastolic=70,pulse_bpm=96,spo2_percent=94,respiratory_rate=22),
    dict(appointment=appointments[4],patient=patients[4],weight_kg=88,height_cm=168,
         temperature_f=98.4,bp_systolic=132,bp_diastolic=84,pulse_bpm=76,spo2_percent=99),
    dict(appointment=appointments[8],patient=patients[6],weight_kg=71,height_cm=172,
         temperature_f=98.8,bp_systolic=155,bp_diastolic=95,pulse_bpm=88,spo2_percent=96,respiratory_rate=18),
]
for v in vitals_data:
    if not VitalSigns.objects.filter(appointment=v['appointment']).exists():
        VitalSigns.objects.create(**v,recorded_by=nurse_user)
print(f"🩺 {len(vitals_data)} vital records seeded.")

# ── Medical Records ───────────────────────────────────────────────────────────
records_data = [
    dict(patient=patients[2],doctor=doctors[2],appointment=appointments[2],visit_date=today,
         chief_complaint='High blood sugar, fatigue, increased thirst',
         history_of_present_illness='Known T2DM 5yrs. HbA1c 9.2% last quarter. Poor dietary compliance.',
         examination_findings='BP:148/92, Pulse:82, Wt:82kg, BMI:28.4. No neuropathy.',
         diagnosis='Uncontrolled Type 2 Diabetes Mellitus with Hypertension',icd_code='E11.9',
         treatment_plan='1. Increase Metformin to 1000mg BD\n2. Add Glimepiride 2mg OD\n3. HbA1c in 3 months\n4. Low-carb diet. 30-min daily walk.',
         lab_tests_ordered='HbA1c, FBS, PPBS, KFT, LFT, Lipid Profile',
         follow_up_date=today+timedelta(90),follow_up_notes='Review HbA1c, check for neuropathy.'),
    dict(patient=patients[3],doctor=doctors[4],appointment=appointments[3],visit_date=today-timedelta(2),
         chief_complaint='Wheezing, shortness of breath on exertion',
         history_of_present_illness='Known asthmatic since childhood. Triggered by dust exposure.',
         examination_findings='SpO2:94%, RR:22. Bilateral wheeze. No cyanosis.',
         diagnosis='Mild Persistent Asthma – Acute Exacerbation',icd_code='J45.20',
         treatment_plan='1. Budesonide 200mcg BD\n2. Salbutamol PRN\n3. Montelukast 10mg OD bedtime\n4. Avoid allergens',
         lab_tests_ordered='Chest X-ray, CBC',
         follow_up_date=today+timedelta(28),follow_up_notes='Reassess control, spirometry.'),
    dict(patient=patients[4],doctor=doctors[3],visit_date=today-timedelta(5),
         chief_complaint='Right knee pain and stiffness, difficulty climbing stairs',
         history_of_present_illness='Gradual onset 3 months. Morning stiffness <30 min. No trauma.',
         examination_findings='Mild effusion, crepitus, medial joint line tenderness. ROM 0-120°.',
         diagnosis='Right Knee Osteoarthritis Grade II',icd_code='M17.11',
         treatment_plan='1. Physiotherapy 3x/week\n2. Paracetamol 500mg (NSAIDs avoided – allergy)\n3. Glucosamine supplement\n4. Weight reduction 5kg target',
         lab_tests_ordered='X-ray knee AP&Lateral, Uric Acid, CRP',
         follow_up_date=today+timedelta(42),follow_up_notes='Review physio progress.'),
    dict(patient=patients[6],doctor=doctors[0],appointment=appointments[8],visit_date=today-timedelta(3),
         chief_complaint='Exertional chest discomfort, breathlessness on stairs',
         history_of_present_illness='Known CAD (PTCA 2018). Recurrence of exertional chest tightness 2 weeks.',
         examination_findings='BP:155/95. Pulse:88 irregular. Old LBBB on ECG. SpO2:96%.',
         diagnosis='Stable Angina, Uncontrolled Hypertension on known CAD',icd_code='I20.9',
         treatment_plan='1. Add Isosorbide Mononitrate 20mg BD\n2. Amlodipine 5mg for BP\n3. Repeat ECG, 2D Echo\n4. Cardiology referral',
         lab_tests_ordered='Troponin I serial, Lipid Panel, 2D Echo'),
]
records = []
for r in records_data:
    obj,created = MedicalRecord.objects.get_or_create(
        patient=r['patient'],visit_date=r['visit_date'],doctor=r['doctor'],defaults=r)
    records.append(obj)
print(f"📋 {len(records_data)} medical records seeded.")

# ── Prescriptions ─────────────────────────────────────────────────────────────
def seed_rx(record, patient, doctor, pdate, items, notes=''):
    if Prescription.objects.filter(patient=patient,prescribed_date=pdate).exists(): return
    rx = Prescription.objects.create(medical_record=record,patient=patient,doctor=doctor,
        prescribed_date=pdate,valid_until=pdate+timedelta(90),status='active',notes=notes)
    for it in items: PrescriptionItem.objects.create(prescription=rx,**it)

if records:
    seed_rx(records[0],patients[2],doctors[2],today,[
        dict(medicine_name='Metformin 1000mg',generic_name='Metformin HCl',dosage='1 tab',route='oral',frequency='twice_daily',timing='after_food',duration_days=90,quantity=180),
        dict(medicine_name='Glimepiride 2mg',generic_name='Glimepiride',dosage='1 tab',route='oral',frequency='once_daily',timing='before_food',duration_days=90,quantity=90),
        dict(medicine_name='Telmisartan 40mg',generic_name='Telmisartan',dosage='1 tab',route='oral',frequency='once_daily',timing='morning',duration_days=90,quantity=90),
        dict(medicine_name='Vitamin D3 60000 IU',generic_name='Cholecalciferol',dosage='1 cap',route='oral',frequency='weekly',timing='after_food',duration_days=84,quantity=12),
    ],'Monitor glucose twice daily. Avoid sunlight on Glimepiride.')

if len(records) > 1:
    seed_rx(records[1],patients[3],doctors[4],today-timedelta(2),[
        dict(medicine_name='Salbutamol 100mcg Inhaler',generic_name='Salbutamol Sulfate',dosage='2 puffs',route='inhaled',frequency='as_needed',timing='',duration_days=60,quantity=2),
        dict(medicine_name='Budesonide 200mcg Inhaler',generic_name='Budesonide',dosage='2 puffs',route='inhaled',frequency='twice_daily',timing='',duration_days=28,quantity=1),
        dict(medicine_name='Montelukast 10mg',generic_name='Montelukast Sodium',dosage='1 tab',route='oral',frequency='once_daily',timing='bedtime',duration_days=28,quantity=28),
    ],'Use spacer. Rinse mouth after Budesonide.')

if len(records) > 2:
    seed_rx(records[2],patients[4],doctors[3],today-timedelta(5),[
        dict(medicine_name='Paracetamol 500mg',generic_name='Acetaminophen',dosage='1-2 tab',route='oral',frequency='thrice_daily',timing='after_food',duration_days=14,quantity=42),
        dict(medicine_name='Glucosamine 500mg + Chondroitin',generic_name='Glucosamine Sulfate',dosage='1 cap',route='oral',frequency='twice_daily',timing='after_food',duration_days=90,quantity=180),
    ],'NSAIDs avoided – patient has NSAIDs allergy.')

print("💊 Prescriptions seeded.")

# ── Bills ─────────────────────────────────────────────────────────────────────
bills_data = [
    (patients[2],appointments[2],400,0,0,1200,'upi',1600,'paid'),
    (patients[3],appointments[3],500,200,350,0,'cash',700,'partial'),
    (patients[4],appointments[4],600,500,0,800,'',0,'unpaid'),
    (patients[6],appointments[8],800,1500,0,2500,'card',4800,'paid'),
    (patients[0],appointments[6],400,0,180,0,'upi',580,'paid'),
]
for pat,appt,consult,proc,med,lab,method,paid,status in bills_data:
    if Bill.objects.filter(appointment=appt).exists(): continue
    b = Bill.objects.create(patient=pat,appointment=appt,bill_date=appt.appointment_date,
        consultation_charge=consult,procedure_charge=proc,medicine_charge=med,lab_charge=lab,
        amount_paid=paid,payment_status=status,payment_method=method,generated_by=reception_user,
        paid_at=timezone.now() if status=='paid' else None)
    if paid > 0:
        Payment.objects.create(bill=b,amount=paid,payment_method=method,
            transaction_id=f'TXN{b.pk:06d}',received_by=reception_user)
print("🧾 Bills seeded.")

# ── Notifications ─────────────────────────────────────────────────────────────
if not Notification.objects.filter(user=admin).exists():
    Notification.objects.create(user=admin,title='Welcome to MediDesk!',
        message='Setup complete. All modules active.',notif_type='system')
    Notification.objects.create(user=admin,title='Pending Payments',
        message='2 bills have pending payment.',notif_type='billing',link='/billing/?status=unpaid')

print()
print("=" * 60)
print("✅  MediDesk setup complete!")
print("=" * 60)
print("  Run:   python manage.py runserver")
print("  Open:  http://127.0.0.1:8000")
print()
print("  Username       Password        Role")
print("  admin          admin123        Administrator")
print("  reception1     reception123    Receptionist")
print("  nurse1         nurse123        Nurse")
print("  pharmacist1    pharma123       Pharmacist")
print("  dr_priya       doctor123       Doctor (Cardiology)")
print("  dr_anita       doctor123       Doctor (General)")
print("  dr_vikram      doctor123       Doctor (Ortho)")
print("  dr_rahul       doctor123       Doctor (Neuro)")
print("  dr_deepa       doctor123       Doctor (Pediatrics)")
print("=" * 60)
