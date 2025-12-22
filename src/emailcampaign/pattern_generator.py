"""
Email Pattern Generator - Creates possible email combinations from name + domain
"""
import re
from typing import List
from unidecode import unidecode  # Handle accented characters


def normalize_name(name: str) -> str:
    """Normalize a name for email generation"""
    if not name:
        return ""
    # Convert accented characters to ASCII
    try:
        name = unidecode(name)
    except:
        pass
    # Lowercase and remove special characters
    name = name.lower().strip()
    name = re.sub(r'[^a-z\s-]', '', name)
    # Handle hyphenated names
    name = name.replace('-', ' ')
    return name.strip()


def generate_email_patterns(first_name: str, last_name: str, domain: str) -> List[str]:
    """
    Generate possible email patterns for a person at a company.
    Returns list ordered by likelihood (most common patterns first).
    """
    first = normalize_name(first_name)
    last = normalize_name(last_name)

    if not first or not last or not domain:
        return []

    # Handle multi-part names (take first/last parts)
    first_parts = first.split()
    last_parts = last.split()

    f = first_parts[0] if first_parts else ""  # First name
    l = last_parts[-1] if last_parts else ""   # Last name (surname)

    if not f or not l:
        return []

    fi = f[0]  # First initial
    li = l[0]  # Last initial

    # Most common email patterns (ordered by frequency in business)
    patterns = [
        f"{f}.{l}",           # john.smith
        f"{f}{l}",            # johnsmith
        f"{fi}{l}",           # jsmith
        f"{f}_{l}",           # john_smith
        f"{f}",               # john
        f"{l}",               # smith
        f"{f}{li}",           # johns
        f"{fi}.{l}",          # j.smith
        f"{l}.{f}",           # smith.john
        f"{l}{f}",            # smithjohn
        f"{l}{fi}",           # smithj
        f"{fi}{li}",          # js
        f"{f}-{l}",           # john-smith
        f"{l}-{f}",           # smith-john
        f"{fi}_{l}",          # j_smith
        f"{f}.{li}",          # john.s
    ]

    # Generate full email addresses
    emails = [f"{pattern}@{domain}" for pattern in patterns]

    return emails


def generate_email_patterns_extended(first_name: str, last_name: str, domain: str) -> List[str]:
    """
    Extended patterns including numbers and additional variations.
    Use when basic patterns don't work.
    """
    basic = generate_email_patterns(first_name, last_name, domain)

    first = normalize_name(first_name)
    last = normalize_name(last_name)

    if not first or not last or not domain:
        return basic

    first_parts = first.split()
    f = first_parts[0] if first_parts else ""
    last_parts = last.split()
    l = last_parts[-1] if last_parts else ""

    if not f or not l:
        return basic

    # Extended patterns with numbers (common when duplicates exist)
    extended = []
    for num in ['1', '2', '01', '02']:
        extended.append(f"{f}.{l}{num}@{domain}")
        extended.append(f"{f}{l}{num}@{domain}")
        extended.append(f"{f[0]}{l}{num}@{domain}")

    # Patterns with middle initial (if available)
    if len(first_parts) > 1:
        mi = first_parts[1][0]  # Middle initial
        extended.append(f"{f}.{mi}.{l}@{domain}")
        extended.append(f"{f}{mi}{l}@{domain}")

    return basic + extended


# Test
if __name__ == "__main__":
    patterns = generate_email_patterns("John", "Smith", "acme.com")
    print("Basic patterns for John Smith @ acme.com:")
    for p in patterns:
        print(f"  {p}")

    patterns = generate_email_patterns("José María", "García-López", "empresa.com")
    print("\nPatterns for José María García-López @ empresa.com:")
    for p in patterns:
        print(f"  {p}")
