# TWS in Docker

## Getting Started

### 1. Create a `.env` file

```bash
IB_ACCOUNT=<your IB username>
# wrap password in single quotes if $, /, or \ are present
IB_PASSWORD='<your IB password>'
AUTHELIA_DOMAIN=tws.upshon.net
```

### 2. Generate Authelia secrets and password hash

Create the secrets directory and generate random keys:

```bash
mkdir -p authelia/secrets
tr -dc 'A-Za-z0-9!@#%^&*' </dev/urandom | head -c 64 > authelia/secrets/jwt_secret
tr -dc 'A-Za-z0-9!@#%^&*' </dev/urandom | head -c 64 > authelia/secrets/session_secret
tr -dc 'A-Za-z0-9!@#%^&*' </dev/urandom | head -c 64 > authelia/secrets/storage_encryption_key
chmod 600 authelia/secrets/*
```

Generate an argon2id password hash for your chosen login password:

```bash
docker run --rm authelia/authelia:latest \
  authelia crypto hash generate argon2 --password 'your-password-here'
```

Copy the output hash into `authelia/users_database.yml`:

```yaml
users:
  mike:
    displayname: "Mike"
    password: "$argon2id$v=19$..."   # paste hash here
    email: mike@localhost
    groups:
      - admins
```

### 3. Start the stack

```bash
docker compose up -d
```

Access the TWS desktop at [https://tws.upshon.net](https://tws.upshon.net). You will be redirected to the Authelia login page. On first login, you will be prompted to register a TOTP device (Google Authenticator or Authy).

TWS API is accessible at port `8888`.

---

## Architecture

```
Browser → nginx-proxy-manager (TLS) → nginx (port 6080) → Authelia (auth check) → noVNC (port 6081, internal) → Xvnc (port 5900)
```

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| nginx | 6080 | public | Reverse proxy with Authelia forward-auth |
| Authelia | 9091 | internal only | Authentication portal (password + TOTP) |
| noVNC | 6081 | internal only | Web-based VNC client |
| Xvnc | 5900 | internal only | VNC server |
| TWS API | 8888 | public | Interactive Brokers API |

---

## Authentication

Access is protected by [Authelia](https://www.authelia.com/) with:

- **Password** — argon2id-hashed, stored in `authelia/users_database.yml`
- **TOTP** — 6-digit time-based code via Google Authenticator or Authy
- **Session expiry** — sessions expire after 8 hours, or 1 hour of inactivity

### Registering a TOTP device

Authelia registers TOTP devices via an identity verification link that it writes to a local file (no SMTP required). If you need to register a new TOTP device or re-register after losing access to your authenticator app, use the Authelia CLI directly — this bypasses the email step entirely:

```bash
ENCRYPTION_KEY=$(sudo cat authelia/secrets/storage_encryption_key)
docker exec tws-authelia authelia storage user totp generate mike \
  --sqlite.path /data/db.sqlite3 \
  --encryption-key "$ENCRYPTION_KEY"
```

This outputs an `otpauth://` URI. To view it as a scannable QR code in the terminal:

```bash
ENCRYPTION_KEY=$(sudo cat authelia/secrets/storage_encryption_key)
docker exec tws-authelia authelia storage user totp generate mike \
  --sqlite.path /data/db.sqlite3 \
  --encryption-key "$ENCRYPTION_KEY" | \
  grep -o 'otpauth://[^ ]*' | xargs qrencode -t UTF8
```

Scan the QR code with your authenticator app. The secret is stored immediately in the database — no further steps needed.

### Reading the notification file

When Authelia sends a notification (password reset link, device registration link), it writes to a local file instead of sending email. Read it with:

```bash
# From the host
sudo cat /var/lib/docker/volumes/tws-docker_authelia_data/_data/notification.txt

# Or from inside the container
docker exec tws-authelia cat /data/notification.txt
```

The file always contains the most recent notification. Copy the link from the file and open it in your browser to complete the flow.

### Changing your password

Update the hash in `authelia/users_database.yml`:

```bash
docker run --rm authelia/authelia:latest \
  authelia crypto hash generate argon2 --password 'new-password'
```

Paste the output into `authelia/users_database.yml`. Authelia hot-reloads this file — no restart needed.

---

## Notes

- `authelia/users_database.yml` and `authelia/secrets/` are excluded from git — keep backups somewhere safe.
- nginx receives HTTP from the TLS-terminating upstream proxy. It trusts the `X-Forwarded-Proto: https` header from that proxy and passes it to Authelia. Do not expose port 6080 directly to the internet without TLS in front.
- Port 8888 (TWS API) has no authentication — bind it to localhost only (`127.0.0.1:8888:8888`) if API clients are on the same machine.
