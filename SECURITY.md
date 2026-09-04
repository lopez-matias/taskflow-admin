# Security policy

## Supported versions

OrangeFlow is a portfolio project. Security fixes are applied only to the latest revision on the default branch.

## Reporting a vulnerability

Do not publish exploitable details in a public issue. Use GitHub private vulnerability reporting when it is enabled for the repository. Include:

- A concise description of the vulnerability
- Reproduction steps or a minimal proof of concept
- The affected endpoint or component
- Expected impact
- Any suggested mitigation

Reports should receive an initial response within seven days. Timelines may vary because this is not a commercial support channel.

## Known scope limitations

This repository intentionally does not include authentication, authorization, tenant isolation, rate limiting, or production secrets management. It must not be exposed to untrusted networks or used with sensitive organizational data without those controls.

The demo credentials in configuration examples are intended only for isolated local development.
