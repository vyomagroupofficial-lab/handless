"""Secure Credential Management for Vyoma Handless.

Stores sensitive credentials (such as Google Gemini API keys) in the
native Windows Credential Manager via the `keyring` library, ensuring
credentials are encrypted at rest by Windows DPAPI and never stored
in plaintext files on disk.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import keyring

logger = logging.getLogger(__name__)

SERVICE_NAME = "VyomaHandless"
GEMINI_KEY_ACCOUNT = "gemini_api_key"


def get_gemini_api_key() -> Optional[str]:
    """Retrieve the Gemini API key from Windows Credential Manager or environment.

    First checks the Windows Credential Manager. If not found, falls back
    to the GEMINI_API_KEY environment variable.

    Returns:
        The API key string if available, otherwise None.
    """
    try:
        stored_key = keyring.get_password(SERVICE_NAME, GEMINI_KEY_ACCOUNT)
        if stored_key and stored_key.strip():
            return stored_key.strip()
    except Exception as exc:
        logger.warning("Could not read credential from Windows Credential Manager: %s", exc)

    # Fallback to environment variable if present
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return env_key if env_key else None


def store_gemini_api_key(api_key: str) -> bool:
    """Store the Gemini API key securely in Windows Credential Manager.

    Args:
        api_key: The Google AI Studio Gemini API key.

    Returns:
        True if stored successfully, False otherwise.
    """
    cleaned_key = api_key.strip()
    if not cleaned_key:
        return False

    try:
        keyring.set_password(SERVICE_NAME, GEMINI_KEY_ACCOUNT, cleaned_key)
        logger.info("Gemini API key successfully stored in Windows Credential Manager.")
        return True
    except Exception as exc:
        logger.error("Failed to store credential in Windows Credential Manager: %s", exc)
        return False


def delete_gemini_api_key() -> bool:
    """Remove the stored Gemini API key from Windows Credential Manager.

    Returns:
        True if deleted or was absent, False on error.
    """
    try:
        keyring.delete_password(SERVICE_NAME, GEMINI_KEY_ACCOUNT)
        logger.info("Gemini API key removed from Windows Credential Manager.")
        return True
    except keyring.errors.PasswordDeleteError:
        return True
    except Exception as exc:
        logger.error("Failed to delete credential from Windows Credential Manager: %s", exc)
        return False


def has_gemini_api_key() -> bool:
    """Check whether a Gemini API key is configured."""
    key = get_gemini_api_key()
    return bool(key and len(key) > 5)


GROQ_KEY_ACCOUNT = "groq_api_key"


def get_groq_api_key() -> Optional[str]:
    """Retrieve the Groq API key from Windows Credential Manager or environment."""
    try:
        stored_key = keyring.get_password(SERVICE_NAME, GROQ_KEY_ACCOUNT)
        if stored_key and stored_key.strip():
            return stored_key.strip()
    except Exception as exc:
        logger.warning("Could not read Groq credential from Windows Credential Manager: %s", exc)

    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    return env_key if env_key else None


def store_groq_api_key(api_key: str) -> bool:
    """Store the Groq API key securely in Windows Credential Manager."""
    cleaned_key = api_key.strip()
    if not cleaned_key:
        return False

    try:
        keyring.set_password(SERVICE_NAME, GROQ_KEY_ACCOUNT, cleaned_key)
        logger.info("Groq API key successfully stored in Windows Credential Manager.")
        return True
    except Exception as exc:
        logger.error("Failed to store Groq credential in Windows Credential Manager: %s", exc)
        return False


def delete_groq_api_key() -> bool:
    """Remove the stored Groq API key from Windows Credential Manager."""
    try:
        keyring.delete_password(SERVICE_NAME, GROQ_KEY_ACCOUNT)
        logger.info("Groq API key removed from Windows Credential Manager.")
        return True
    except keyring.errors.PasswordDeleteError:
        return True
    except Exception as exc:
        logger.error("Failed to delete Groq credential from Windows Credential Manager: %s", exc)
        return False


def has_groq_api_key() -> bool:
    """Check whether a Groq API key is configured."""
    key = get_groq_api_key()
    return bool(key and len(key) > 5)

