"""
EmailCampaign - LinkedIn email finder and Brevo campaign automation

Find email addresses for your LinkedIn connections and sync them to Brevo
for automated marketing campaigns.
"""

__version__ = "1.0.0"
__author__ = "Chad Littlepage"

from .domain_finder import find_domain
from .pattern_generator import generate_email_patterns
from .email_verifier import verify_email_smtp, VerificationResult

__all__ = [
    "find_domain",
    "generate_email_patterns",
    "verify_email_smtp",
    "VerificationResult",
]
