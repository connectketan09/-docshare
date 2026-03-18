from django.db import models
import uuid
import os
from django.utils import timezone
from django.core.exceptions import ValidationError

# ✅ Allowed file types
ALLOWED_EXTENSIONS = ['pdf', 'doc', 'docx', 'jpg', 'png']

# ✅ File validation function
def validate_file(file):
    ext = file.name.split('.')[-1].lower()

    # Block dangerous files
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError("Only PDF, DOC, DOCX, JPG, PNG files are allowed.")

    # Limit file size (5MB)
    if file.size > 5 * 1024 * 1024:
        raise ValidationError("File size must be under 5MB.")

def upload_to_encrypted(instance, filename):
    return f'encrypted_vault/{uuid.uuid4()}_{filename}'

class FileVault(models.Model):
    vault_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    original_filename = models.CharField(max_length=255)

    # ✅ Add validator here
    encrypted_file = models.FileField(
        upload_to=upload_to_encrypted,
        validators=[validate_file]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expiry_time = models.DateTimeField()

    def __str__(self):
        return str(self.vault_id)

    @property
    def is_expired(self):
        return timezone.now() > self.expiry_time
