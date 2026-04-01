import sys

sys.path.insert(0, "C:/Users/USER/Desktop/Ruleta")

from app.services.auth_service import hashear_password, verificar_password

# Test hashing
hashed = hashear_password("admin123")
print(f"Hash: {hashed}")

# Test verification
result = verificar_password("admin123", hashed)
print(f"Verification: {result}")
