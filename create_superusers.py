#!/usr/bin/env python
"""
Script to create superuser and superadmin for Django admin and application
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartcity_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

User = get_user_model()

def create_superuser():
    """Create Django superuser (admin/123) for Django admin panel"""
    username = 'admin'
    password = '123'
    email = 'admin@smartcity.uz'
    
    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"✅ Django superuser '{username}' yangilandi (parol: {password})")
    else:
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        print(f"✅ Django superuser '{username}' yaratildi (parol: {password})")
    
    # Create or get token for superuser
    token, created = Token.objects.get_or_create(user=user)
    if created:
        print(f"✅ Token yaratildi: {token.key}")
    else:
        print(f"✅ Token mavjud: {token.key}")
    
    return user

def create_fergan_user():
    """Create Farg'ona shahar user (fergan/123) for application login"""
    username = 'fergan'
    password = '123'
    email = 'fergan@smartcity.uz'
    
    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        user.set_password(password)
        user.is_staff = True
        user.save()
        print(f"✅ Farg'ona foydalanuvchi '{username}' yangilandi (parol: {password})")
    else:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True
        )
        print(f"✅ Farg'ona foydalanuvchi '{username}' yaratildi (parol: {password})")
    
    # Create or get token for fergan user
    token, created = Token.objects.get_or_create(user=user)
    if created:
        print(f"✅ Token yaratildi: {token.key}")
    else:
        print(f"✅ Token mavjud: {token.key}")
    
    return user

if __name__ == '__main__':
    print("=" * 50)
    print("Superuser va Superadmin yaratish")
    print("=" * 50)
    
    # Create Django superuser
    print("\n1. Django superuser yaratilmoqda...")
    create_superuser()
    
    # Create Farg'ona shahar user
    print("\n2. Farg'ona shahar foydalanuvchisi yaratilmoqda...")
    create_fergan_user()
    
    print("\n" + "=" * 50)
    print("✅ Barcha foydalanuvchilar tayyor!")
    print("=" * 50)
    print("\nKirish ma'lumotlari:")
    print("  Django Admin: admin / 123")
    print("  Application: fergan / 123")
    print("\n")

