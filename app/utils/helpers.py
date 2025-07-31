
import base64
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

UPLOAD_FOLDER = 'static/images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_base64_image(base64_str, slug):
    try:
        header, encoded = base64_str.split(",", 1)
        file_ext = header.split('/')[1].split(';')[0]
        filename = f"{slug}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(encoded))
        return filename
    except Exception as e:
        print(f"Gagal menyimpan gambar {slug}: {e}")
        return None

def safe_decimal(value):
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        print("❌ Invalid Decimal:", value)
        return Decimal("0.0")

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y%m%d').date()
    except:
        return None
