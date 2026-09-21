"""Tromox WhatsApp MVP - Botmaker webhook service.

Receives Botmaker webhook callbacks, normalises them into lead records (shared
`tromox_lead` schema), stores them and notifies the sales group on escalation.
"""

__version__ = "0.1.0"
