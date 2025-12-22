#!/usr/bin/env python3
"""
LinkedIn Email Finder
Finds and verifies email addresses for LinkedIn connections.

Usage:
    python email_finder.py input.csv output.csv

Input CSV should have columns: First Name, Last Name, Company
Output CSV will have an additional 'Found Email' column
"""
import asyncio
import argparse
import pandas as pd
import aiohttp
from tqdm import tqdm
from typing import Optional, Dict, List
from dataclasses import dataclass
import json
import os
from datetime import datetime

from domain_finder import find_domain
from pattern_generator import generate_email_patterns
from email_verifier import verify_email_smtp, VerificationResult, quick_syntax_check


@dataclass
class ContactResult:
    first_name: str
    last_name: str
    company: str
    domain: Optional[str]
    found_email: Optional[str]
    verification_status: str
    patterns_tried: int


class LinkedInEmailFinder:
    def __init__(self, concurrency: int = 3, verify: bool = True):
        self.concurrency = concurrency
        self.verify = verify
        self.domain_cache: Dict[str, str] = {}
        self.stats = {
            'total': 0,
            'found': 0,
            'verified': 0,
            'catch_all': 0,
            'no_domain': 0,
            'no_match': 0,
        }

    async def find_email_for_contact(
        self,
        first_name: str,
        last_name: str,
        company: str,
        session: aiohttp.ClientSession
    ) -> ContactResult:
        """Find email for a single contact"""

        # Skip if missing required fields
        if not first_name or not last_name or not company:
            return ContactResult(
                first_name=first_name or "",
                last_name=last_name or "",
                company=company or "",
                domain=None,
                found_email=None,
                verification_status="missing_data",
                patterns_tried=0
            )

        # Find domain
        domain = await find_domain(company, session, self.domain_cache)
        if not domain:
            self.stats['no_domain'] += 1
            return ContactResult(
                first_name=first_name,
                last_name=last_name,
                company=company,
                domain=None,
                found_email=None,
                verification_status="no_domain",
                patterns_tried=0
            )

        # Generate email patterns
        patterns = generate_email_patterns(first_name, last_name, domain)

        if not patterns:
            return ContactResult(
                first_name=first_name,
                last_name=last_name,
                company=company,
                domain=domain,
                found_email=None,
                verification_status="no_patterns",
                patterns_tried=0
            )

        # If not verifying, return first pattern
        if not self.verify:
            self.stats['found'] += 1
            return ContactResult(
                first_name=first_name,
                last_name=last_name,
                company=company,
                domain=domain,
                found_email=patterns[0],
                verification_status="unverified",
                patterns_tried=1
            )

        # Try to verify each pattern
        for i, email in enumerate(patterns[:8]):  # Limit to top 8 patterns
            if not quick_syntax_check(email):
                continue

            result = await verify_email_smtp(email, timeout=10)

            if result.result == VerificationResult.VALID:
                self.stats['verified'] += 1
                self.stats['found'] += 1
                return ContactResult(
                    first_name=first_name,
                    last_name=last_name,
                    company=company,
                    domain=domain,
                    found_email=email,
                    verification_status="verified",
                    patterns_tried=i + 1
                )
            elif result.result == VerificationResult.CATCH_ALL:
                # Domain accepts all, return most likely pattern
                self.stats['catch_all'] += 1
                self.stats['found'] += 1
                return ContactResult(
                    first_name=first_name,
                    last_name=last_name,
                    company=company,
                    domain=domain,
                    found_email=patterns[0],  # Most common pattern
                    verification_status="catch_all",
                    patterns_tried=i + 1
                )

            # Small delay between verification attempts
            await asyncio.sleep(0.5)

        # No valid email found
        self.stats['no_match'] += 1
        return ContactResult(
            first_name=first_name,
            last_name=last_name,
            company=company,
            domain=domain,
            found_email=None,
            verification_status="not_found",
            patterns_tried=len(patterns[:8])
        )

    async def process_csv(
        self,
        input_path: str,
        output_path: str,
        progress_callback=None
    ) -> Dict:
        """Process a LinkedIn CSV file"""

        # Read CSV
        print(f"\nReading {input_path}...")
        df = pd.read_csv(input_path, skiprows=3)  # LinkedIn CSVs have 3 header rows

        # Normalize column names
        df.columns = df.columns.str.strip()

        # Check for required columns
        required = ['First Name', 'Last Name', 'Company']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        self.stats['total'] = len(df)
        print(f"Found {len(df)} contacts to process\n")

        # Add new columns
        df['Found Email'] = None
        df['Email Status'] = None
        df['Domain'] = None

        # Process contacts
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.concurrency)

            async def process_row(idx, row):
                async with semaphore:
                    result = await self.find_email_for_contact(
                        str(row.get('First Name', '')).strip(),
                        str(row.get('Last Name', '')).strip(),
                        str(row.get('Company', '')).strip(),
                        session
                    )
                    return idx, result

            # Create tasks
            tasks = [
                process_row(idx, row)
                for idx, row in df.iterrows()
            ]

            # Process with progress bar
            results = []
            with tqdm(total=len(tasks), desc="Finding emails") as pbar:
                for coro in asyncio.as_completed(tasks):
                    idx, result = await coro
                    df.at[idx, 'Found Email'] = result.found_email
                    df.at[idx, 'Email Status'] = result.verification_status
                    df.at[idx, 'Domain'] = result.domain
                    results.append(result)
                    pbar.update(1)

                    # Save progress periodically
                    if len(results) % 50 == 0:
                        df.to_csv(output_path, index=False)

        # Final save
        df.to_csv(output_path, index=False)
        print(f"\nResults saved to {output_path}")

        # Print stats
        print("\n" + "="*50)
        print("RESULTS SUMMARY")
        print("="*50)
        print(f"Total contacts:     {self.stats['total']}")
        print(f"Emails found:       {self.stats['found']}")
        print(f"  - Verified:       {self.stats['verified']}")
        print(f"  - Catch-all:      {self.stats['catch_all']}")
        print(f"No domain found:    {self.stats['no_domain']}")
        print(f"No email matched:   {self.stats['no_match']}")
        print(f"Success rate:       {self.stats['found']/max(self.stats['total'],1)*100:.1f}%")
        print("="*50)

        return self.stats


async def main():
    parser = argparse.ArgumentParser(
        description="Find email addresses for LinkedIn connections"
    )
    parser.add_argument('input', help='Input CSV file (LinkedIn export)')
    parser.add_argument('output', help='Output CSV file with emails')
    parser.add_argument(
        '--no-verify', action='store_true',
        help='Skip email verification (faster but less accurate)'
    )
    parser.add_argument(
        '--concurrency', type=int, default=3,
        help='Number of concurrent lookups (default: 3)'
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}")
        return

    finder = LinkedInEmailFinder(
        concurrency=args.concurrency,
        verify=not args.no_verify
    )

    await finder.process_csv(args.input, args.output)


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           LinkedIn Email Finder                               ║
║   Find & verify emails for your LinkedIn connections          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())
