import os
import io
import socket
import uuid
import qrcode
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.utils import timezone
from .models import FileVault
from cryptography.fernet import Fernet
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_fernet():
    return Fernet(settings.FERNET_KEY)

def encrypt_file(file_content):
    f = get_fernet()
    return f.encrypt(file_content)

def decrypt_file(encrypted_content):
    f = get_fernet()
    return f.decrypt(encrypted_content)

def upload_view(request):
    return render(request, 'vault/upload.html')

@csrf_exempt
def api_upload(request):
    if request.method == 'POST':
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
            
        file = request.FILES['file']
        
        # Max size validation (50MB = 50 * 1024 * 1024 bytes)
        if file.size > 52428800:
            return JsonResponse({'error': 'File too large (Max 50MB)'}, status=400)
            
        if not file.name.lower().endswith('.pdf'):
            return JsonResponse({'error': 'Only PDF supported'}, status=400)
        
        try:
            # Generate unique ID
            vault_id = str(uuid.uuid4())[:12] # Shortened for a simpler QR
            
            # Read and encrypt
            file_content = file.read()
            encrypted_content = encrypt_file(file_content)
            
            # Define save path
            if not os.path.exists(settings.MEDIA_ROOT):
                os.makedirs(settings.MEDIA_ROOT)
                
            enc_dir = os.path.join(settings.MEDIA_ROOT, 'encrypted_vault')
            if not os.path.exists(enc_dir):
                os.makedirs(enc_dir)
                
            enc_filename = f"{vault_id}_{file.name}.enc"
            enc_path = os.path.join(enc_dir, enc_filename)
            
            with open(enc_path, 'wb') as f:
                f.write(encrypted_content)
            
            # Save to Database
            expiry_time = timezone.now() + timedelta(hours=24)
            
            vault = FileVault(
                vault_id=vault_id,
                original_filename=file.name,
                encrypted_file=os.path.join('encrypted_vault', enc_filename),
                expiry_time=expiry_time
            )
            vault.save()
            
            return JsonResponse({'success': True, 'vault_id': vault_id})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def processing_view(request, vault_id):
    vault = get_object_or_404(FileVault, vault_id=vault_id)
    return render(request, 'vault/processing.html', {'vault': vault})

def qr_result_view(request, vault_id):
    vault = get_object_or_404(FileVault, vault_id=vault_id)
    
    # Check expiry
    if vault.is_expired:
        return render(request, 'vault/expired.html')
        
    access_url = request.build_absolute_uri(reverse('vault:access_file', args=[vault.vault_id]))
    
    # If using localhost, swap it for the real local IP so mobile phones can scan correctly
    if 'localhost' in access_url or '127.0.0.1' in access_url:
        local_ip = get_local_ip()
        access_url = access_url.replace('localhost', local_ip).replace('127.0.0.1', local_ip)
    
    # Generate QR Code image as base64 or serve directly. Let's send the url and generate on template or backend.
    # In backend, we can generate a base64 encoded image string.
    import base64
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(access_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    context = {
        'vault': vault,
        'qr_b64': qr_b64,
        'access_url': access_url
    }
    return render(request, 'vault/qr_result.html', context)

def access_file_view(request, vault_id):
    vault = get_object_or_404(FileVault, vault_id=vault_id)
    
    if vault.is_expired:
        return render(request, 'vault/expired.html')
        
    # Read encrypted file and decrypt
    try:
        file_path = os.path.join(settings.MEDIA_ROOT, vault.encrypted_file.name)
        with open(file_path, 'rb') as f:
            encrypted_data = f.read()
            
        decrypted_data = decrypt_file(encrypted_data)
        
        # Return as downloadable 
        response = HttpResponse(decrypted_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{vault.original_filename}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error accessing file: {str(e)}", status=500)
