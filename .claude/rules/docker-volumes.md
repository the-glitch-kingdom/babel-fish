# babel-fish — Docker Volumes

> Auto-loaded every session. Written once by the babel-fish installer and never overwritten:
> edit it to fit this repo.

## Hard rules

1. **ALWAYS use a named volume** for anything a container stores or shares: databases, caches,
   uploads, queues, build caches. Declare it under the top-level `volumes:` key of the compose file
   and mount it by name (`pgdata:/var/lib/postgresql/data`). Docker manages it, it survives
   `docker compose down`, and it behaves the same on every host.
2. **NEVER use an anonymous volume** (`- /var/lib/postgresql/data` with no name). It gets a random
   ID; after `docker compose down` the next `up` starts with a fresh one, so the data is effectively
   gone and the old volume is left behind as an orphan.
3. **A bind mount (`./host/path:/container/path`) only when functionality requires a host path**:
   - an entrypoint or init script the image runs from a mounted path
     (`./db/init.sql:/docker-entrypoint-initdb.d/init.sql`);
   - a config file or certificate the host provides (`nginx.conf`, TLS certs);
   - source code mounted for live reload in development;
   - a host socket or device (`/var/run/docker.sock`);
   - output the host must read directly.

   Each one carries a one-line comment saying which of these it is, and is `:ro` unless the
   container must write to it. If the file can be built into the image with `COPY` instead, do that.
4. **NEVER run `docker compose down -v`, `docker volume rm` or `docker volume prune`** without
   explicit permission. They delete named volumes, and with them the data.
