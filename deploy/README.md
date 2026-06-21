# MoodlePRO server deployment (Oracle Cloud Always-Free)

This is the always-on home for the **server + Redis + Postgres** — the piece the cluster
GPU worker and the browser extension both connect to. It must live off your laptop so the
laptop is only needed to submit/update the cluster job. The stack runs as four containers
(Postgres, Redis, FastAPI server, Caddy HTTPS proxy) via `docker compose`.

```
            Internet
   ┌───────────────┐
   │  :443 (TLS)   │
   ▼               │
 Caddy ──► server ──► postgres
              └────► redis            ◄── cluster GPU worker (HTTPS only, outbound)
```

Caddy terminates HTTPS (auto Let's Encrypt). **443 is the only internet-facing port** for
data — the extension *and* the cluster worker both go through it. Redis and Postgres stay
on the internal Docker network; the worker reaches Redis indirectly via the server's
`/internal` HTTPS endpoints (the BGU cluster blocks all outbound except 80/443, so a direct
Redis connection on 6379 is impossible anyway).

---

## 1. Provision the VM

In the Oracle Cloud console → **Compute → Instances → Create**:

- **Shape:** `VM.Standard.A1.Flex` (Ampere/ARM, Always-Free). 1–2 OCPU and 6–12 GB RAM is
  plenty. (Our images are multi-arch, so ARM is fine.)
- **Image:** Canonical **Ubuntu 22.04**.
- **Networking:** assign a **public IPv4**. Then **reserve** it (Networking → reserved
  public IPs) so it survives a stop/start — otherwise DNS breaks when the IP changes.
- Add your SSH public key.

## 2. Open ports in the VCN security list

Networking → your VCN → Security List → **Ingress rules**, add:

| Port | Source | Why |
| --- | --- | --- |
| 80  | `0.0.0.0/0` | Let's Encrypt HTTP challenge |
| 443 | `0.0.0.0/0` | HTTPS (extension + worker API) |

That's it — **do not open 6379.** The worker talks to the server over HTTPS only, so Redis
never needs to be internet-facing. (If you opened 6379 during an earlier setup, remove that
ingress rule and the matching host-firewall rule — see step 7.)

## 3. DNS

The extension and the cluster worker need a stable name (Let's Encrypt won't issue for a
bare IP). Free option: **DuckDNS** — create a subdomain, point it at the reserved public
IP. Put that name in `.env` as `DOMAIN` / `PUBLIC_BASE_URL`.

## 4. Install Docker + open the host firewall

The default OCI user is `ubuntu` on Ubuntu images and `opc` on Oracle Linux images.
Pick the matching block below. Either way, **both** the VCN security list (step 2) **and**
the host firewall must allow the port, or you'll get "connection refused" despite correct
VCN rules.

### Ubuntu

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### Oracle Linux (8/9)

The `get.docker.com` convenience script rejects Oracle Linux (`ERROR: Unsupported
distribution 'ol'`). Install Docker CE from Docker's CentOS repo instead, and use
`firewalld` (active by default on OL) rather than raw iptables:

```bash
sudo dnf install -y dnf-utils
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER && newgrp docker

# firewalld is active on OL images; netfilter-persistent does NOT exist here.
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

## 5. Deploy

```bash
# Everything lives on `main`. Repo is private — when prompted for a password, paste a
# GitHub Personal Access Token (Settings → Developer settings → PAT).
git clone https://github.com/RoiPrives/MoodlePRO.git ~/MoodlePRO && cd ~/MoodlePRO/deploy
cp .env.example .env
# Generate secrets and edit .env:
openssl rand -hex 32        # use for POSTGRES_PASSWORD, REDIS_PASSWORD, INTERNAL_API_TOKEN
nano .env                   # set DOMAIN, PUBLIC_BASE_URL, the 3 secrets, and a fresh GROQ_API_KEY

docker compose up -d --build
docker compose ps           # all healthy?
docker compose logs -f caddy   # watch the cert get issued
```

## 6. Verify

```bash
curl https://YOUR-DOMAIN/health      # -> {"status":"ok"}
```

Then from the **cluster** (over VPN), run the connectivity probe — this is the gate for the
whole worker path:

```bash
# on slurm.bgu.ac.il, in gpu_worker/cluster/
sbatch --export=ALL,SERVER_URL='https://YOUR-DOMAIN' probe.sbatch
cat moodlepro-probe-*.out
```

You only need **section 3 to print `HTTP OK`** — that proves the cluster can reach the
server over 443, which is the only path the worker uses. (The probe's section 4 Redis check
will fail; ignore it — 6379 is intentionally not exposed.)

## 7. (No Redis to lock down)

Earlier versions exposed Redis on 6379 to the cluster's egress IP. That's no longer needed
or possible — the BGU cluster blocks all outbound except 80/443, and the worker now reaches
Redis indirectly through the server's HTTPS `/internal` endpoints. **If you previously opened
6379, close it again** to keep Redis off the internet:

```bash
# Oracle Linux (firewalld): remove the rich rule you added
sudo firewall-cmd --permanent --remove-rich-rule="rule family=ipv4 source address=<cluster-egress-IP>/32 port port=6379 protocol=tcp accept"
sudo firewall-cmd --reload
```
…and delete the **Ingress 6379** rule from the VCN security list. (Re-deploying with the
updated `docker-compose.yml` also stops publishing 6379 on the host in the first place.)

---

## Security notes

- **Redis is no longer internet-facing** — it lives on the internal Docker network and the
  worker talks to it only via the server's token-authed HTTPS `/internal` endpoints. This
  is the hardening this doc used to defer; the cluster's 80/443-only egress forced (and got)
  the better design.
- `INTERNAL_API_TOKEN` here **must equal** the cluster worker's `~/.moodlepro.env` value.
- `.env` is gitignored — keep it that way. Rotate the Groq key that was shared in chat.
- Postgres and Redis both have **no published port** — only the server container reaches them.

## Connecting the worker

On the cluster, `~/.moodlepro.env` (see `gpu_worker/cluster/README.md`) points back here —
just the HTTPS endpoint and the shared token, no Redis:

```
SERVER_BASE_URL=https://YOUR-DOMAIN
INTERNAL_API_TOKEN=<same as deploy/.env>
```
