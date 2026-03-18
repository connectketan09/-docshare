import os
import io
import socket
import uuid
import qrcode
from datetime import timedelta
from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import FileVault
from cryptography.fernet import Fernet
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

# ------------------ UTIL FUNCTIONS ------------------

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
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
    return get_fernet().encrypt(file_content)

def decrypt_file(encrypted_content):
    return get_fernet().decrypt(encrypted_content)

# ------------------ VIEWS ------------------

@login_required
def upload_view(request):
    return render(request, 'vault/upload.html')


# ✅ SECURE UPLOAD API (NO CSRF EXEMPT)
@require_POST
@login_required
def api_upload(request):
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    file = request.FILES['file']

    # ✅ File validation
    if file.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'File too large (Max 5MB)'}, status=400)

    if not file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Only PDF files are allowed'}, status=400)

    try:
        vault_id = str(uuid.uuid4())[:12]

        file_content = file.read()
        encrypted_content = encrypt_file(file_content)

        enc_dir = os.path.join(settings.MEDIA_ROOT, 'encrypted_vault')
        os.makedirs(enc_dir, exist_ok=True)

        enc_filename = f"{vault_id}_{file.name}.enc"
        enc_path = os.path.join(enc_dir, enc_filename)

        with open(enc_path, 'wb') as f:
            f.write(encrypted_content)

        expiry_time = timezone.now() + timedelta(hours=24)

        vault = FileVault.objects.create(
            vault_id=vault_id,
            original_filename=file.name,
            encrypted_file=os.path.join('encrypted_vault', enc_filename),
            expiry_time=expiry_time
        )

        return JsonResponse({
            'success': True,
            'vault_id': vault_id
        })

    except Exception:
        return JsonResponse({'error': 'Upload failed'}, status=500)


def processing_view(request, vault_id):
    vault = get_object_or_404(FileVault, vault_id=vault_id)
    return render(request, 'vault/processing.html', {'vault': vault})


def qr_result_view(request, vault_id):
    vault = get_object_or_404(FileVault, vault_id=vault_id)

    if vault.is_expired:
        return render(request, 'vault/expired.html')

    access_url = request.build_absolute_uri(
        reverse('vault:access_file', args=[vault.vault_id])
    )

    render_url = os.environ.get('RENDER_EXTERNAL_URL')

    if render_url:
        if not access_url.startswith(render_url):
            path = reverse('vault:access_file', args=[vault.vault_id])
            access_url = f"{render_url.rstrip('/')}{path}"

    elif 'localhost' in access_url or '127.0.0.1' in access_url:
        local_ip = get_local_ip()
        access_url = access_url.replace('localhost', local_ip).replace('127.0.0.1', local_ip)

    import base64
    qr = qrcode.make(access_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'vault/qr_result.html', {
        'vault': vault,
        'qr_b64': qr_b64,
        'access_url': access_url
    })


# ✅ SECURE FILE ACCESS
@login_required
def access_file_view(request, vault_id):
    vault = get_object_or_404(FileVault, vault_id=vault_id)

    if vault.is_expired:
        vault.encrypted_file.delete()
        vault.delete()
        return render(request, 'vault/expired.html')

    try:
        file_path = os.path.join(settings.MEDIA_ROOT, vault.encrypted_file.name)

        with open(file_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = decrypt_file(encrypted_data)

        response = HttpResponse(decrypted_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{vault.original_filename}"'
        response['X-Content-Type-Options'] = 'nosniff'

        return response

    except Exception:
        return HttpResponse("Error accessing file", status=500)
