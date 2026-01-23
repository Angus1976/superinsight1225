"""
AES-256 加密工具模块

提供企业级加密/解密功能，用于敏感数据存储。
使用 AES-256-GCM 模式提供认证加密。

Validates: 需求 14.1
"""

import os
import base64
import hashlib
import secrets
import logging
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from src.i18n.translations import get_translation

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """加密操作错误"""
    pass


class DecryptionError(Exception):
    """解密操作错误"""
    pass


class AES256Encryption:
    """
    AES-256-GCM 加密服务
    
    提供安全的加密/解密功能，支持：
    - AES-256-GCM 认证加密
    - PBKDF2 密钥派生
    - 安全随机数生成
    """
    
    # 常量配置
    KEY_SIZE = 32  # 256 bits
    NONCE_SIZE = 12  # 96 bits (GCM 推荐)
    SALT_SIZE = 16  # 128 bits
    PBKDF2_ITERATIONS = 100000  # OWASP 推荐
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化加密服务
        
        Args:
            master_key: 主密钥（可选）。如果不提供，将从环境变量读取
        """
        self._master_key = master_key or os.environ.get("ENCRYPTION_MASTER_KEY")
        if self._master_key:
            self._derived_key = self._derive_key_from_password(
                self._master_key,
                b"superinsight_default_salt"  # 默认盐值
            )
        else:
            self._derived_key = None
    
    def encrypt(self, plaintext: str, key: Optional[str] = None) -> str:
        """
        加密文本
        
        Args:
            plaintext: 要加密的明文
            key: 加密密钥（可选）。如果不提供，使用主密钥
            
        Returns:
            Base64 编码的密文（格式: nonce + ciphertext + tag）
            
        Raises:
            EncryptionError: 加密失败时抛出
        """
        if not plaintext:
            raise EncryptionError(
                get_translation("security.encryption.empty_plaintext", "zh")
            )
        
        try:
            # 获取密钥
            encryption_key = self._get_key(key)
            
            # 生成随机 nonce
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            
            # 创建 AESGCM 实例
            aesgcm = AESGCM(encryption_key)
            
            # 加密
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
            
            # 组合 nonce + ciphertext 并 Base64 编码
            encrypted_data = nonce + ciphertext
            result = base64.b64encode(encrypted_data).decode('utf-8')
            
            logger.debug("security.encryption.encrypt_success")
            return result
            
        except Exception as e:
            logger.error(f"security.encryption.encrypt_failed: {e}")
            raise EncryptionError(
                get_translation("security.encryption.encrypt_failed", "zh")
            ) from e
    
    def decrypt(self, ciphertext: str, key: Optional[str] = None) -> str:
        """
        解密文本
        
        Args:
            ciphertext: Base64 编码的密文
            key: 解密密钥（可选）。如果不提供，使用主密钥
            
        Returns:
            解密后的明文
            
        Raises:
            DecryptionError: 解密失败时抛出
        """
        if not ciphertext:
            raise DecryptionError(
                get_translation("security.encryption.empty_ciphertext", "zh")
            )
        
        try:
            # 获取密钥
            decryption_key = self._get_key(key)
            
            # Base64 解码
            encrypted_data = base64.b64decode(ciphertext)
            
            # 分离 nonce 和密文
            if len(encrypted_data) < self.NONCE_SIZE:
                raise DecryptionError(
                    get_translation("security.encryption.invalid_ciphertext", "zh")
                )
            
            nonce = encrypted_data[:self.NONCE_SIZE]
            actual_ciphertext = encrypted_data[self.NONCE_SIZE:]
            
            # 创建 AESGCM 实例
            aesgcm = AESGCM(decryption_key)
            
            # 解密
            plaintext_bytes = aesgcm.decrypt(nonce, actual_ciphertext, None)
            result = plaintext_bytes.decode('utf-8')
            
            logger.debug("security.encryption.decrypt_success")
            return result
            
        except DecryptionError:
            raise
        except Exception as e:
            logger.error(f"security.encryption.decrypt_failed: {e}")
            raise DecryptionError(
                get_translation("security.encryption.decrypt_failed", "zh")
            ) from e
    
    @staticmethod
    def generate_key() -> str:
        """
        生成安全的随机密钥
        
        Returns:
            Base64 编码的 256 位密钥
        """
        key_bytes = secrets.token_bytes(AES256Encryption.KEY_SIZE)
        return base64.b64encode(key_bytes).decode('utf-8')
    
    @staticmethod
    def generate_salt() -> bytes:
        """
        生成随机盐值
        
        Returns:
            随机盐值字节
        """
        return secrets.token_bytes(AES256Encryption.SALT_SIZE)
    
    def derive_key(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        从密码派生密钥（使用 PBKDF2）
        
        Args:
            password: 用户密码
            salt: 盐值（可选）。如果不提供，将生成新的盐值
            
        Returns:
            (派生密钥, 盐值) 元组
        """
        if salt is None:
            salt = self.generate_salt()
        
        derived_key = self._derive_key_from_password(password, salt)
        return derived_key, salt
    
    def _derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """
        内部方法：从密码派生密钥
        
        Args:
            password: 密码
            salt: 盐值
            
        Returns:
            派生的密钥字节
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))
    
    def _get_key(self, key: Optional[str] = None) -> bytes:
        """
        获取加密密钥
        
        Args:
            key: 可选的密钥字符串
            
        Returns:
            密钥字节
            
        Raises:
            EncryptionError: 没有可用密钥时抛出
        """
        if key:
            # 如果提供了密钥，尝试 Base64 解码
            try:
                key_bytes = base64.b64decode(key)
                if len(key_bytes) != self.KEY_SIZE:
                    # 如果长度不对，使用 SHA256 哈希
                    key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
                return key_bytes
            except Exception:
                # 如果解码失败，使用 SHA256 哈希
                return hashlib.sha256(key.encode('utf-8')).digest()
        
        if self._derived_key:
            return self._derived_key
        
        raise EncryptionError(
            get_translation("security.encryption.no_key", "zh")
        )
    
    def encrypt_with_salt(self, plaintext: str, password: str) -> str:
        """
        使用密码加密（包含盐值）
        
        Args:
            plaintext: 要加密的明文
            password: 用户密码
            
        Returns:
            Base64 编码的密文（格式: salt + nonce + ciphertext + tag）
        """
        if not plaintext:
            raise EncryptionError(
                get_translation("security.encryption.empty_plaintext", "zh")
            )
        
        try:
            # 生成盐值和派生密钥
            salt = self.generate_salt()
            derived_key = self._derive_key_from_password(password, salt)
            
            # 生成随机 nonce
            nonce = secrets.token_bytes(self.NONCE_SIZE)
            
            # 创建 AESGCM 实例
            aesgcm = AESGCM(derived_key)
            
            # 加密
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
            
            # 组合 salt + nonce + ciphertext 并 Base64 编码
            encrypted_data = salt + nonce + ciphertext
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"security.encryption.encrypt_with_salt_failed: {e}")
            raise EncryptionError(
                get_translation("security.encryption.encrypt_failed", "zh")
            ) from e
    
    def decrypt_with_salt(self, ciphertext: str, password: str) -> str:
        """
        使用密码解密（从密文中提取盐值）
        
        Args:
            ciphertext: Base64 编码的密文
            password: 用户密码
            
        Returns:
            解密后的明文
        """
        if not ciphertext:
            raise DecryptionError(
                get_translation("security.encryption.empty_ciphertext", "zh")
            )
        
        try:
            # Base64 解码
            encrypted_data = base64.b64decode(ciphertext)
            
            # 分离 salt、nonce 和密文
            min_length = self.SALT_SIZE + self.NONCE_SIZE
            if len(encrypted_data) < min_length:
                raise DecryptionError(
                    get_translation("security.encryption.invalid_ciphertext", "zh")
                )
            
            salt = encrypted_data[:self.SALT_SIZE]
            nonce = encrypted_data[self.SALT_SIZE:self.SALT_SIZE + self.NONCE_SIZE]
            actual_ciphertext = encrypted_data[self.SALT_SIZE + self.NONCE_SIZE:]
            
            # 派生密钥
            derived_key = self._derive_key_from_password(password, salt)
            
            # 创建 AESGCM 实例
            aesgcm = AESGCM(derived_key)
            
            # 解密
            plaintext_bytes = aesgcm.decrypt(nonce, actual_ciphertext, None)
            return plaintext_bytes.decode('utf-8')
            
        except DecryptionError:
            raise
        except Exception as e:
            logger.error(f"security.encryption.decrypt_with_salt_failed: {e}")
            raise DecryptionError(
                get_translation("security.encryption.decrypt_failed", "zh")
            ) from e


# 便捷函数
_default_encryption = None


def get_encryption_service() -> AES256Encryption:
    """获取默认加密服务实例"""
    global _default_encryption
    if _default_encryption is None:
        _default_encryption = AES256Encryption()
    return _default_encryption


def encrypt(plaintext: str, key: Optional[str] = None) -> str:
    """
    加密文本（便捷函数）
    
    Args:
        plaintext: 要加密的明文
        key: 加密密钥（可选）
        
    Returns:
        Base64 编码的密文
    """
    return get_encryption_service().encrypt(plaintext, key)


def decrypt(ciphertext: str, key: Optional[str] = None) -> str:
    """
    解密文本（便捷函数）
    
    Args:
        ciphertext: Base64 编码的密文
        key: 解密密钥（可选）
        
    Returns:
        解密后的明文
    """
    return get_encryption_service().decrypt(ciphertext, key)


def generate_key() -> str:
    """生成安全密钥（便捷函数）"""
    return AES256Encryption.generate_key()
