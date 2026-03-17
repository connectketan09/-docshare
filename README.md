# DocShare

DocShare is a secure digital vault application that allows users to upload high-value documents, encrypt them using AES-256 encryption, and share access temporarily via a secure QR code.

## Core Features

- **Secure File Upload**: Support for PDF files up to 50MB.
- **End-to-End Encryption**: Documents are encrypted with AES-256 before being stored on the server. Only the encrypted blobs are saved.
- **Unique Vault System**: Each upload generates a temporary vault with a unique identifier.
- **Temporary Access**: Vault URLs expire exactly 24 hours after creation.
- **QR Code Generation**: Instantly generates a QR code to share the vault link.
- **Auto Cleanup Mechanism**: Built-in Django command to garbage-collect expired encrypted files.

## Technology Stack

- **Frontend**: HTML5, Vanilla CSS3 (Custom Properties, Flexbox, Grid), Vanilla JavaScript.
- **Backend**: Python 3, Django 4.x.
- **Database**: SQLite (built-in).
- **Security**: Cryptography (`cryptography` / Fernet) for AES-256 encryption.
- **Utilities**: `qrcode` [PIL] for generating Shareable QR codes.

## Requirements

Ensure Python 3 is installed. The repository includes an initialized Python virtual environment containing the necessary packages.

## Getting Started

1. **Activate the Virtual Environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Run Migrations** (if not already applied):
   ```bash
   python manage.py makemigrations vault
   python manage.py migrate
   ```

3. **Start the Development Server**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   Access the app at `http://localhost:8000`

## Auto-Delete Background Job

The application includes a custom Django management command that removes expired files from both the filesystem and database. For continuous garbage collection in a production environment, set up a cron job:

```bash
# Example Cron to run every hour
0 * * * * cd /path/to/project && source venv/bin/activate && python manage.py cleanup_vault
```

To run it manually:
```bash
python manage.py cleanup_vault
```

## Security Notices

- In `docshare/settings.py`, `FERNET_KEY` acts as the master key. This must be rotated, secured, and ideally read from Environment Variables in a true production setting.
- The `DEBUG = True` flag must also be disabled prior to real-world deployment.
