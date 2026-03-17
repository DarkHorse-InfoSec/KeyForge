# KeyForge - Universal API Infrastructure Assistant

<div align="center">
  <img src="https://customer-assets.emergentagent.com/job_apiforge-2/artifacts/r0co6pp1_1000006696-removebg-preview.png" alt="KeyForge Logo" width="100" height="100">

  **Securely manage, validate, and monitor all your API credentials in one place.**

  [![React](https://img.shields.io/badge/React-19.0.0-blue?logo=react)](https://reactjs.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.110.1-green?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![MongoDB](https://img.shields.io/badge/MongoDB-7.0-green?logo=mongodb)](https://www.mongodb.com/)
  [![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org/)
</div>

## Overview

KeyForge is a full-stack API credential management platform. It scans codebases to detect API usage, stores keys with envelope encryption, enforces rotation and expiration policies, and provides compliance reporting, all behind JWT authentication with MFA support.

## Features

### Credential Management
- **Encrypted storage** - Two-level Fernet envelope encryption (per-user data keys wrapped by master key)
- **27+ provider validators** - Format checks and live validation for OpenAI, Stripe, GitHub, AWS, GCP, Azure, Twilio, SendGrid, and more
- **Version history** - Full credential versioning with rollback capability
- **Import/export** - .env and JSON format support

### Security
- **MFA/TOTP** - Time-based one-time passwords with backup codes
- **IP allowlisting** - CIDR-aware access control
- **Session management** - Active session tracking, selective revocation
- **KMS integration** - Pluggable key management (Local, AWS KMS, HashiCorp Vault Transit)
- **Credential proxying** - Short-lived tokens that proxy API requests without exposing real keys
- **Secret scanning** - Detect hardcoded credentials in source code with 42 patterns
- **Breach detection** - Pattern heuristics and cross-user hash comparison
- **NoSQL injection & XSS protection** - Request body sanitization middleware

### Operations
- **Key rotation** - Policy-based rotation tracking with auto-rotation for AWS, GitHub, Stripe
- **Expiration enforcement** - Configurable policies (warn, block, grace period)
- **Health checks** - Scheduled and manual credential validation
- **Tamper-proof audit logs** - SHA-256 hash-chained audit entries
- **Encrypted backups** - Gzip-compressed, Fernet-encrypted, with checksum verification

### Analytics & Compliance
- **Usage analytics** - Track credential access patterns, detect idle credentials
- **Compliance scoring** - 0-100 scoring across SOC2, GDPR, and general frameworks
- **Lifecycle tracking** - Full credential lifecycle event timeline
- **Prometheus metrics** - `/api/metrics/prometheus` endpoint for monitoring

### Team Collaboration
- **Teams with RBAC** - Owner, admin, member, viewer roles
- **Per-credential permissions** - Read, use, manage, admin granularity
- **Credential groups** - Organize credentials into logical groups
- **Webhooks** - Event notifications for credential changes

### Developer Tools
- **Python SDK** - `KeyForgeClient` class with 13 methods
- **CLI** - `keyforge` command-line tool (login, pull, push, list, scan)
- **VS Code extension** - List, pull, scan, and test credentials from the editor
- **Terraform provider** - Resource and data sources for infrastructure-as-code
- **Kubernetes operator** - Sync credentials to K8s Secrets via CRD
- **Git pre-commit hook** - Scan staged files for secrets before commit
- **Docker integration** - Inject credentials into containers
- **GitHub App** - Detect committed secrets via push webhook

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB 7.0+

### Installation

```bash
git clone https://github.com/HackingPain/KeyForge.git
cd KeyForge
```

**Backend:**
```bash
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend && npm install
```

### Environment Variables

```env
# Required
MONGO_URL=mongodb://localhost:27017
DB_NAME=keyforge_database
ENCRYPTION_KEY=<fernet-key>        # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
JWT_SECRET=<random-secret>

# Optional: KMS provider (default: local)
KMS_PROVIDER=local                 # local | aws | vault
AWS_KMS_KEY_ID=<key-id>            # if using aws
VAULT_ADDR=https://vault:8200      # if using vault
VAULT_TOKEN=<token>                # if using vault
```

### Run

```bash
# Backend
uvicorn backend.server:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend && npm start
```

### Docker

```bash
docker-compose up
```

This starts MongoDB, the backend (port 8001), and the frontend (port 3000).

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌───────────┐
│   Frontend   │     │     Backend      │     │  MongoDB  │
│   (React)    │────>│    (FastAPI)     │────>│           │
│  Port 3000   │     │    Port 8001    │     │ Port 27017│
└──────────────┘     └──────────────────┘     └───────────┘
                            │
                     ┌──────┴──────┐
                     │  Middleware  │
                     ├─────────────┤
                     │ Rate Limiter│
                     │ Sanitizer   │
                     │ Monitoring  │
                     │ Error Handler│
                     │ CORS        │
                     └─────────────┘
```

### Directory Structure

```
KeyForge/
├── backend/
│   ├── server.py                  # FastAPI app (v5.0, 32 routers)
│   ├── config.py                  # DB connection, encryption setup
│   ├── security.py                # JWT auth, password hashing
│   ├── models.py                  # Core Pydantic models
│   ├── models_security.py         # MFA, IP, session models
│   ├── models_lifecycle.py        # Expiration, versioning, rotation models
│   ├── models_analytics.py        # Breach, usage, compliance models
│   ├── models_envelope.py         # Envelope encryption models
│   ├── models_kms.py              # KMS provider models
│   ├── models_proxy.py            # Credential proxy models
│   ├── models_backup.py           # Backup/restore models
│   ├── models_policy.py           # Expiration policy models
│   ├── models_audit.py            # Audit integrity models
│   ├── models_field_encryption.py # Field encryption models
│   ├── validators.py              # 27 provider validators
│   ├── scanners.py                # Secret scanning engine
│   ├── routes/                    # 32 API route modules
│   ├── encryption/                # Envelope encryption, KMS, field encryption
│   ├── middleware/                 # Rate limiter, sanitizer, monitoring, errors
│   ├── audit/                     # Tamper-proof audit chain
│   ├── backup/                    # Encrypted backup manager
│   ├── proxy/                     # Credential proxy with short-lived tokens
│   ├── policies/                  # Expiration enforcement
│   ├── utils/                     # Pagination, API docs
│   └── migrations/                # Versioned DB migrations
├── frontend/
│   ├── src/
│   │   ├── App.js                 # Main app with sidebar nav, dark mode
│   │   └── components/            # 22 React components
│   └── src/__tests__/             # Jest + RTL component tests
├── tests/                         # 314 backend unit + integration tests
├── e2e/                           # Playwright E2E tests
├── tools/
│   ├── cli.py                     # CLI tool
│   ├── sdk/                       # Python SDK
│   ├── docker_integration.py      # Docker credential injection
│   ├── github_app.py              # GitHub webhook handler
│   └── vscode_extension/          # VS Code extension
├── integrations/
│   ├── terraform/                 # Terraform provider (Go)
│   ├── kubernetes/                # K8s operator (kopf)
│   └── git-hooks/                 # Pre-commit hook package
├── .github/workflows/             # CI/CD (lint, test, build, deploy)
├── docker-compose.yml             # MongoDB + backend + frontend
├── Dockerfile.backend
├── Dockerfile.frontend
└── requirements.txt
```

## API Reference

The API serves 32 route groups on `/api/*`. Full interactive docs at `/docs` when running.

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |
| GET | `/api/credentials` | List credentials |
| POST | `/api/credentials` | Store new credential (encrypted) |
| POST | `/api/credentials/{id}/test` | Validate credential |
| POST | `/api/projects/analyze` | Analyze codebase for API usage |
| GET | `/api/dashboard/overview` | Dashboard stats |

### Security
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/mfa/setup` | Enable TOTP MFA |
| POST | `/api/ip-allowlist` | Add allowed IP/CIDR |
| GET | `/api/sessions` | List active sessions |
| POST | `/api/encryption/envelope/keys/rotate-user` | Rotate user's data key |
| GET | `/api/kms/status` | KMS provider status |
| POST | `/api/proxy/tokens` | Create short-lived proxy token |
| POST | `/api/proxy/request` | Execute proxied API request |

### Lifecycle
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/expiration` | Set credential expiration |
| GET | `/api/policies/expiration/violations` | Policy violations |
| GET | `/api/versioning/{id}/versions` | Version history |
| POST | `/api/versioning/{id}/rollback` | Rollback to version |
| POST | `/api/auto-rotation/config` | Configure auto-rotation |

### Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/audit/integrity/verify` | Verify audit chain |
| POST | `/api/backup/create` | Create encrypted backup |
| POST | `/api/backup/restore/{id}` | Restore from backup |
| POST | `/api/encryption/fields/encrypt-collection` | Encrypt collection fields |
| GET | `/api/metrics/prometheus` | Prometheus metrics |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/breach-detection/check/{id}` | Check for breach indicators |
| GET | `/api/usage-analytics/dashboard` | Usage dashboard |
| POST | `/api/compliance/reports/generate` | Generate compliance report |
| GET | `/api/compliance/score` | Compliance score (0-100) |

All authenticated endpoints require `Authorization: Bearer <jwt-token>`.

## Testing

```bash
# Backend unit + integration tests (314 tests)
cd tests && pytest

# Frontend component tests
cd frontend && npm test

# E2E tests
cd e2e && npx playwright test
```

## Deployment

### Docker Compose (recommended)

```bash
docker-compose up -d
```

### GitHub Actions CI/CD

The `.github/workflows/ci.yml` pipeline runs:
1. Backend linting (black, isort, flake8)
2. Backend tests (pytest with MongoDB service)
3. Frontend build
4. Frontend tests (Jest + React Testing Library)
5. Frontend linting (ESLint)
6. Security scan (bandit, safety)

Tag-based deployment via `.github/workflows/deploy.yml`.

### Integrations

**Terraform:**
```hcl
provider "keyforge" {
  host  = "https://keyforge.example.com"
  token = var.keyforge_token
}

data "keyforge_credential" "stripe" {
  api_name = "stripe"
}
```

**Kubernetes:**
```yaml
apiVersion: keyforge.io/v1alpha1
kind: KeyForgeSecret
spec:
  credentialIds: ["cred-123"]
  secretName: my-api-keys
```

**Pre-commit:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/HackingPain/KeyForge
    hooks:
      - id: keyforge-scan
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add my feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

<div align="center">
  <strong>Built by the KeyForge Team</strong>
  <br>
  <em>Making API credential management secure and simple</em>
</div>
