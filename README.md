# native-ops-conf (Starter Template)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

This is the official **starter template** for managing your fleet with **[`theta42/native-ops`](https://github.com/theta42/native-ops)**.

It provides a complete, declarative GitOps configuration for provisioning cloud hosts (DigitalOcean, Proxmox VE), managing Incus/LXC container workloads, persistent storage volumes, and dynamic Caddy edge reverse proxy routing with wildcard TLS.

---

## 🚀 Quickstart for New Organizations

### 1. Fork or Migrate this Repository
- **On GitHub**: Click **[Use this template](https://github.com/theta42/native-ops-conf/generate)** or **Fork** to create a private `native-ops-conf` repository in your organization.
- **On Gitea / GitLab / Self-Hosted**: Use **Migrate Repository** pointing to `https://github.com/theta42/native-ops-conf.git`.

### 2. Configure Your Git Secret (1 Secret Only!)
In your repository or organization settings (**Settings → Secrets and Variables → Actions**), add:

| Secret Name | Description | Example |
|---|---|---|
| **`DO_API_TOKEN`** | DigitalOcean API Token (Read & Write permissions) | `dop_v1_...` |

*(Note: If no SSH key is provided, `native-ops` will automatically generate a secure in-memory Ed25519 keypair and inject it into your Droplet on first boot).*

### 3. Customize `fleet.yml`
Edit `fleet.yml` to define your domain, cloud provider, and host:

```yaml
name: my-company-fleet
domain: mydomain.com
dns_provider: digitalocean

providers:
  digitalocean:
    region: nyc1
    default_size: s-4vcpu-8gb

hosts:
  node-01:
    provider: digitalocean
    size: s-4vcpu-8gb
    region: nyc1
    address: "auto" # automatically creates droplet & resolves IP
```

### 4. Open a Pull Request & Merge
1. Create a branch and open a Pull Request with your changes.
2. The automated PR check runs `native-ops validate` to check the plan.
3. Merge the PR to `main` — the runner automatically:
   - Provisions your Droplet in DigitalOcean with cloud-init (Incus + UFW).
   - Points `@.mydomain.com` and `*.mydomain.com` DNS records to the new host.
   - Deploys Caddy edge proxy with automatic Let's Encrypt Wildcard TLS certificates.
   - Deploys your declarative services (`services/`).

---

## 📁 Repository Structure

```
.
├── fleet.yml                      # Global fleet, DNS, and host definitions
├── services/                      # Static / persistent cluster services
│   ├── edge/service.yml           # Caddy reverse proxy (ports 80/443)
│   ├── postgres/service.yml       # PostgreSQL 16 with persistent volume
│   ├── redis/service.yml          # Redis 7 cache
│   └── gitea/service.yml          # Self-hosted Git server
├── templates/                     # Blueprints for dynamic tenant instances (SaaS)
│   └── app/template.yml           # App container blueprint
├── providers/
│   └── dns/
│       └── digitalocean.py        # Python DNS plugin
└── .github/workflows/
    └── gitops.yml                 # Automated validation on PR and deployment on merge
```

---

## ⚙️ Service Manifest Reference (`service.yml`)

```yaml
name: postgres
image: docker.io/library/postgres:16-alpine # OCI image or local alias
profiles:
  - base
  - service

volumes:
  - name: postgres-data           # Incus storage volume
    path: /var/lib/postgresql/data # Mount path inside container
    pool: default
    shifted: true                 # security.shifted=true for unprivileged uid mapping

limits:
  limits.cpu: "2"                 # cgroup CPU core limit
  limits.memory: "2GB"            # cgroup memory limit

env:
  POSTGRES_USER: "app_user"
  POSTGRES_DB: "app_db"

healthcheck:
  path: /
  port: 5432
  timeout: 30

routing:                          # Optional Caddy reverse proxy route
  domain: db.mydomain.com
  upstream_port: 5432
```

---

## 🚢 Application CI/CD Deployments

Application repositories (like web apps, APIs, or internal tools) can deploy new versions to this fleet automatically when a git release tag is pushed.

### Tag-Based Release Pattern in App Repositories

In your application's repository (e.g. `my-app`), add `.github/workflows/release.yml`:

```yaml
name: Deploy Release

on:
  push:
    tags: [ 'v*' ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install native-ops
        run: |
          curl -fsSL https://github.com/theta42/native-ops/releases/download/v1.3.0/native-ops_v1.3.0_linux_amd64.tar.gz | tar -xz
          sudo mv native-ops_v1.3.0_linux_amd64 /usr/local/bin/native-ops

      - name: Immutable Update
        env:
          TAG: ${{ github.ref_name }}
          DO_API_TOKEN: ${{ secrets.DO_API_TOKEN }}
        run: |
          native-ops instance update \
            --name my-app \
            --image "my-app:${TAG}" \
            --service my-app
```

**What happens on `git push origin v1.0.0`**:
1. `native-ops` snapshots the app's persistent storage volume (`my-app-data`).
2. Replaces the container from the new `my-app:v1.0.0` image.
3. Re-attaches persistent volumes with `security.shifted=true`.
4. Probes `/health` before confirming zero-downtime success.

---

## License

MIT License. Copyright (c) 2026 theta42.

