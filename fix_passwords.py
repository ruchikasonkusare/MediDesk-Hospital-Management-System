#!/usr/bin/env python
"""
MediDesk – Fix Passwords
Run this if staff logins show 'Invalid credentials':
    python fix_passwords.py
"""
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medidesk.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

accounts = [
    ('admin',        'admin123',       'admin'),
    ('reception1',   'reception123',   'receptionist'),
    ('nurse1',       'nurse123',       'nurse'),
    ('pharmacist1',  'pharma123',      'pharmacist'),
    ('dr_priya',     'doctor123',      'doctor'),
    ('dr_rahul',     'doctor123',      'doctor'),
    ('dr_anita',     'doctor123',      'doctor'),
    ('dr_vikram',    'doctor123',      'doctor'),
    ('dr_deepa',     'doctor123',      'doctor'),
]

print("🔐 Resetting passwords...\n")
for username, password, role in accounts:
    try:
        u = User.objects.get(username=username)
        u.set_password(password)
        u.save()
        # Ensure UserProfile exists with correct role
        UserProfile.objects.update_or_create(user=u, defaults={'role': role})
        print(f"  ✅ {username:15s}  →  {password}  ({role})")
    except User.DoesNotExist:
        print(f"  ⚠️  {username} not found — run setup_and_seed.py first")

print("\n✅ Done! Try logging in again at http://127.0.0.1:8000/login/")
