#!/usr/bin/env python3
"""
EmailCampaign CLI - Find emails and sync to Brevo
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="EmailCampaign - LinkedIn email finder and Brevo sync",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find emails for LinkedIn connections
  emailcampaign find connections.csv output.csv

  # Sync contacts with emails to Brevo
  emailcampaign sync output.csv --list "My Campaign"

  # Full pipeline: find emails and sync to Brevo
  emailcampaign pipeline connections.csv --list "LinkedIn Q1 2025"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Find emails command
    find_parser = subparsers.add_parser("find", help="Find emails for LinkedIn connections")
    find_parser.add_argument("input", help="Input CSV file (LinkedIn export)")
    find_parser.add_argument("output", help="Output CSV file with emails")
    find_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip email verification (faster but less accurate)",
    )
    find_parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Number of concurrent lookups (default: 3)",
    )

    # Sync to Brevo command
    sync_parser = subparsers.add_parser("sync", help="Sync contacts to Brevo")
    sync_parser.add_argument("input", help="CSV file with 'Found Email' column")
    sync_parser.add_argument(
        "--list",
        default="LinkedIn Connections",
        help="Brevo list name (default: 'LinkedIn Connections')",
    )
    sync_parser.add_argument(
        "--api-key",
        help="Brevo API key (or set BREVO_API_KEY env var)",
    )

    # Full pipeline command
    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="Full pipeline: find emails and sync to Brevo",
    )
    pipeline_parser.add_argument("input", help="Input CSV file (LinkedIn export)")
    pipeline_parser.add_argument(
        "--list",
        default="LinkedIn Connections",
        help="Brevo list name",
    )
    pipeline_parser.add_argument(
        "--output",
        help="Output CSV file (default: input_with_emails.csv)",
    )

    args = parser.parse_args()

    if args.command == "find":
        from .email_finder import LinkedInEmailFinder

        async def run_find():
            finder = LinkedInEmailFinder(
                concurrency=args.concurrency,
                verify=not args.no_verify,
            )
            await finder.process_csv(args.input, args.output)

        print(
            """
╔═══════════════════════════════════════════════════════════════╗
║           EmailCampaign - Email Finder                        ║
║   Find & verify emails for your LinkedIn connections          ║
╚═══════════════════════════════════════════════════════════════╝
        """
        )
        asyncio.run(run_find())

    elif args.command == "sync":
        from .brevo_client import sync_linkedin_to_brevo

        print(
            """
╔═══════════════════════════════════════════════════════════════╗
║           EmailCampaign - Brevo Sync                          ║
║   Sync your contacts to Brevo for campaigns                   ║
╚═══════════════════════════════════════════════════════════════╝
        """
        )

        try:
            result = sync_linkedin_to_brevo(
                csv_path=args.input,
                api_key=args.api_key,
                list_name=args.list,
            )

            print("\n" + "=" * 50)
            print("SYNC COMPLETE")
            print("=" * 50)
            print(f"Total contacts:  {result.total}")
            print(f"Created/Updated: {result.created}")
            print(f"Failed:          {result.failed}")
            if result.errors:
                print(f"\nErrors ({len(result.errors)}):")
                for err in result.errors[:10]:
                    print(f"  - {err}")
                if len(result.errors) > 10:
                    print(f"  ... and {len(result.errors) - 10} more")
            print("=" * 50)

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif args.command == "pipeline":
        from .email_finder import LinkedInEmailFinder
        from .brevo_client import sync_linkedin_to_brevo

        print(
            """
╔═══════════════════════════════════════════════════════════════╗
║           EmailCampaign - Full Pipeline                       ║
║   Find emails → Sync to Brevo                                 ║
╚═══════════════════════════════════════════════════════════════╝
        """
        )

        # Determine output path
        input_path = Path(args.input)
        output_path = args.output or str(
            input_path.parent / f"{input_path.stem}_with_emails.csv"
        )

        # Step 1: Find emails
        print("\n📧 Step 1: Finding emails...")

        async def run_find():
            finder = LinkedInEmailFinder(concurrency=3, verify=True)
            await finder.process_csv(args.input, output_path)

        asyncio.run(run_find())

        # Step 2: Sync to Brevo
        print("\n📤 Step 2: Syncing to Brevo...")
        try:
            result = sync_linkedin_to_brevo(
                csv_path=output_path,
                list_name=args.list,
            )
            print(f"✅ Synced {result.created} contacts to Brevo list: {args.list}")
        except Exception as e:
            print(f"❌ Brevo sync failed: {e}")
            print("   Set BREVO_API_KEY and try: emailcampaign sync " + output_path)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
