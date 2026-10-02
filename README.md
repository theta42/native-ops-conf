# native-ops-conf (starter template)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

The starter configuration repository for **[theta42/native-ops](https://github.com/theta42/native-ops)**.
Fork it, describe your fleet, and operate it from git.

**How it works.** This repository is the source of truth. CI is the only control path: nobody runs a
control app on their own machine, and after the first bootstrap nobody logs in to a host. Each host
runs the **native-ops daemon**, and CI talks to it over HTTPS with API tokens:

- every pull request is validated and **planned** against the host;
- an admin **approves** the exact plan, in the daemon's web UI;
- the **Apply** workflow runs that plan, and only that plan, as a job with a record.

The daemon holds the host's credentials. CI holds only scoped tokens.

---

## Quickstart

### 1. Fork

- **GitHub:** **Use this template** (or fork) to make a private repository in your organization.
- **Gitea / self-hosted:** **New Migration** from `https://github.com/theta42/native-ops-conf.git`.
  Gitea Actions runs the workflows in `.github/workflows`.

### 2. Describe your fleet

- `fleet.yml`: your fleet's name, domain and host, and uncomment `daemon:`, pinning a native-ops
  release and its SHA-256 from the release's `checksums.txt`.
- `edge/Caddyfile`: your email for Let's Encrypt, and `native-ops.<your domain>`.
- `services/*/service.yml`: the `routing.domain` of each service.
- In every workflow under `.github/workflows`, set `NATIVE_OPS_URL`, `NATIVE_OPS_VERSION` and
  `NATIVE_OPS_SHA256` at the top.

### 3. Bootstrap (once)

Create an environment named **`bootstrap`** (Settings → Environments; on GitHub, add yourself as a
required reviewer) and give it three secrets:

| Secret | What |
|---|---|
| `DO_API_TOKEN` | a DigitalOcean API token (read and write) |
| `SSH_PRIVATE_KEY` | the private key reconcile logs in with; its public half is put on the host |
| `NATIVE_OPS_BOOTSTRAP_TOKEN` | `nops_` followed by 64 random hex characters (`echo nops_$(openssl rand -hex 32)`): the daemon's first admin (also used by the **Secrets** workflow) |

The bootstrap token is an admin credential. Keep it in that protected environment, where a pull
request cannot read it, and never in plain repository secrets.

Run the **Bootstrap** workflow (Actions → Bootstrap → Run). It:

1. creates the host (a droplet) with cloud-init that installs Incus and the native-ops daemon (the
   host gets only the bootstrap token's SHA-256);
2. points `@` and `*` of your domain at it;
3. prepares Incus, then deploys the services and `edge/Caddyfile` directly over SSH. This is the only
   time anything is deployed that way. Afterwards the daemon answers at `https://native-ops.<domain>`.

### 4. Give CI its tokens

Open `https://native-ops.<domain>`, paste the bootstrap token, and go to **Tokens**:

| Create | Store it as the repository secret | Used by |
|---|---|---|
| a `planner` token | `NATIVE_OPS_PLAN_TOKEN` | GitOps (plans every pull request; can do nothing else) |
| a `deployer` token | `NATIVE_OPS_DEPLOY_TOKEN` | Apply, Edge, Release an app, Maintenance |

A deployer token can apply only a plan an admin approved, so a stolen one can at most re-run an
approved plan, once, within the hour.

For people, turn on sign-in instead of sharing tokens: `--enable-auth` (local users, managed over the
API) or the OIDC flags. See the daemon docs.

### 5. Everyday flow

1. Change a manifest in a pull request. **GitOps** prints the plan; its last line is `plan <hash>`.
2. Merge, then an admin approves that plan on the daemon's **Plans** page.
3. Run **Apply** with the hash. The daemon refuses if the host or the tree changed since the plan, so
   what was reviewed is what runs.

Changes to `edge/` are applied by **Edge** on merge. **Maintenance** runs nightly: backups with
retention (once `fleet.yml` has a `backup:` section) and DNS records.

### The daemon's own credentials

Backups, DNS records and OIDC sign-in need credentials on the daemon itself. Nobody logs in to put them
there: enter them in this repository's **`bootstrap` environment** and run the **Secrets** workflow,
which pushes them to the daemon. The daemon keeps them on the host and reads them when it needs them;
values are never shown back, and the daemon's Tokens page lists the names.

| In the `bootstrap` environment | Kind | For |
|---|---|---|
| `DO_API_TOKEN` | secret | DNS records (`dns_records:`), and DNS on the status page |
| `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY` | secret | backups (`backup:`) |
| `NATIVE_OPS_OIDC_CLIENT_SECRET` | secret | OIDC sign-in |
| `BACKUP_ENDPOINT`, `BACKUP_BUCKET` | variable | the only backup destination the daemon will use: the same as in `fleet.yml` |
| `DNS_ZONES` | variable | the zones a DNS sync may change, e.g. `example.com` |

The two pins exist because `fleet.yml` comes in with every upload: without them, anyone holding the
deployer token could send backups elsewhere or change records in any zone the DNS token reaches.
Re-run **Secrets** whenever a value changes; one removed here is removed from the daemon too.

---

## Building your own apps

`images/<app>/build.sh` is an image recipe. `scripts/build-image.sh` runs it on the host in a
throwaway container and publishes `app-<app>:<ref>` and `app-<app>:latest`. The example app `hello`
is a small HTTP service run by systemd, configured from `/etc/default/hello`, which native-ops writes
from the manifest's `env`.

1. Run **Release an app** with `app=hello` and `ref=main`. The first time, it fails with
   `recipe_not_approved`: a build runs the recipe's scripts on the host, so an admin approves the
   recipe once on the daemon's **Recipes** page. Builds of other refs from the same recipe need no new
   approval. Any change to `scripts/` or `images/` is a new recipe. On a fresh host the build makes
   `app-base` first (a few minutes), then the app.
2. Copy `examples/services/hello` to `services/hello` in a pull request, then plan, approve and
   apply. (It is not in `services/` from the start because the bootstrap deploys every service, and
   its image does not exist until it is built.)

An app repository can dispatch **Release an app** on a tag. For per-customer instances, a tenant
system holds a scoped deployer token (names, images, domains) and calls
`PUT /v1/instances/<name>` and `POST /v1/instances/<name>/update` on the daemon.

---

## Repository layout

```
.
├── fleet.yml                  # fleet, DNS, hosts, the daemon release, backups, DNS records
├── edge/Caddyfile             # the edge's global options and hand-written sites (the daemon's route)
├── services/                  # static services: one directory, one service.yml each
│   ├── edge/                  #   Caddy, the only container taking public traffic
│   ├── gitea/                 #   an upstream OCI image with a data volume and a route
│   └── redis/                 #   an OCI image with a volume and no HTTP health check
├── examples/services/hello/   # an app built from images/hello (the native pattern), to copy in
├── templates/app/             # a blueprint for per-tenant instances (instance launch, previews)
├── images/                    # image recipes: base, and one directory per app
├── scripts/                   # build-image.sh (run by the daemon for a build) and its helpers
└── .github/workflows/         # GitOps, Apply, Edge, Release an app, Maintenance, Bootstrap, Secrets
```

---

## `service.yml` reference

```yaml
name: hello                       # the container's name (defaults to the directory)
image: app-hello:latest           # a local image alias, or an image from Docker Hub as docker:<name>
profiles: [base, service]
volumes:
  - name: hello-data              # an Incus custom volume, created if missing
    path: /var/lib/hello          # where it is mounted
    pool: default
    shifted: true                 # security.shifted=true: the container's uids map onto it
    owner: hello                  # optional: hand the mount point to this user in the container
limits:
  limits.cpu: "1"
  limits.memory: "256MB"
env:                              # written to /etc/default/<name> (values never appear in a plan)
  PORT: "8080"
env_file: services/hello/hello.env   # optional, relative to the repository root; env wins over it
healthcheck:                      # an HTTP probe; apply waits for it (omit for non-HTTP services)
  path: /health
  port: 8080
  timeout: 30
routing:                          # publish https://<domain> through the edge
  domain: hello.example.com
  upstream_port: 8080
forwards:                         # raw host ports for protocols the edge cannot carry
  - listen: 2222                  #   on the host
    target: 22                    #   in the container
hooks:                            # optional scripts: a file in the service's directory, or inline
  pre_deploy: pre.sh              #   on the host, before launch
  container_init: init.sh         #   inside the new container, before its service starts
  post_deploy: post.sh            #   on the host, after it is healthy
```

An apply replaces a container rather than patching it: it snapshots the volumes, launches the new
image, reattaches the data, writes the environment and waits for the health check before the route
moves. A plan shows every change first, by key name only.

**Known limit: OCI environment.** An upstream OCI image that reads its configuration from container environment
variables (for example `postgres`, which needs `POSTGRES_PASSWORD`) does not see `env:` yet: native-ops
writes `/etc/default/<name>`, which only a systemd service reads
([native-ops#9](https://github.com/theta42/native-ops/issues/9)). Use images like `hello` for such
apps, or images that work without environment.

---

## More

- [native-ops README](https://github.com/theta42/native-ops#readme): the engine and its commands.
- [docs/daemon.md](https://github.com/theta42/native-ops/blob/main/docs/daemon.md): the daemon's API,
  roles, approvals, tokens, sign-in and maintenance jobs.
- [docs/git-organization.md](https://github.com/theta42/native-ops/blob/main/docs/git-organization.md):
  branch and tag protection, secret scoping, and the staging → production lanes.

## License

MIT License. Copyright (c) 2026 theta42.
