# Security policy

## Reporting

Do not open a public issue for a suspected bypass, race condition, key-spoofing
problem, or denial-of-service vector. Use GitHub's private vulnerability
reporting feature for this repository.

Include the affected version, backend, algorithm, reproduction steps, expected
behavior, observed behavior, and impact.

## Deployment notes

- Use Redis authentication and TLS when Redis crosses a trusted network boundary.
- Do not trust `X-Forwarded-For` unless a controlled reverse proxy overwrites it.
- Choose fail-closed behavior for security-sensitive endpoints such as login and
  password reset.
- Apply independent limits to expensive endpoints, not only a global policy.
- Treat user-provided rate-limit keys as untrusted input and bound their length.
