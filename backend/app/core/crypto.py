"""Cryptographic utilities for asymmetric Ed25519 signing and E2EE validation."""

import base64
from functools import lru_cache

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import Settings, get_settings


class CryptoManager:
    """Manager for administrative asymmetric digital signatures using Ed25519."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._private_key, self._public_key = self._load_or_generate_keys()

    def _load_or_generate_keys(
        self,
    ) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Load configured PEM keys or generate an ephemeral Ed25519 keypair."""
        pem_priv = self.settings.admin_override_private_key
        if pem_priv and pem_priv.strip():
            priv_key = serialization.load_pem_private_key(
                pem_priv.encode("utf-8"),
                password=None,
            )
            if not isinstance(priv_key, ed25519.Ed25519PrivateKey):
                raise TypeError("Configured admin private key must be an Ed25519 key")
            return priv_key, priv_key.public_key()

        # Fallback to ephemeral keypair for dev/testing
        priv_key = ed25519.Ed25519PrivateKey.generate()
        return priv_key, priv_key.public_key()

    def get_public_key_pem(self) -> str:
        """Export the public key in standard SubjectPublicKeyInfo PEM format."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def sign_bytes(self, data: bytes) -> str:
        """Sign binary data with Ed25519 private key and return Base64 signature."""
        signature = self._private_key.sign(data)
        return base64.b64encode(signature).decode("utf-8")

    def verify_signature(self, data: bytes, signature_b64: str) -> bool:
        """Verify an Ed25519 signature against data using public key."""
        try:
            signature = base64.b64decode(signature_b64)
            self._public_key.verify(signature, data)
            return True
        except (InvalidSignature, Exception):
            return False


@lru_cache
def get_crypto_manager() -> CryptoManager:
    """Return cached CryptoManager singleton."""
    return CryptoManager()


def is_valid_base64(value: str) -> bool:
    """Check whether a string is valid Base64 encoded."""
    try:
        base64.b64decode(value, validate=True)
        return True
    except Exception:
        return False
