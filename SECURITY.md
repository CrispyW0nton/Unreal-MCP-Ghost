# Security Policy

## Reporting A Vulnerability

Please do not open a public issue for vulnerabilities, leaked secrets, exploit paths, or private project data.

Send a private report to the repository owner through GitHub or another trusted private channel with:

- A short description of the issue.
- Steps to reproduce, if safe to share.
- Affected files, branches, or releases.
- Whether any token, credential, or private project data may be exposed.

## Supported Branch

Security fixes target `main` first. Experimental work belongs on `wip`.

## Secrets And Private Data

Never commit API keys, MCP tunnel credentials, local PDF paths, raw PDFs, Unreal project assets, generated game content, or project-specific knowledge-base folders. Use ignored local files and environment variables instead.
