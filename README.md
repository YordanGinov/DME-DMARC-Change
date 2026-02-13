# DNSMadeEasy DMARC Record Manager

A Python utility to identify and update non-compliant DMARC records across your DNS domains managed by DNSMadeEasy.

## Features

- **Domain Scanning**: Retrieves all managed domains from your DNSMadeEasy account
- **DMARC Detection**: Identifies domains with missing or non-compliant DMARC records
- **Batch Updates**: Updates existing DMARC records and adds new ones in a single operation
- **Data Persistence**: Writes results immediately to files during scanning to preserve data if requests fail
- **Rate Limiting**: Includes built-in delays to respect API rate limits
- **Business Logic**: Respects a configurable ignore list for critical business domains

## Prerequisites

- Python 3.11 or higher
- uv installed (https://docs.astral.sh/uv/)
- DNSMadeEasy API credentials (API Key and Secret)
- Internet connectivity to access DNSMadeEasy API

## Installation

1. Clone or download this repository
2. Create/update the environment with uv:

```bash
uv sync
```

## Usage

Run the script:

```bash
uv run python DNSMadeEasy-DMARC-Fix.py
```

You will be prompted to enter your API Key and Secret. The script presents an interactive menu:

### Option 1: Extract DMARC Records

Scans all domains and identifies:
- **Domains without any DMARC record** → saved to `domains_without_dmarc.txt`
- **Domains with non-compliant DMARC records** → saved to `domains_with_dmarc.txt`

Results are written immediately as processing occurs, ensuring data is preserved even if the scan fails partway through.

### Option 2: Update DMARC Records

Updates all identified domains with the new DMARC policy:

```
v=DMARC1; p=reject; sp=reject; fo=1
```

This operation:
- Updates existing DMARC records from `domains_with_dmarc.txt`
- Adds new DMARC records for domains in `domains_without_dmarc.txt`
- Reports success/failure for each domain

### Option 3: Exit

Closes the script.

## Configuration

Modify these sections in `DNSMadeEasy-DMARC-Fix.py` as needed:

**Known DMARC Policies** - Policies considered non-compliant and needing updates:
```python
KNOWN_DMARC_POLICIES = {
    "v=DMARC1; p=none",
    # ... other policies
}
```

**Domains to Ignore** - Business-critical domains that should never be updated:
```python
DOMAINS_TO_IGNORE = {
    "critical-domain.example",
    # ... other domains to ignore
}
```

**New DMARC Policy** - The policy applied during updates (currently):
```python
new_dmarc_value = "v=DMARC1; p=reject; sp=reject; fo=1"
```

## Output Files

**domains_without_dmarc.txt**
Format: `domain_name:domain_id`
```
domain.example:12345
another.example:67890
```

**domains_with_dmarc.txt**
Format: `domain_name:domain_id:record_id:normalized_dmarc_value`
```
domain.example:12345:98765:v=DMARC1; p=none
another.example:67890:54321:v=DMARC1; p=reject; sp=none; pct=40
```

## Error Handling

The script includes comprehensive error handling:
- Individual domain failures don't stop the entire process
- Failed operations are logged to console
- Success/failure counts displayed at completion
- All API responses checked before processing

## Rate Limiting

The script includes a 2-second delay between API calls to respect DNSMadeEasy's rate limits. Adjust `REQUEST_SLEEP` if needed:

```python
REQUEST_SLEEP = 2  # seconds between API calls
```

## Security Considerations

⚠️ **IMPORTANT**: API credentials are requested at runtime and never stored in files!

- API Key and Secret are entered interactively when running the script
- Credentials are never saved to disk
- Use strong, unique API credentials
- Rotate API credentials regularly

## Troubleshooting

**API Connection Errors**
- Verify your API credentials are correct
- Check your internet connection
- Ensure the API URL is accessible from your network
- Verify the API credentials have the necessary permissions

**No domains found**
- Verify your DNSMadeEasy account has managed domains
- Check that your API credentials have the necessary permissions

**Permission Denied when updating records**
- Ensure your API credentials have write permissions
- Check domain name spelling in DOMAINS_TO_IGNORE

## License

[Add your license here]

## Support

For issues or questions:
- Check DNSMadeEasy API documentation: https://api-docs.dnsmadeeasy.com/
- Review the script comments for detailed explanations
