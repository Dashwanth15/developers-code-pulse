# Application Security Hardening & Threat Model — Developers Code Pulse (DCP)

## 1. Executive Summary & Security Posture

Developers Code Pulse (DCP) adheres to **Defense-in-Depth** and **Least Privilege** security principles. Because DCP handles sensitive repository metadata, webhook deliveries, and AI synthesis, security controls are implemented across authentication, multi-tenant authorization, network boundaries, AI prompt sanitization, and request processing.

---

## 2. Threat Model (STRIDE Methodology)

| Threat Category | Potential Risk in DCP | Implemented Mitigation | Priority |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Forged GitHub webhook events or fraudulent JWT authentication tokens | Timing-safe HMAC-SHA256 signature verification (`hmac.compare_digest`); RS256 / HS256 JWT validation with expiration verification and refresh token family rotation. | **CRITICAL** |
| **Tampering** | Interception or alteration of report artifacts or database state | TLS 1.3 in transit; SQLAlchemy parameterized queries preventing SQL injection; immutable report hashing and checksum validation. | **HIGH** |
| **Repudiation** | Unaudited actions or unauthorized report downloads | Correlation tracking via `X-Request-ID`; structured JSON audit logging capturing timestamps, user UUID, org UUID, and client IP. | **MEDIUM** |
| **Information Disclosure** | Cross-tenant data leakage or leaking credentials in logs/PDFs | Organization-scoped database filters; automatic sensitive data log masking (`mask_sensitive_data_processor`); strict PDF rendering controls; error sanitization. | **CRITICAL** |
| **Denial of Service** | Volumetric HTTP flooding, payload exhaustion, or webhook spikes | Sliding window rate limiting (300 req/min); 15MB request payload size cap (`request_size_limit_middleware`); Celery asynchronous queues. | **HIGH** |
| **Elevation of Privilege** | Tenant user accessing admin capabilities or other organization repos | Role-Based Access Control (`OWNER`, `ADMIN`, `MEMBER`, `VIEWER`); strict repository-to-organization membership validation dependencies. | **CRITICAL** |

---

## 3. Security Implementation Details

### A. Authentication & Session Management
- **Password Storage**: Hashed using `bcrypt` with automatic salt generation and work factor $\ge 12$. Plaintext passwords are never persisted or logged.
- **Access Tokens**: Short-lived (15 minutes default) JSON Web Tokens (JWT) signed with `SECRET_KEY`.
- **Refresh Token Rotation**: Issued in single-use token families. When a refresh token is used, it is revoked and replaced. If a previously revoked token is reused, all tokens in the family are revoked immediately.
- **Client Storage**: Secure token management with automatic header injection and session invalidation on HTTP 401.

### B. Authorization & Multi-Tenant Isolation
- **Organization Boundary**: Every database model (`Commit`, `PullRequest`, `Bottleneck`, `Deployment`, `Report`, `AIInsight`, `ScheduledReport`) includes `organization_id`.
- **Tenant Verification Dependency**: FastAPI routes enforce `get_current_active_user` and `verify_organization_membership`. Cross-tenant queries are blocked at the database engine level.
- **Secure File Downloads**: The `/reports/{id}/download` endpoint authenticates the caller, validates organization ownership, and streams files directly via authenticated token headers.

### C. GitHub Integration Hardening
- **Webhook HMAC Verification**: Every incoming webhook payload is validated against `GITHUB_WEBHOOK_SECRET` using timing-safe comparison:
  ```python
  expected_sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
  if not hmac.compare_digest(expected_sig, signature_header):
      raise DCPException(status_code=401, detail="Invalid webhook signature")
  ```
- **Token Handling**: GitHub tokens are loaded strictly from the environment, stored in memory, and never exposed in client bundles or public endpoints.
- **Rate-Limit Resilience**: GitHub API clients respect `X-RateLimit-Reset` headers and implement exponential backoff.

### D. AI Integration & Prompt Security
- **Untrusted Model Output**: External model outputs from Gemini are treated as untrusted data and parsed strictly against Pydantic schemas.
- **Zero Hallucination Grounding**: Prompts contain strictly numerical aggregates. No proprietary source code, secrets, or individual employee identifiers are passed to external models.
- **API Key Isolation**: `GEMINI_API_KEY` is loaded in backend memory only and never passed to the frontend or embedded in reports.

### E. Application-Level Defenses
- **Enterprise Security Headers**:
  - `Content-Security-Policy`: Disallows unauthorized script injection and frame embedding (`frame-ancestors 'none'`).
  - `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
  - `X-Frame-Options: DENY`: Prevents Clickjacking attacks.
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`: Forces HTTPS.
  - `Referrer-Policy: strict-origin-when-cross-origin`: Minimizes referrer leakage.
- **Payload Size Capping**: Requests exceeding 15MB are rejected immediately with HTTP 413.
- **Rate Limiting**: Monitored via sliding window counters with `X-RateLimit-Limit` and `X-RateLimit-Remaining` response headers.
- **Sanitized Errors**: Unhandled 500 errors return sanitized RFC 7807 responses (`INTERNAL_SERVER_ERROR`), preventing stack trace leakage.

---

## 4. Secret Rotation Procedures

### 1. `SECRET_KEY` (JWT Signing Key)
```bash
# 1. Generate new 32-byte hexadecimal key
NEW_KEY=$(openssl rand -hex 32)

# 2. Update SECRET_KEY in .env
sed -i "s/SECRET_KEY=.*/SECRET_KEY=${NEW_KEY}/" .env

# 3. Gracefully reload API workers
docker compose -f docker-compose.prod.yml restart dcp-api
```
*Note: Rotating `SECRET_KEY` invalidates active access tokens, requiring users to refresh or re-authenticate.*

### 2. Database Password (`POSTGRES_PASSWORD`)
```bash
# 1. Update password in PostgreSQL
docker compose -f docker-compose.prod.yml exec dcp-db psql -U dcp_user -d dcp_db -c "ALTER USER dcp_user WITH PASSWORD 'new_password';"

# 2. Update .env with new_password and recreate services
sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=new_password/" .env
docker compose -f docker-compose.prod.yml up -d dcp-api dcp-worker dcp-beat
```

### 3. Redis Password (`REDIS_PASSWORD`)
```bash
# 1. Issue CONFIG SET requirepass in Redis
docker compose -f docker-compose.prod.yml exec dcp-redis redis-cli -a old_password CONFIG SET requirepass new_password

# 2. Update .env and restart dependent services
sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=new_password/" .env
docker compose -f docker-compose.prod.yml restart dcp-api dcp-worker dcp-beat
```
