# Contributing

Thanks for considering a contribution to Immersion Deck Builder.

## Development setup

Linux:

```bash
./setup.sh
.venv/bin/python -m pytest
```

Windows:

```text
setup.bat
.\.venv\Scripts\python.exe -m pytest
```

The Local AI and Playwright subsystem is optional. Core changes must remain usable without either dependency.

## Pull requests

1. Create a focused branch.
2. Keep the application local-first and offline-capable.
3. Add tests for changed behavior.
4. Run the complete test suite.
5. Explain user-visible changes in the pull request.

Never commit real cards, SQLite databases, browser profiles, credentials, API keys, screenshots containing personal information, or generated `.apkg` files.

## Reporting bugs

Use the repository issue templates. Redact personal Japanese study material and local paths when they are not necessary to understand the problem.

