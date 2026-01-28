from Cryptodome.Cipher import AES, DES3
from Cryptodome.Random import get_random_bytes
from Cryptodome.Hash import SHA256
from Cryptodome.Util.Padding import pad


def derive_hybrid_key(base_key: bytes, des3_key: bytes, salt: bytes) -> bytes:
    """
    Derive a 32-byte AES key by combining:
    - A 32-byte base key (random or user-provided)
    - A DES3-CBC encryption of the salt (8-byte block cipher)

    This design uses DES3 only for key derivation, keeping per-message overhead
    minimal while strengthening the effective key material. Bulk encryption uses
    AES-GCM for speed and integrity.
    """
    # DES3-CBC with zero IV over padded salt to get mixing bytes
    cipher_3des = DES3.new(des3_key, DES3.MODE_CBC, iv=b"\x00" * 8)
    mixed = cipher_3des.encrypt(pad(salt, 8))

    # Hash base_key || mixed to produce a 32-byte AES key
    h = SHA256.new(base_key + mixed)
    return h.digest()


class HybridCrypto:
    """
    Hybrid architecture:
    - DES3 contributes to key derivation (integrity of DES3 preserved in key path)
    - AES-GCM provides high-speed authenticated encryption for bulk data
    This keeps per-message overhead near AES-GCM while adding DES3-based entropy.
    """

    def __init__(self, base_key: bytes, des3_key: bytes):
        self.base_key = base_key
        self.des3_key = des3_key

    @staticmethod
    def generate_keys():
        """Generate a random 32-byte base key and a valid 24-byte DES3 key."""
        base_key = get_random_bytes(32)
        des3_key_raw = DES3.adjust_key_parity(get_random_bytes(24))
        return base_key, des3_key_raw

    def encrypt(self, data: bytes) -> dict:
        """Encrypt data using AES-GCM with a DES3-derived AES key; returns dict."""
        salt = get_random_bytes(16)
        aes_key = derive_hybrid_key(self.base_key, self.des3_key, salt)
        cipher = AES.new(aes_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return {
            "salt": salt,
            "nonce": cipher.nonce,
            "ciphertext": ciphertext,
            "tag": tag,
        }

    def decrypt(self, salt: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
        """Decrypt and verify using AES-GCM with the DES3-derived AES key."""
        aes_key = derive_hybrid_key(self.base_key, self.des3_key, salt)
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag) 