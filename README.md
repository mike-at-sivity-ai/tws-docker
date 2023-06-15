# TWS in Docker

## Getting Started


Create a `.env` file:

```bash
IB_ACCOUNT=<your IB username>
# wrap password in single quotes if $, /, or \ are present
IB_PASSWORD='<your IB password>'
```

`docker-compose.yml`:

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

```bash
docker compose up -d
```

View at [localhost:6080](http://localhost:6080).

TWS API is accessible at port `8888`.
