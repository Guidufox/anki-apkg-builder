# Security policy

## Supported version

Security fixes are applied to the latest version on the `main` branch.

## Reporting a vulnerability

Do not publish credentials, private cards, browser profiles, or exploitable details in a public issue. Contact the repository owner through their GitHub profile first and provide a minimal description. After a private channel is agreed, share the complete reproduction details.

## Security model

- The application binds to `127.0.0.1` by default.
- Core deck creation does not need Internet access.
- Local AI endpoints are restricted to loopback addresses.
- Browser automation is disabled by default and has an explicit action allowlist.
- Card content is rendered as text and escaped before APKG export.
- User databases, backups, profiles and generated packages are excluded from Git.

This project is designed for local single-user operation. Do not expose the current development server directly to the public Internet.

