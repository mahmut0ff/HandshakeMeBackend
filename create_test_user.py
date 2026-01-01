#!/usr/bin/env python
"""
Simple script to create a test user for the contractor connect app.
Run this from the backend directory: python create_test_user.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contractor_connect.settings')
django.setup()

from apps.accounts.models import User

def create_test_user():
    # Create a test client user
    client_email = 'client@test.com'
    client_password = 'testpass123'
    
    if not User.objects.filter(email=client_email).exists():
        client = User.objects.create_user(
            email=client_email,
            username='testclient',
            password=client_password,
            first_name='Test',
            last_name='Client',
            user_type='client'
        )
        print(f"✅ Created test client: {client_email} / {client_password}")
    else:
        print(f"ℹ️  Test client already exists: {client_email}")
    
    # Create a test contractor user
    contractor_email = 'contractor@test.com'
    contractor_password = 'testpass123'
    
    if not User.objects.filter(email=contractor_email).exists():
        contractor = User.objects.create_user(
            email=contractor_email,
            username='testcontractor',
            password=contractor_password,
            first_name='Test',
            last_name='Contractor',
            user_type='contractor'
        )
        print(f"✅ Created test contractor: {contractor_email} / {contractor_password}")
    else:
        print(f"ℹ️  Test contractor already exists: {contractor_email}")

if __name__ == '__main__':
    create_test_user()
    print("\n🎉 Test users created! You can now login with:")
    print("   Client: client@test.com / testpass123")
    print("   Contractor: contractor@test.com / testpass123")