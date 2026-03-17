from django.db import models
import uuid
import os
from django.utils import timezone

def upload_to_encrypted(instance, filename):
    return f'encrypted_vault/{uuid.uuid4()}_{filename}'

class FileVault(models.Model):
    vault_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    original_filename = models.CharField(max_length=255)
    encrypted_file = models.FileField(upload_to=upload_to_encrypted)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_time = models.DateTimeField()
    
    def __str__(self):
        return str(self.vault_id)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expiry_time
