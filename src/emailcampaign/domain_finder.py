"""
Domain Finder - Finds company domains from company names
"""
import re
import asyncio
import aiohttp
from urllib.parse import urlparse, quote_plus
from typing import Optional, Dict
import json


# Common company domain mappings (for speed)
KNOWN_DOMAINS: Dict[str, str] = {
    "google": "google.com",
    "microsoft": "microsoft.com",
    "apple": "apple.com",
    "amazon": "amazon.com",
    "meta": "meta.com",
    "facebook": "meta.com",
    "netflix": "netflix.com",
    "salesforce": "salesforce.com",
    "oracle": "oracle.com",
    "ibm": "ibm.com",
    "intel": "intel.com",
    "cisco": "cisco.com",
    "adobe": "adobe.com",
    "spotify": "spotify.com",
    "uber": "uber.com",
    "airbnb": "airbnb.com",
    "linkedin": "linkedin.com",
    "twitter": "x.com",
    "stripe": "stripe.com",
    "shopify": "shopify.com",
    "slack": "slack.com",
    "zoom": "zoom.us",
    "dropbox": "dropbox.com",
    "hubspot": "hubspot.com",
    "mailchimp": "mailchimp.com",
    "twilio": "twilio.com",
    "datadog": "datadoghq.com",
    "snowflake": "snowflake.com",
    "palantir": "palantir.com",
}


def normalize_company_name(company: str) -> str:
    """Normalize company name for matching"""
    # Remove common suffixes
    suffixes = [
        r'\s+inc\.?$', r'\s+llc\.?$', r'\s+ltd\.?$', r'\s+corp\.?$',
        r'\s+corporation$', r'\s+company$', r'\s+co\.?$', r'\s+group$',
        r'\s+holdings?$', r'\s+technologies$', r'\s+technology$',
        r'\s+solutions$', r'\s+services$', r'\s+international$',
        r'\s+worldwide$', r'\s+global$', r',.*$'
    ]

    normalized = company.lower().strip()
    for suffix in suffixes:
        normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

    return normalized.strip()


def guess_domain_from_name(company: str) -> Optional[str]:
    """Guess domain directly from company name"""
    normalized = normalize_company_name(company)

    # Check known domains
    for key, domain in KNOWN_DOMAINS.items():
        if key in normalized or normalized in key:
            return domain

    # Try simple transformations
    # Remove spaces and special chars
    simple = re.sub(r'[^a-z0-9]', '', normalized)
    if simple:
        return f"{simple}.com"

    return None


async def search_domain_duckduckgo(company: str, session: aiohttp.ClientSession) -> Optional[str]:
    """Search DuckDuckGo for company domain"""
    try:
        query = quote_plus(f"{company} official website")
        url = f"https://html.duckduckgo.com/html/?q={query}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                text = await response.text()
                # Extract URLs from results
                urls = re.findall(r'href="(https?://[^"]+)"', text)

                # Filter for likely company domains
                normalized = normalize_company_name(company)
                for url in urls[:10]:
                    try:
                        parsed = urlparse(url)
                        domain = parsed.netloc.lower()
                        # Skip search engines and common sites
                        skip = ['duckduckgo', 'google', 'bing', 'yahoo', 'wikipedia',
                                'linkedin.com', 'facebook.com', 'twitter.com', 'youtube.com',
                                'glassdoor', 'indeed', 'crunchbase', 'bloomberg']
                        if any(s in domain for s in skip):
                            continue
                        # Check if company name is in domain
                        domain_base = domain.replace('www.', '')
                        if any(word in domain_base for word in normalized.split() if len(word) > 2):
                            return domain_base
                    except:
                        continue
    except Exception as e:
        pass

    return None


async def verify_domain_exists(domain: str, session: aiohttp.ClientSession) -> bool:
    """Verify a domain exists by checking if it resolves"""
    import dns.resolver

    try:
        # Check MX records (indicates email capability)
        dns.resolver.resolve(domain, 'MX')
        return True
    except:
        try:
            # Fallback to A record
            dns.resolver.resolve(domain, 'A')
            return True
        except:
            return False


async def find_domain(company: str, session: aiohttp.ClientSession, cache: dict = None) -> Optional[str]:
    """Find domain for a company name"""
    if not company or company.strip() == '':
        return None

    # Check cache first
    cache_key = normalize_company_name(company)
    if cache and cache_key in cache:
        return cache[cache_key]

    # Try direct guess first (fast)
    guessed = guess_domain_from_name(company)
    if guessed:
        exists = await verify_domain_exists(guessed, session)
        if exists:
            if cache is not None:
                cache[cache_key] = guessed
            return guessed

    # Try web search (slower but more accurate)
    searched = await search_domain_duckduckgo(company, session)
    if searched:
        exists = await verify_domain_exists(searched, session)
        if exists:
            if cache is not None:
                cache[cache_key] = searched
            return searched

    # Return guessed domain even if we couldn't verify
    if guessed:
        if cache is not None:
            cache[cache_key] = guessed
        return guessed

    return None


# Test
if __name__ == "__main__":
    async def test():
        async with aiohttp.ClientSession() as session:
            companies = ["Microsoft", "Acme Corp", "Spotify", "Some Random Startup LLC"]
            for company in companies:
                domain = await find_domain(company, session)
                print(f"{company} -> {domain}")

    asyncio.run(test())
