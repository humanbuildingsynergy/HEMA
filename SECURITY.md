# Security Policy

## Overview

HEMA is designed with security as a first-class concern. This document outlines the security practices, data handling procedures, and guidelines for reporting security vulnerabilities.

## Security Best Practices

### API Key Management

HEMA supports multiple LLM providers. To use HEMA securely:

1. **Set Environment Variables** (Never commit API keys to the repository)
   ```bash
   export OPENAI_API_KEY="your-key-here"
   export GOOGLE_API_KEY="your-key-here"
   export ANTHROPIC_API_KEY="your-key-here"
   ```

2. **Use `.env.example` as Template**
   - Copy `.env.example` to `.env` (local, not committed)
   - Fill in your actual API keys in `.env`
   - `.env` is in `.gitignore` - never commit it

3. **Local-First Option**
   - Use Ollama for local LLM processing (no API keys required)
   - See [Installation](README.md#installation) for Ollama setup
   - This is the most private option

### Data Privacy

HEMA handles home energy consumption data - sensitive information that deserves protection:

#### What HEMA Does NOT Do
- ❌ Store data in databases
- ❌ Send your energy data to external servers
- ❌ Collect or track user behavior
- ❌ Retain conversation history on disk (unless explicitly saved)

#### What HEMA Does
- ✅ Process data locally in memory during conversations
- ✅ Send data to LLM providers ONLY if you explicitly:
  - Ask questions that require analysis
  - Request recommendations using your data
- ✅ Allow you to control data flow via configuration
- ✅ Support local-only processing with Ollama (no cloud services)

#### Your Responsibilities
- Store your energy data securely
- Protect your `.env` file containing API keys
- Review conversation logs if you save them
- Choose cloud vs. local LLM based on privacy requirements

### Environment Setup

```bash
# Create isolated virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create local .env file (DO NOT COMMIT)
cp .env.example .env
# Edit .env with your actual API keys

# Verify .gitignore protects sensitive files
git check-ignore .env  # Should output: .env

# Never stage .env file
git status  # Should NOT show .env
```

## Supported Providers & Security

### Local Processing (Recommended for Maximum Privacy)
- **Ollama** (runs locally on your machine)
  - No API keys required
  - No data sent to external servers
  - Requires local GPU or CPU (depends on model size)

### Cloud Providers (Trade-off: Privacy vs. Capability)
- **OpenAI** - Requires OPENAI_API_KEY
  - Data Policy: Review at https://openai.com/policies/api-data-usage-policies
  - Fallback option with automatic retry

- **Google Gemini** - Requires GOOGLE_API_KEY
  - Data Policy: Review at https://ai.google.dev/
  - Fallback option with automatic retry

- **Anthropic Claude** - Requires ANTHROPIC_API_KEY
  - Data Policy: Review at https://www.anthropic.com/privacy

## Vulnerability Reporting

If you discover a security vulnerability in HEMA:

1. **DO NOT** open a public GitHub issue
2. **DO NOT** include sensitive details in public comments
3. **Instead**, contact the maintainer directly:
   - **Email**: wooyoung -at- arizona -dot- edu
   - **Subject**: "HEMA Security Vulnerability"
   - Include: description, steps to reproduce, potential impact, suggested fix (if any)

4. **Response Timeline**:
   - Initial acknowledgment: Within 48 hours
   - Assessment: Within 1 week
   - Fix timeline: Depends on severity
   - Public disclosure: After fix is released

## Security Considerations for Production Deployment

If deploying HEMA in a production environment:

### Network Security
- Use HTTPS/TLS for API endpoints
- Implement authentication/authorization
- Restrict access to authorized users only
- Use environment-specific configuration

### Data Security
- Encrypt data at rest if storing conversation history
- Implement database-level encryption if using persistent storage
- Use secure connection strings with credentials in environment variables
- Regularly backup and test disaster recovery

### Access Control
- Implement user authentication for web interface
- Use role-based access control if needed
- Audit and log API access
- Implement rate limiting to prevent abuse

### Monitoring & Logging
- Monitor for suspicious API usage patterns
- Log security-relevant events
- Set up alerts for unusual activity
- Review logs regularly

## Dependency Security

HEMA depends on several open-source libraries. Security practices:

- **Regular Updates**: Dependencies are updated regularly
- **Vulnerability Scanning**: Monitor for known vulnerabilities
- **Minimal Dependencies**: Only essential packages included
- **Trustworthy Sources**: All packages from PyPI (for Python) and npm (for JavaScript)

To check for vulnerable dependencies:
```bash
pip audit  # Check Python dependencies
npm audit  # Check JavaScript dependencies
```

## Code Security

### Input Validation
- User queries are validated before processing
- API inputs are sanitized
- File uploads (if any) are validated

### Output Handling
- LLM responses are treated as untrusted
- HTML/code in responses is properly escaped
- No direct command execution from LLM outputs

## Security Testing

The codebase undergoes security testing:
- Secrets scanning (no hardcoded API keys)
- Dependency vulnerability scanning
- Manual code review for security issues
- Regular security audits before releases

## Compliance

- **GPL-3.0 License**: Open-source software with transparency requirements
- **Data Handling**: Designed for GDPR compliance (minimal data collection, user control)
- **Privacy First**: Supports local-only processing without external data transmission

## Updates & Patches

- Security patches are released promptly
- Users should keep HEMA and dependencies updated
- Subscribe to releases for security announcements

## Questions?

For security-related questions (non-vulnerability):
- Check this document and the main [README.md](README.md)
- Open a GitHub Discussion for general security questions
- Contact the maintainer for specific deployment concerns

---

**Last Updated**: February 2026
**Maintained By**: Dr. Wooyoung Jung, Human-Building Synergy Lab, University of Arizona
