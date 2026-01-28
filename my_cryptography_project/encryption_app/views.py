from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from Crypto.Cipher import DES3

import os
import base64

from .forms import SignUpForm, LoginForm
from .models import User
from .crypto_hybrid import HybridCrypto

def generate_key():
    return DES3.adjust_key_parity(os.urandom(24))

def index(request):
    return render(request, 'index.html')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            users = User.load_users()
            username = form.cleaned_data['username']
            if username in users:
                return render(request, 'signup.html', {'form': form, 'error': 'Username already exists'})
            users[username] = form.cleaned_data['password']
            User.save_user(users)
            return redirect('login')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            users = User.load_users()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            if users.get(username) == password:
                request.session['username'] = username
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'form': form, 'error': 'Invalid credentials'})
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})

def dashboard(request):
    if 'username' not in request.session:
        return redirect('login')
    return render(request, 'dashboard.html')

def encrypt_file(request):
    if request.method == 'POST' and request.FILES['file']:
        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        # Use hybrid cryptography instead of DES3
        hybrid_crypto = HybridCrypto()
        with open(file_path, 'rb') as f:
            plaintext = f.read()
        
        # Encrypt using hybrid algorithm
        encrypted_data = hybrid_crypto.encrypt(plaintext)

        encrypted_file_name = 'confidential_data.' + file.name.split('.')[-1]
        encrypted_file_path = os.path.join(settings.MEDIA_ROOT, encrypted_file_name)
        with open(encrypted_file_path, 'wb') as f:
            f.write(encrypted_data)

        return render(request, 'encrypt.html', {
            'key': base64.b64encode(hybrid_crypto.base_key).decode('utf-8'),
            'file_url': fs.url(encrypted_file_name),
            'algorithm': 'Hybrid (DES3 + AES-GCM)'
        })

    return render(request, 'encrypt.html')

def decrypt_file(request):
    if request.method == 'POST' and request.FILES['file'] and request.POST['key']:
        file = request.FILES['file']
        key = base64.b64decode(request.POST['key'])
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        # Use hybrid cryptography for decryption
        hybrid_crypto = HybridCrypto(base_key=key)
        
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()

        try:
            # Decrypt using hybrid algorithm
            plaintext = hybrid_crypto.decrypt(encrypted_data)

            decrypted_file_name = 'message_file.' + file.name.split('.')[-1]
            decrypted_file_path = os.path.join(settings.MEDIA_ROOT, decrypted_file_name)
            with open(decrypted_file_path, 'wb') as f:
                f.write(plaintext)

            return render(request, 'decrypt.html', {
                'file_url': fs.url(decrypted_file_name),
                'algorithm': 'Hybrid (DES3 + AES-GCM)',
                'success': True
            })
        except Exception as e:
            return render(request, 'decrypt.html', {
                'error': f'Decryption failed: {str(e)}',
                'algorithm': 'Hybrid (DES3 + AES-GCM)'
            })

    return render(request, 'decrypt.html')
    