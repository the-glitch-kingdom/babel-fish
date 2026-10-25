---
paths:
  - "**/*compose*.{yml,yaml}"
  - "**/Dockerfile*"
  - "**/.dockerignore"
  - "infra/{compose,docker}/**"
---

# babel-fish — Docker Volumes

> Written once by babel-fish; yours to edit.

1. **ALWAYS use a named volume** for anything a container stores or shares (databases, caches,
   uploads, queues), declared under the top-level `volumes:` key: `pgdata:/var/lib/postgresql/data`.
2. **NEVER use an anonymous volume** (`- /var/lib/postgresql/data`): after `docker compose down`
   the next `up` gets a fresh one and the data is orphaned.
3. **A bind mount only when a host path is required**: an entrypoint or init script, host-provided
   config or certs, source for dev live reload, a host socket or device, or output the host reads.
   Comment which case it is; `:ro` unless the container writes. Prefer `COPY` into the image.
4. **Files live under `infra/`** unless `.claude/structure.toml` says otherwise: compose files in
   `infra/compose/`, host files for a container in `infra/docker/<service>/`. Mount paths resolve
   from the compose file: `../docker/db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro`.
5. **NEVER run `docker compose down -v`, `docker volume rm` or `docker volume prune`** without
   explicit permission: they delete the data.
