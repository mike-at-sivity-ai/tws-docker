# TWS in Docker

## Getting Started

### Using `docker run`

```bash
docker run -d \
  -p 6080:6080 \
  -p 8888:8888 \
  --ulimit nofile=10000 \
  -e IB_ACCOUNT=your_username \
  -e IB_PASSWORD=your_password \
  tws:latest
```

### Using `docker compose`

Create a `.env` file:

```bash
IB_ACCOUNT=<your IB username>
# wrap password in single quotes if $, /, or \ are present
IB_PASSWORD='<your IB password>'
```

`compose.yml`:

```yml
version: '3.4'
services:
  tws:
    build: ./tws
    image: tws
    container_name: tws
    restart: unless-stopped
    ports:
      - "6080:6080" # noVNC browser access
      - "8888:8888" # API access
    ulimits:
      nofile: 10000
    environment:
      USERNAME: ${IB_ACCOUNT}
      PASSWORD: ${IB_PASSWORD}
      TWOFA_TIMEOUT_ACTION: restart
      GATEWAY_OR_TWS: tws
      TZ: Pacific/Auckland
```

View at [localhost:6080](http://localhost:6080).

TWS API is accessible at port `8888`.
