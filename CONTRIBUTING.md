# Contributing to HEMA

Thank you for your interest in HEMA! This document provides guidelines for contributing.

## Reporting Bugs

If you find a bug:
1. Check if it's already reported in [GitHub Issues](https://github.com/humanbuildingsynergy/HEMA/issues)
2. If not, create a new issue with:
   - Clear title describing the problem
   - Steps to reproduce
   - Expected vs. actual behavior
   - Python/Node version, OS, environment
   - Relevant logs or screenshots

## Contributing Code

Bug fixes, documentation improvements, and new features are welcome via pull requests.

### Development Setup

```bash
# Fork and clone
git clone https://github.com/your-username/HEMA.git
cd HEMA

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API key(s)

# Frontend
cd frontend && npm install
```

### Making Changes

1. Create a branch from `main`:
   ```bash
   git checkout -b fix/your-bug-fix-name
   ```
2. Make your changes
3. Test thoroughly
4. Submit a pull request with a clear description

### Code Style

- **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/), use type hints where applicable
- **JavaScript**: Use consistent formatting with Prettier

### Commit Messages

Write clear, descriptive commit messages:
- `Fix energy data loading for UTC timestamps`
- `Update README installation instructions`

## Extending HEMA

HEMA is designed to be extensible. If you want to add new capabilities:

- **New Agent**: Create tools in `agents/tools/`, agent in `agents/specialized/`, add routing in `agents/graph/`
- **New Tools**: Implement tool function, add to agent's tool list, update system prompt
- **New LLM Provider**: Add to `LLMProvider` enum, implement in `config/llm_factory.py`

You are welcome to fork the repository and build on it under the GPL-3.0 license.

## Security

- Never commit API keys or credentials
- Never include real household data
- Use environment variables for secrets
- If you accidentally commit sensitive data, contact maintainers immediately

## Questions?

- **Bug Reports**: Open a [GitHub Issue](https://github.com/humanbuildingsynergy/HEMA/issues)
- **Questions**: Open a [GitHub Discussion](https://github.com/humanbuildingsynergy/HEMA/discussions)
- **Security Issues**: See [SECURITY.md](SECURITY.md)
- **Maintainer**: Dr. Wooyoung Jung (wooyoung -at- arizona -dot- edu)

---

By contributing, you agree that your contributions will be licensed under the same [GPL-3.0 license](LICENSE) as the project.
