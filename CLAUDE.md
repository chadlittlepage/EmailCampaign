# EmailCampaign - Claude Context

## Project Overview
LinkedIn email finder and Brevo campaign automation tool. Finds email addresses for LinkedIn connections and syncs them to Brevo for marketing campaigns.

## Primary Color
- Primary: #4a556c

## Tech Stack
- Python 3.10+
- Async/await for concurrent operations
- pandas for CSV processing
- dnspython for MX lookups
- aiohttp for HTTP requests
- sib-api-v3-sdk for Brevo integration

## Key Files
- `src/emailcampaign/email_finder.py` - Main orchestrator
- `src/emailcampaign/domain_finder.py` - Company name → domain lookup
- `src/emailcampaign/pattern_generator.py` - Email pattern generation
- `src/emailcampaign/email_verifier.py` - MX/SMTP verification
- `src/emailcampaign/brevo_client.py` - Brevo API integration
- `src/emailcampaign/cli.py` - Command-line interface

## Commands
```bash
# Find emails
python -m emailcampaign find input.csv output.csv

# Sync to Brevo
python -m emailcampaign sync output.csv --list "Campaign Name"

# Full pipeline
python -m emailcampaign pipeline input.csv --list "Campaign Name"

# Run tests
pytest

# Format code
black src/ tests/ && isort src/ tests/

# Lint
flake8 src/ tests/
```

## Environment Variables
- `BREVO_API_KEY` - Required for Brevo sync

## Code Style
- Black formatter (120 line length)
- isort for imports
- Type hints on all functions
- Async for I/O operations
- Docstrings on public functions

## Testing
- pytest with pytest-asyncio
- Mock external services (DNS, SMTP, Brevo API)
- Target 80% coverage

## CI/CD
- GitHub Actions on push/PR
- Runs: lint, type check, tests, security scan
- Dependabot for dependency updates
