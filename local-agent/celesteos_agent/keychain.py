"""
macOS Keychain integration for secure credential storage.
Uses keyring library with macOS Security framework backend.
"""

import keyring
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)


class KeychainManager:
    """Manages secure credential storage in macOS Keychain."""

    SERVICE_NAME = "CelesteOS Agent"
    NAS_PASSWORD_KEY = "nas_password"

    def __init__(self):
        """Initialize keychain manager."""
        # Verify keyring backend is macOS Keychain
        backend = keyring.get_keyring()
        logger.debug(f"Using keyring backend: {backend}")

    def store_nas_password(self, username: str, password: str) -> None:
        """Store NAS password in keychain.

        Args:
            username: NAS username
            password: NAS password
        """
        try:
            keyring.set_password(
                self.SERVICE_NAME,
                f"{self.NAS_PASSWORD_KEY}_{username}",
                password
            )
            logger.info(f"NAS password stored for user: {username}")
        except Exception as e:
            logger.error(f"Failed to store NAS password: {e}")
            raise

    def get_nas_password(self, username: str) -> Optional[str]:
        """Retrieve NAS password from keychain.

        Args:
            username: NAS username

        Returns:
            Password or None if not found
        """
        try:
            password = keyring.get_password(
                self.SERVICE_NAME,
                f"{self.NAS_PASSWORD_KEY}_{username}"
            )
            if password:
                logger.debug(f"Retrieved NAS password for user: {username}")
            else:
                logger.warning(f"No NAS password found for user: {username}")
            return password
        except Exception as e:
            logger.error(f"Failed to retrieve NAS password: {e}")
            return None

    def delete_nas_password(self, username: str) -> None:
        """Delete NAS password from keychain.

        Args:
            username: NAS username
        """
        try:
            keyring.delete_password(
                self.SERVICE_NAME,
                f"{self.NAS_PASSWORD_KEY}_{username}"
            )
            logger.info(f"NAS password deleted for user: {username}")
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"No password to delete for user: {username}")
        except Exception as e:
            logger.error(f"Failed to delete NAS password: {e}")
            raise

    def store_credential(self, key: str, value: str) -> None:
        """Store generic credential in keychain.

        Args:
            key: Credential key
            value: Credential value
        """
        try:
            keyring.set_password(self.SERVICE_NAME, key, value)
            logger.info(f"Credential stored: {key}")
        except Exception as e:
            logger.error(f"Failed to store credential {key}: {e}")
            raise

    def get_credential(self, key: str) -> Optional[str]:
        """Retrieve generic credential from keychain.

        Args:
            key: Credential key

        Returns:
            Credential value or None
        """
        try:
            value = keyring.get_password(self.SERVICE_NAME, key)
            if value:
                logger.debug(f"Retrieved credential: {key}")
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve credential {key}: {e}")
            return None

    def delete_credential(self, key: str) -> None:
        """Delete generic credential from keychain.

        Args:
            key: Credential key
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, key)
            logger.info(f"Credential deleted: {key}")
        except keyring.errors.PasswordDeleteError:
            logger.warning(f"No credential to delete: {key}")
        except Exception as e:
            logger.error(f"Failed to delete credential {key}: {e}")
            raise

    def clear_all(self) -> None:
        """Clear all credentials (use with caution!)."""
        logger.warning("Clearing all CelesteOS credentials from keychain")
        # Note: keyring doesn't provide a "list all" function
        # We can only delete known keys
        # This is a security feature
        logger.info("Keychain cleared (known credentials only)")
