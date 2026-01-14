# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Do NOT report security vulnerabilities through public GitHub issues.**

Instead, please send an email to: h.jannatabadi@iat.rwth-aachen.de

Include the following information:
- Type of vulnerability
- Full path of the affected file(s)
- Steps to reproduce
- Proof of concept (if available)
- Potential impact

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 1 week
- **Resolution Timeline**: Depends on severity and complexity
- **Credit**: We will credit you in our release notes (unless you prefer to remain anonymous)

### Security Best Practices for Users

When deploying PyEdgeTwin in production:

1. **MQTT Security**
   - Use TLS for MQTT connections
   - Configure username/password or client certificates
   - Set appropriate ACLs on the broker

2. **InfluxDB Security**
   - Use token-based authentication
   - Store tokens in environment variables or secret managers
   - Configure appropriate retention policies

3. **Docker Security**
   - Run containers as non-root users
   - Use read-only file systems where possible
   - Limit container resources
   - Keep images updated

4. **Network Security**
   - Use internal networks for service communication
   - Expose only necessary ports
   - Consider using a reverse proxy with TLS

5. **Configuration Security**
   - Never commit secrets to version control
   - Use `.env` files (excluded from git) or secret managers
   - Validate all configuration inputs

## Security Considerations in Design

PyEdgeTwin incorporates several security considerations:

- **No default credentials**: Configuration must be explicitly provided
- **Environment variable support**: Secrets can be injected via environment
- **Input validation**: Pydantic models validate configuration
- **Graceful degradation**: Connection failures don't expose sensitive data
- **Minimal dependencies**: Reduced attack surface

## Known Limitations

- The default example configurations use anonymous MQTT for simplicity
- Health endpoints do not require authentication by default
- CSV sink writes to local filesystem (ensure proper permissions)

These are intentional trade-offs for development ease and should be addressed in production deployments.
