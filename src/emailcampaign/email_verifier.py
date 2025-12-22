"""
Email Verifier - Verifies if email addresses exist using SMTP
"""
import asyncio
import dns.resolver
import socket
import re
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from enum import Enum


class VerificationResult(Enum):
    VALID = "valid"           # Email exists
    INVALID = "invalid"       # Email doesn't exist
    CATCH_ALL = "catch_all"   # Domain accepts all emails (can't verify)
    UNKNOWN = "unknown"       # Couldn't determine (timeout, blocked, etc.)


@dataclass
class EmailVerification:
    email: str
    result: VerificationResult
    message: str


# Cache for MX records
mx_cache: Dict[str, list] = {}


async def get_mx_records(domain: str) -> list:
    """Get MX records for a domain"""
    if domain in mx_cache:
        return mx_cache[domain]

    try:
        records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in records])
        mx_cache[domain] = [host for _, host in mx_hosts]
        return mx_cache[domain]
    except Exception as e:
        return []


async def verify_email_mx_only(email: str) -> EmailVerification:
    """
    Lightweight verification - just check if domain has MX records.
    Use this when SMTP port 25 is blocked.
    """
    if not email or '@' not in email:
        return EmailVerification(email, VerificationResult.INVALID, "Invalid email format")

    local_part, domain = email.rsplit('@', 1)

    mx_hosts = await get_mx_records(domain)
    if mx_hosts:
        return EmailVerification(email, VerificationResult.VALID, "Domain can receive email (MX verified)")
    else:
        return EmailVerification(email, VerificationResult.INVALID, "No MX records - domain cannot receive email")


async def verify_email_smtp(email: str, timeout: int = 10) -> EmailVerification:
    """
    Verify an email address exists using SMTP.

    This works by:
    1. Finding the MX records for the domain
    2. Connecting to the mail server
    3. Sending RCPT TO command to check if recipient exists

    Note: Many servers block this or return catch-all responses.
    """
    if not email or '@' not in email:
        return EmailVerification(email, VerificationResult.INVALID, "Invalid email format")

    local_part, domain = email.rsplit('@', 1)

    # Get MX records
    mx_hosts = await get_mx_records(domain)
    if not mx_hosts:
        return EmailVerification(email, VerificationResult.UNKNOWN, "No MX records found")

    # Try each MX host
    for mx_host in mx_hosts[:2]:  # Try top 2 MX servers
        try:
            result = await _check_smtp(email, mx_host, timeout)
            if result.result != VerificationResult.UNKNOWN:
                return result
        except Exception as e:
            continue

    # Fallback to MX-only verification if SMTP is blocked
    return await verify_email_mx_only(email)


async def _check_smtp(email: str, mx_host: str, timeout: int) -> EmailVerification:
    """Check email via SMTP connection"""
    try:
        # Create connection
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(mx_host, 25),
            timeout=timeout
        )

        try:
            # Read greeting
            response = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not response.startswith(b'220'):
                return EmailVerification(email, VerificationResult.UNKNOWN, "Bad greeting")

            # HELO
            writer.write(b'HELO verify.local\r\n')
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=timeout)

            # MAIL FROM
            writer.write(b'MAIL FROM:<verify@verify.local>\r\n')
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not response.startswith(b'250'):
                return EmailVerification(email, VerificationResult.UNKNOWN, "MAIL FROM rejected")

            # RCPT TO - This is the key check
            writer.write(f'RCPT TO:<{email}>\r\n'.encode())
            await writer.drain()
            response = await asyncio.wait_for(reader.readline(), timeout=timeout)

            # Analyze response
            code = response[:3].decode() if len(response) >= 3 else ""
            message = response.decode().strip()

            if code == '250':
                # Check for catch-all by testing fake email
                is_catch_all = await _check_catch_all(reader, writer, email.split('@')[1], timeout)
                if is_catch_all:
                    return EmailVerification(email, VerificationResult.CATCH_ALL, "Domain accepts all emails")
                return EmailVerification(email, VerificationResult.VALID, "Email exists")
            elif code in ('550', '551', '552', '553', '554'):
                return EmailVerification(email, VerificationResult.INVALID, message)
            elif code == '450' or code == '451':
                return EmailVerification(email, VerificationResult.UNKNOWN, "Temporary error")
            else:
                return EmailVerification(email, VerificationResult.UNKNOWN, message)

        finally:
            writer.write(b'QUIT\r\n')
            await writer.drain()
            writer.close()
            await writer.wait_closed()

    except asyncio.TimeoutError:
        return EmailVerification(email, VerificationResult.UNKNOWN, "Connection timeout")
    except Exception as e:
        return EmailVerification(email, VerificationResult.UNKNOWN, str(e))


async def _check_catch_all(reader, writer, domain: str, timeout: int) -> bool:
    """Check if domain is catch-all by testing fake email"""
    try:
        fake_email = f"nonexistent_user_test_12345@{domain}"
        writer.write(f'RCPT TO:<{fake_email}>\r\n'.encode())
        await writer.drain()
        response = await asyncio.wait_for(reader.readline(), timeout=timeout)
        code = response[:3].decode() if len(response) >= 3 else ""
        return code == '250'  # If fake email accepted, it's catch-all
    except:
        return False


async def verify_emails_batch(emails: list, concurrency: int = 5) -> list:
    """Verify multiple emails with concurrency limit"""
    semaphore = asyncio.Semaphore(concurrency)

    async def verify_with_limit(email):
        async with semaphore:
            return await verify_email_smtp(email)

    tasks = [verify_with_limit(email) for email in emails]
    return await asyncio.gather(*tasks)


def quick_syntax_check(email: str) -> bool:
    """Quick syntax validation before SMTP check"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# Test
if __name__ == "__main__":
    async def test():
        emails = [
            "test@google.com",
            "definitely_not_real_user@google.com",
        ]
        for email in emails:
            result = await verify_email_smtp(email)
            print(f"{email}: {result.result.value} - {result.message}")

    asyncio.run(test())
