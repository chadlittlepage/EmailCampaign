# EmailCampaign

LinkedIn email finder and Brevo campaign automation with FAANG-level infrastructure.

## Features

- **Email Finder**: Find email addresses for your LinkedIn connections
  - Smart domain detection from company names
  - Email pattern generation (firstname.lastname@, jsmith@, etc.)
  - MX record verification
  - Handles international names (unicode support)

- **Brevo Integration**: Sync contacts for marketing campaigns
  - Create/update contacts automatically
  - Organize into lists
  - Ready for campaign creation

- **FAANG Infrastructure**
  - GitHub Actions CI/CD
  - Code quality (Black, Flake8, MyPy)
  - Security scanning (Bandit, Safety)
  - Dependabot for dependency updates

## Quick Start

### 1. Install

```bash
cd /Users/chadlittlepage/Documents/APPs/EmailCampaign
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Find Emails

Export your LinkedIn connections:
- LinkedIn → Settings → Data Privacy → Get a copy of your data → Connections

Run the email finder:

```bash
python -m emailcampaign find ~/Downloads/Connections.csv output.csv
```

### 3. Sync to Brevo

Set your Brevo API key:

```bash
export BREVO_API_KEY="your-api-key-here"
```

Sync contacts:

```bash
python -m emailcampaign sync output.csv --list "LinkedIn Q1 2025"
```

### Full Pipeline

Run everything in one command:

```bash
python -m emailcampaign pipeline ~/Downloads/Connections.csv --list "My Campaign"
```

## CLI Commands

```
emailcampaign find <input.csv> <output.csv>    Find emails for LinkedIn contacts
emailcampaign sync <input.csv> --list "Name"   Sync contacts to Brevo
emailcampaign pipeline <input.csv>             Full pipeline: find + sync
```

## Project Structure

```
EmailCampaign/
├── src/emailcampaign/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── domain_finder.py    # Company → domain lookup
│   ├── email_finder.py     # Main email finding logic
│   ├── email_verifier.py   # Email verification (MX/SMTP)
│   ├── pattern_generator.py # Email pattern generation
│   └── brevo_client.py     # Brevo API integration
├── tests/
├── .github/workflows/      # CI/CD pipelines
├── .claude/agents/         # AI code review agents
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Configuration

Create a `.env` file:

```env
BREVO_API_KEY=your-brevo-api-key
```

## Getting Brevo API Key

1. Log into [Brevo](https://app.brevo.com)
2. Go to Settings → API Keys
3. Create a new API key with full access
4. Copy and save securely

## How Email Finding Works

1. **Domain Detection**: Given "Microsoft", find "microsoft.com"
   - Known company database
   - Web search fallback
   - MX record verification

2. **Pattern Generation**: For "John Smith" at "acme.com":
   - john.smith@acme.com
   - jsmith@acme.com
   - john@acme.com
   - smith.john@acme.com
   - etc.

3. **Verification**: Check if email exists
   - MX record lookup (always works)
   - SMTP verification (when network allows)

## Expected Results

- **Hit rate**: 30-50% of contacts will get verified emails
- **Catch-all domains**: Some domains accept all emails (marked separately)
- **No domain**: Some companies can't be mapped to domains

## Legal Considerations

- Only use for people you're connected to on LinkedIn
- Comply with CAN-SPAM and GDPR
- Include unsubscribe links in campaigns
- Respect opt-outs

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

## License

MIT
