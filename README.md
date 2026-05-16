# TWS in Docker

## Getting Started

### 1. Create a `.env` file

```bash
IB_ACCOUNT=<your IB username>
# wrap password in single quotes if $, /, or \ are present
IB_PASSWORD='<your IB password>'
```

### 2. Generate the nginx credentials file

The web interface is protected by HTTP Basic Auth. Create the `nginx/.htpasswd` file before starting the stack. Run this once and enter your chosen password when prompted:

```bash
mkdir -p nginx
htpasswd -Bc nginx/.htpasswd <username>
```

If `htpasswd` is not installed locally, use Docker instead:

```bash
mkdir -p nginx
docker run --rm httpd:alpine htpasswd -Bn <username> > nginx/.htpasswd
```

The `-B` flag uses bcrypt hashing. You can add multiple users by re-running without the `-c` flag:

```bash
htpasswd -B nginx/.htpasswd <second-username>
```

### 3. Start the stack

```bash
docker compose up -d
```

Access the TWS desktop at [http://localhost:6080](http://localhost:6080). You will be prompted for the username and password set in step 2.

TWS API is accessible at port `8888`.

---

## Architecture

```
Browser → nginx (port 6080, HTTP Basic Auth) → noVNC (port 6081, internal) → Xvnc (port 5900)
```

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| nginx | 6080 | public | Reverse proxy with HTTP Basic Auth |
| noVNC | 6081 | internal only | Web-based VNC client |
| Xvnc | 5900 | internal only | VNC server |
| TWS API | 8888 | public | Interactive Brokers API |

---

## nginx Configuration

The nginx config is at `nginx/nginx.conf`. It proxies all traffic to the noVNC service and handles WebSocket upgrades required by noVNC.

Key settings:

```nginx
auth_basic "TWS Access";
auth_basic_user_file /etc/nginx/.htpasswd;

proxy_pass http://tws:6081;
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 3600s;
```

The `Upgrade` and `Connection` headers are required for the WebSocket connection that noVNC uses. The `proxy_read_timeout` is set to 1 hour to prevent idle VNC sessions from being dropped.

---

## Managing Users

**Add a user:**
```bash
htpasswd -B nginx/.htpasswd <username>
```

**Remove a user:**
```bash
htpasswd -D nginx/.htpasswd <username>
```

**List users:**
```bash
cut -d: -f1 nginx/.htpasswd
```

After changing users, reload nginx without restarting the full stack:

```bash
docker exec tws-nginx nginx -s reload
```

---

## Notes

- `nginx/.htpasswd` is excluded from git — keep a backup of it somewhere safe.
- If you access TWS remotely, put nginx behind a TLS-terminating reverse proxy (e.g. nginx-proxy-manager) to encrypt credentials in transit.
- Port 8888 (TWS API) has no authentication — bind it to localhost only (`127.0.0.1:8888:8888`) if API clients are on the same machine.
