import os
from django.core.management.base import BaseCommand
from django.conf import settings
from vault.models import FileVault
from django.utils import timezone

class Command(BaseCommand):
    help = 'Cleans up expired vault files from the database and filesystem'

    def handle(self, *args, **kwargs):
        expired_vaults = FileVault.objects.filter(expiry_time__lt=timezone.now())
        count = expired_vaults.count()
        
        for vault in expired_vaults:
            # Delete file
            file_path = os.path.join(settings.MEDIA_ROOT, vault.encrypted_file.name)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete DB record
            vault.delete()
            
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} expired vault(s)'))
