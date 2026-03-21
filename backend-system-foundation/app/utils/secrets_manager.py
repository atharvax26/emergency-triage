"""Secrets management utilities for secure handling of sensitive data."""

import os
import base64
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


class SecretsManager:
    """
    Secrets management for secure storage and retrieval of sensitive data.
    
    Features:
    - Encryption of secrets at rest
    - Environment variable integration
    - No hardcoded secrets in code
    - Key derivation from master key
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize secrets manager.
        
        Args:
            master_key: Master encryption key (should come from environment)
        """
        self.master_key = master_key or os.getenv("SECRETS_ENCRYPTION_KEY", "")
        self._cipher = None
        
        if self.master_key:
            self._initialize_cipher()
    
    def _initialize_cipher(self):
        """Initialize Fernet cipher with derived key."""
        # Derive a key from the master key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"backend-system-foundation-salt",  # In production, use a random salt
            iterations=100000,
        )
        
        # Derive key and encode for Fernet
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        self._cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a secret value.
        
        Args:
            plaintext: Secret value to encrypt
            
        Returns:
            Encrypted value as base64 string
            
        Raises:
            ValueError: If encryption is not configured
        """
        if not self._cipher:
            raise ValueError("Secrets encryption not configured. Set SECRETS_ENCRYPTION_KEY.")
        
        encrypted = self._cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a secret value.
        
        Args:
            ciphertext: Encrypted value as base64 string
            
        Returns:
            Decrypted plaintext value
            
        Raises:
            ValueError: If encryption is not configured
        """
        if not self._cipher:
            raise ValueError("Secrets encryption not configured. Set SECRETS_ENCRYPTION_KEY.")
        
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self._cipher.decrypt(encrypted)
        return decrypted.decode()
    
    def get_secret(self, key: str, default: Optional[str] = None, encrypted: bool = False) -> Optional[str]:
        """
        Get a secret from environment variables.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            encrypted: Whether the value is encrypted
            
        Returns:
            Secret value (decrypted if encrypted)
        """
        value = os.getenv(key, default)
        
        if value and encrypted and self._cipher:
            try:
                return self.decrypt(value)
            except Exception:
                # If decryption fails, return as-is (might not be encrypted)
                return value
        
        return value
    
    def set_secret(self, key: str, value: str, encrypt: bool = False) -> str:
        """
        Set a secret (for development/testing only).
        
        Args:
            key: Environment variable name
            value: Secret value
            encrypt: Whether to encrypt the value
            
        Returns:
            The value that was set (encrypted if encrypt=True)
        """
        if encrypt and self._cipher:
            encrypted_value = self.encrypt(value)
            os.environ[key] = encrypted_value
            return encrypted_value
        else:
            os.environ[key] = value
            return value
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new encryption key.
        
        Returns:
            Base64-encoded encryption key
        """
        return Fernet.generate_key().decode()
    
    @staticmethod
    def validate_no_hardcoded_secrets(file_path: str) -> Dict[str, Any]:
        """
        Validate that a file doesn't contain hardcoded secrets.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            Dictionary with validation results
        """
        from app.utils.security import SecretsProtection
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file: {e}"
            }
        
        # Detect hardcoded secrets
        detected = SecretsProtection.detect_hardcoded_secrets(content)
        
        # Check for common secret patterns
        issues = []
        
        # Check for hardcoded passwords
        if "password" in content.lower() and "=" in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if "password" in line.lower() and "=" in line and not line.strip().startswith('#'):
                    # Check if it's not a variable assignment from env
                    if "os.getenv" not in line and "os.environ" not in line and "settings." not in line:
                        issues.append(f"Line {i}: Potential hardcoded password")
        
        # Check for hardcoded API keys
        if "api_key" in content.lower() and "=" in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if "api_key" in line.lower() and "=" in line and not line.strip().startswith('#'):
                    if "os.getenv" not in line and "os.environ" not in line and "settings." not in line:
                        issues.append(f"Line {i}: Potential hardcoded API key")
        
        # Check for hardcoded database credentials
        if "postgresql://" in content or "mysql://" in content:
            if "postgres:postgres" in content or "root:root" in content:
                issues.append("Hardcoded database credentials detected")
        
        return {
            "success": len(issues) == 0 and len(detected) == 0,
            "detected_types": detected,
            "issues": issues,
            "message": "No hardcoded secrets found" if len(issues) == 0 else "Hardcoded secrets detected"
        }


# Global secrets manager instance
secrets_manager = SecretsManager()


def get_database_url() -> str:
    """
    Get database URL from environment with proper secrets handling.
    
    Returns:
        Database connection URL
    """
    return secrets_manager.get_secret("DATABASE_URL", encrypted=False)


def get_redis_url() -> str:
    """
    Get Redis URL from environment with proper secrets handling.
    
    Returns:
        Redis connection URL
    """
    return secrets_manager.get_secret("REDIS_URL", encrypted=False)


def get_jwt_secret() -> str:
    """
    Get JWT secret key from environment with proper secrets handling.
    
    Returns:
        JWT secret key
    """
    secret = secrets_manager.get_secret("JWT_SECRET_KEY", encrypted=False)
    
    # Validate that it's not the default insecure value
    if secret == "your-secret-key-change-in-production":
        import warnings
        warnings.warn(
            "Using default JWT secret key. This is insecure! "
            "Set JWT_SECRET_KEY environment variable in production.",
            RuntimeWarning
        )
    
    return secret


if __name__ == "__main__":
    # Generate a new encryption key
    print("Generated encryption key:")
    print(SecretsManager.generate_key())
    print("\nAdd this to your .env file as SECRETS_ENCRYPTION_KEY")
