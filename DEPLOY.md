# Deploying Sericulture MIS to the State Data Centre

Step-by-step, for the two Ubuntu VMs allocated by the Assam State Data Centre. Follow it
top to bottom. Anything in a grey box is a command — copy and paste it.

For day-to-day local development instead, see `CLAUDE.md`.

---

## The layout

| | `192.168.18.193` — **App Server** | `192.168.18.194` — **Database Server** |
|---|---|---|
| Runs | frontend + backend + Caddy | PostgreSQL 17 + PostGIS |
| Compose file | `docker-compose.prod.yml` | `docker-compose.db.yml` |
| Public | Yes — 80/443, `silkmis.assam.gov.in` | **No public IP, ever** |
| VPN ports | 22, 80, 443 | 22, 5432 |

```
   https://silkmis.assam.gov.in
              |
        [ .193  Caddy ]
         /           \
   /api/*            everything else
  [ backend ]        [ frontend ]
        |
        |  private network, port 5432
        v
   [ .194  PostgreSQL + PostGIS ]
```

**There is no staging environment.** Your own laptop is the reproduction environment: pull
production data down with `sync_prod_to_local.py` and run the *same* `docker-compose.prod.yml`
stack locally. See Part 10 — that habit is what replaces staging, and it only works if you
use Docker locally rather than `yarn dev`.

---

## Where the database connection is configured

**Not in the code.** The application reads one environment variable, `DATABASE_URL`. Only
three files ever touch it:

| File | What it does |
|---|---|
| `backend/app/core/config.py` | Reads it. The app refuses to start if it is missing. |
| `backend/app/core/db.py` | Uses it to connect while running. |
| `backend/alembic/env.py` | Uses it when applying database migrations. |

The value itself goes in **`backend/.env.docker`** on the App Server, which you create by
hand in Part 7 and which is deliberately not in Git. `backend/.env.example` is the template.

---

## The servers are Rocky Linux 10, not Ubuntu

Confirmed on both VMs: `Rocky Linux 10.2 (Red Quartz)`, `platform:el10`. Parts 3 and 4
below are written for Ubuntu and their commands do not apply. Translation:

| Written (Ubuntu) | Rocky Linux 10 |
|---|---|
| `apt install ...` | `dnf install ...` |
| Docker apt repo | `curl -fsSL https://download.docker.com/linux/centos/docker-ce.repo -o /etc/yum.repos.d/docker-ce.repo` |
| (service auto-starts) | `systemctl enable --now docker` -- the RPM does not start it |
| `ufw allow ...` | `firewall-cmd --permanent --add-port=.../tcp` (firewalld was inactive on both, so nothing was blocking) |
| (no SELinux) | **SELinux Enforcing.** Every *bind* mount needs `:Z`. Named volumes are relabelled automatically; bind mounts are not. |

**Two things that cost time on the first real deployment, both worth knowing in advance:**

1. **Docker will not start until you reboot.** Installing `docker-ce` pulls in a newer
   kernel and installs the netfilter modules for *that* kernel, not the running one.
   `dockerd` then dies with `iptables ... Extension addrtype revision 0 not supported,
   missing kernel module?` because `xt_addrtype` does not exist for the running kernel.
   Reboot into the new kernel and it starts cleanly. Nothing else fixes it.

2. **The SELinux label is not optional and fails in a misleading way.** Without `:Z` on the
   database's `./init` mount, PostgreSQL starts perfectly and reports healthy -- but the
   init script never runs, so the `seri_app` role is never created, and the only symptom is
   an authentication failure from the backend much later. Without `:Z` on the app server's
   `./Caddyfile` mount, Caddy exits saying its config is missing.

---

## Before you start

1. **VPN access** to the SDC network from your Windows laptop.
2. **SSH key** — see Part 1. Password logins will not work for scripted deployment.
3. **The department SSL certificate** for `silkmis.assam.gov.in` (`.crt` and `.key`).
4. Login credentials for both VMs, with `sudo` or root.

---

## Part 1 — SSH keys (do this once, on your laptop)

Everything afterwards runs over SSH, and prompts cannot be answered by automation — so
key authentication is required, not optional.

```bash
ssh-keygen -t ed25519 -C "sericulture-mis-deploy"
```

Copy the public key to both servers. On Windows PowerShell:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh <user>@192.168.18.193 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh <user>@192.168.18.194 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Add both to `~/.ssh/config` so later commands are short:

```
Host seri-app
    HostName 192.168.18.193
    User <your-user>
Host seri-db
    HostName 192.168.18.194
    User <your-user>
```

Confirm both work without a password prompt — this also accepts the host keys, which would
otherwise block automation later:

```bash
ssh seri-app "hostname" && ssh seri-db "hostname"
```

Finally, make `sudo` passwordless for your user (or use root), otherwise scripted installs
will hang waiting for input:

```bash
ssh seri-app "echo '<your-user> ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/deploy"
```

---

## Part 2 — The one test that decides everything

Run on **both** servers:

```bash
ping -c 3 google.com
```

```bash
curl -I https://github.com
```

```bash
curl -I https://registry-1.docker.io
```

- All succeed → **Path A** (Part 3).
- Any fail → ask the SDC whether an HTTP proxy is available. If yes, configure it for both
  `apt` and Docker and use Path A. If not → **Path B** (Part 4).

The third command matters most: PostgreSQL comes from the `postgis/postgis:17-3.4` image on
Docker Hub, and that is what tells you whether the server can fetch it.

---

## Part 3 — PATH A: servers have internet

Do this on **both** servers.

```bash
sudo apt update && sudo apt upgrade -y && sudo apt install -y ca-certificates curl git
```

Install Docker from Docker's own repository (not Ubuntu's older package):

```bash
sudo install -m 0755 -d /etc/apt/keyrings && sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && sudo chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list
```

```bash
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

```bash
sudo usermod -aG docker $USER && sudo docker run hello-world
```

Log out and back in so the group change applies.

Firewall — **App Server**:

```bash
sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
```

Firewall — **Database Server**:

```bash
sudo ufw allow OpenSSH && sudo ufw allow from 192.168.18.193 to any port 5432 proto tcp && sudo ufw enable
```

Get the code onto **both** servers (the database server needs only the compose file, but a
full clone keeps them consistent):

```bash
sudo mkdir -p /opt/sericulture && sudo chown $USER:$USER /opt/sericulture && cd /opt/sericulture && git clone https://github.com/mitul-gogoi/sericulture_mis.git .
```

Now go to **Part 5**.

---

## Part 4 — PATH B: servers have no internet

Everything is prepared on the laptop and carried across.

**On your laptop:**

```bash
docker compose -f docker-compose.prod.yml build
```

```bash
docker pull postgis/postgis:17-3.4 && docker pull caddy:2
```

```bash
docker save seri-backend:latest -o seri-backend.tar && docker save seri-frontend:latest -o seri-frontend.tar && docker save postgis/postgis:17-3.4 -o postgis.tar && docker save caddy:2 -o caddy.tar
```

```bash
git archive --format=tar.gz -o sericulture-code.tar.gz HEAD
```

```bash
scp seri-backend.tar seri-frontend.tar caddy.tar sericulture-code.tar.gz seri-app:/tmp/
```

```bash
scp postgis.tar sericulture-code.tar.gz seri-db:/tmp/
```

Docker itself must also be installed offline. From an internet-connected machine download
these five `.deb` files for your Ubuntu version from
`download.docker.com/linux/ubuntu/dists/<codename>/pool/stable/amd64/` — `containerd.io`,
`docker-ce`, `docker-ce-cli`, `docker-buildx-plugin`, `docker-compose-plugin` — and `scp`
them to both servers.

**On each server:**

```bash
sudo dpkg -i /tmp/*.deb
```

If it complains about dependencies, run `sudo apt install -f` and repeat. Then apply the
same firewall rules as Path A, and:

```bash
sudo mkdir -p /opt/sericulture && sudo chown $USER:$USER /opt/sericulture && cd /opt/sericulture && tar -xzf /tmp/sericulture-code.tar.gz
```

Load the images — on the app server:

```bash
docker load -i /tmp/seri-backend.tar && docker load -i /tmp/seri-frontend.tar && docker load -i /tmp/caddy.tar && docker images
```

On the database server:

```bash
docker load -i /tmp/postgis.tar && docker images
```

On this path, **add `--no-build` to every `docker compose up`**, and shipping an update
means repeating build → save → scp → load. There is no `git pull` shortcut.

---

## Part 5 — Database Server first

The App Server's backend runs database migrations at startup and will fail if PostgreSQL
is not already listening. **Always bring `.194` up first.**

```bash
ssh seri-db
cd /opt/sericulture
```

Create the superuser password file:

```bash
nano .env
```

One line — use a strong password and save it in your password manager:

```
POSTGRES_PASSWORD=<strong-superuser-password>
```

```bash
chmod 600 .env && docker compose -f docker-compose.db.yml up -d
```

```bash
docker compose -f docker-compose.db.yml logs --tail=20 db
```

Wait for `database system is ready to accept connections`.

### Create the application role

The app connects as a normal user, not the superuser:

```bash
docker exec -it seri-db psql -U postgres -d sericulture_mis
```

At the `psql` prompt (use a different password from the superuser one):

```sql
CREATE ROLE seri_app LOGIN PASSWORD '<strong-app-password>';
GRANT ALL PRIVILEGES ON DATABASE sericulture_mis TO seri_app;
GRANT ALL ON SCHEMA public TO seri_app;
\q
```

### Confirm it is bound correctly

```bash
sudo ss -lntp | grep 5432
```

It must show `192.168.18.194:5432` — **not** `0.0.0.0:5432`. If it shows `0.0.0.0`, the
port mapping in `docker-compose.db.yml` was changed and the database is exposed on every
interface the VM has. Fix it before continuing.

---

## Part 6 — App Server: certificate

**Which bundle.** The Directorate's certificate arrives as three zips. Use the **Apache**
one: it holds the leaf and the CA bundle as PEM, which is what Caddy reads. IIS ships a
binary `.p7b`; Tomcat splits the chain across extra files for no benefit.

Build the file Caddy wants — leaf **first**, then the chain:

```bash
cat dcf14be23a0d700a.crt gd_bundle-g2.crt > certs/certificate.crt
```

Serving the leaf alone is the classic mistake: desktop browsers often paper over a missing
intermediate from cache, while Android rejects it outright. Confirm three certificates:

```bash
grep -c "BEGIN CERTIFICATE" certs/certificate.crt
```

**Strip the byte-order mark from the private key.** The key arrives as
`generated-private-key.txt` and begins with a UTF-8 BOM (`ef bb bf`). OpenSSL tolerates it,
so every local check passes — but Caddy uses Go's PEM decoder, which requires the file to
*start* with `-----BEGIN`, and fails with `tls: failed to find any PEM data in key input`,
restart-looping. This cost real time on the first install and will recur at renewal:

```bash
sed -i '1s/^ï»¿//' certs/private.key
head -c 3 certs/private.key | od -An -tx1     # must NOT be ef bb bf
chmod 600 certs/private.key
```

**Check the key actually matches the certificate** before restarting anything — a mismatch
is the other common way a cutover fails, and this takes two seconds:

```bash
diff <(openssl x509 -noout -pubkey -in certs/certificate.crt)      <(openssl pkey  -pubout     -in certs/private.key) && echo "key matches cert"
```

**The certificate is a wildcard for all of `assam.gov.in`**, not just this app — treat the
key accordingly: `chmod 600`, never in git, never emailed, and delete stray copies once
installed. It expires **21 Nov 2026** and does not auto-renew; diarise late October.

**DNS is a separate, blocking step.** The certificate can be fully installed and proven
before the domain resolves, because SNI is sent independently of DNS:

```bash
echo | openssl s_client -connect <public-ip>:443 -servername silkmis.assam.gov.in
```

`Verify return code: 0 (ok)` means TLS is correct and only the A record is missing. That
record — `silkmis.assam.gov.in A <public-ip>` — must be created by whoever administers the
`assam.gov.in` zone; it cannot be done from these servers.



```bash
ssh seri-app
cd /opt/sericulture
mkdir -p certs
```

Copy the certificate files up from your laptop, then:

```bash
mv /tmp/certificate.crt certs/certificate.crt && mv /tmp/private.key certs/private.key && chmod 600 certs/private.key
```

> If the department gave you **two** certificate files — a server certificate and an
> intermediate/CA one — join them or browsers will show a trust warning:
>
> ```bash
> cat server.crt intermediate.crt > certs/certificate.crt
> ```

The domain in `Caddyfile` is already set to `silkmis.assam.gov.in`. Only edit it if that
changes.

---

## Part 7 — App Server: secrets

Generate three secrets. Run this three times and save each result in your password manager
**before** going further:

```bash
openssl rand -hex 32
```

```bash
nano backend/.env.docker
```

Paste this in, substituting your real values:

```
DATABASE_URL=postgresql+psycopg://seri_app:<app-password>@192.168.18.194:5432/sericulture_mis
CORS_ORIGINS=https://silkmis.assam.gov.in
JWT_SECRET=<first openssl result>
JWT_REFRESH_SECRET=<second openssl result>
AADHAAR_SECRET_KEY=<third openssl result>
ACCESS_TOKEN_MINUTES=30
REFRESH_TOKEN_DAYS=7
APP_NAME=sericulture-mis
RATE_LIMIT_LOGIN=5/minute
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
UPLOAD_ROOT=/data/uploads
```

```bash
chmod 600 backend/.env.docker
```

> **`AADHAAR_SECRET_KEY` can never be changed or lost.** It both encrypts farmers' Aadhaar
> numbers and derives the index used to detect duplicates. Lose it and every stored Aadhaar
> becomes permanently unreadable *and* duplicate checking silently stops working. Back it up
> now, in a password manager, not in a file on the server.
>
> You will also need this exact value in your **local** `.env` for the production→local
> sync to be readable (Part 10).

### Check the connection before starting anything

```bash
nc -zv 192.168.18.194 5432
```

If this fails, the app-to-database firewall rule was not granted. **Stop and resolve it with
the SDC** — nothing past this point can work.

---

## Part 8 — Start the application

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

(Add `--no-build` if you are on Path B.)

```bash
docker compose -f docker-compose.prod.yml logs --tail=40 backend
```

Wait for `Startup complete — Alembic upgraded and DB seeded.` The first start creates all
50 tables automatically and seeds the master data it can generate itself: 35 districts,
87 sericulture circles, 4 silk types, 16 asset types, castes and religions.

It does **not** seed everything. `activities`, `products`, `silk_type_activity_products`,
`conversion_standards`, `subdivision_cdc_offices` and `users` are all still empty at this
point — so nobody can log in yet, and no yield can be recorded. Part 9 fixes that and is
**not optional**.

```bash
curl -k https://localhost/api
```

Expect `{"app":"Sericulture MIS API","status":"ok","version":"2.0"}`.

---

## Part 9 — Load the remaining master data, and create the first login

**Required. The application is not usable until both halves of this part are done.**

Part 8 left `activities`, `products`, the activity-to-product map, `conversion_standards`
and `subdivision_cdc_offices` empty, and there is no user account at all. Verified against
a genuinely fresh database, not assumed.

### 9a — Restore the master-data dump

Produce `masters_only.dump` on your laptop first (see "Preparing the dump" below), then:

```bash
scp masters_only.dump seri-db:/tmp/
```

```bash
ssh seri-db "docker cp /tmp/masters_only.dump seri-db:/tmp/ && docker exec -i seri-db pg_restore -U postgres -d sericulture_mis --no-owner --no-acl /tmp/masters_only.dump"
```

A warning about `spatial_ref_sys` is normal — that is PostGIS's own internal table. Any
other error naming a table is real; stop and investigate.

Check it landed:

```bash
ssh seri-db "docker exec -it seri-db psql -U postgres -d sericulture_mis -c 'SELECT (SELECT count(*) FROM districts) AS districts, (SELECT count(*) FROM sericulture_circles) AS circles, (SELECT count(*) FROM products) AS products, (SELECT count(*) FROM farmers) AS farmers;'"
```

Expect `districts=35`, `circles=87`, `products=26`, `farmers=0`. If `products` is still 0,
the restore did not take — do not continue.

### 9b — Confirm the State Admin login

You do not need a separate step for this: `reset_all_except_masters.py` creates one State
Admin as part of producing the dump, so the account arrives with the restore.

```bash
ssh seri-db "docker exec -it seri-db psql -U postgres -d sericulture_mis -c \\"SELECT mobile_no, name, role FROM users;\\""
```

Exactly one row, role `STATE_ADMIN`. Log in as it and change the password immediately
(Part 12) — the value baked into the script is a development default and must not survive
into production.

### Preparing the dump (on your laptop, before Part 9a)

**First, change the admin password the dump will carry.** `backend/scripts/reset_all_except_masters.py`
line 25 reads:

```python
NEW_ADMIN = {"name": "Director", "mobile_no": "1111111111", "password": "sa@123"}
```

Set a real mobile number and a strong password before running it. That value becomes the
live State Admin login on a government server.

Never run the wipe against your working database. Copy it first:

```bash
createdb -U postgres seri_export && pg_dump -U postgres -Fc sericulture_mis -f full_local.dump && pg_restore -U postgres -d seri_export --no-owner --no-acl full_local.dump
```

```bash
cd backend && DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/seri_export .venv/Scripts/python scripts/reset_all_except_masters.py --confirm
```

```bash
pg_dump -U postgres -Fc seri_export -f masters_only.dump
```

Before shipping it, confirm the copy is right: 35 districts, 87 circles, 15 activities,
26 products, 20 conversion standards, **1 user** (the State Admin the script just created)
and **0 farmers, 0 FIGs**.

---

## Part 10 — Working without a staging environment

There is no staging server. Your laptop takes its place, and that only works if you follow
two rules.

**Rule 1 — reproduce with Docker, not `yarn dev`.** Pull production data down:

```bash
python backend/scripts/sync_prod_to_local.py --confirm
```

(Requires the VPN. It only ever copies production → local; it refuses outright if pointed
the other way.) Then run the *same* stack you run in production:

```bash
docker compose -f docker-compose.prod.yml up --build
```

`yarn dev` has no Caddy, no reverse proxy, no container networking and no TLS. Bugs caused
by any of those — and in this project that has been most of them — will not appear.

**Rule 2 — test migrations locally before deploying them.** The backend runs
`alembic upgrade head` automatically at startup. Rolling the code back does **not** roll a
migration back. So for any change that adds a file under `backend/alembic/versions/`:
sync production data down, run the migration locally, confirm it works, and only then
deploy. `deploy.sh` will stop and ask you to confirm you have done this.

Your local `.env` must use the **same `AADHAAR_SECRET_KEY`** as production, or every synced
Aadhaar is unreadable. That also means your laptop holds real citizen data — keep full-disk
encryption on and delete old dumps rather than letting them accumulate.

---

## Part 11 — Deploying an update

Once, after the first clone, make the script executable:

```bash
chmod +x /opt/sericulture/deploy.sh
```

Then, from `/opt/sericulture` on the App Server:

```bash
./deploy.sh
```

It backs up the database, tags the running images as `:previous`, pulls, rebuilds, and waits
for the API to answer. If the change contains a migration it stops and asks you to confirm
you tested it locally first.

If a deploy goes wrong:

```bash
./deploy.sh --rollback
```

That re-tags the previous images and restarts — under a minute, no rebuild, no internet
needed. **If the failed deploy included a migration, also restore the pre-deploy dump**
from `~/backups/` — a code rollback cannot undo a schema change.

Rehearse this once, deliberately, before you need it.

---

## Part 12 — Verify

- `docker compose -f docker-compose.prod.yml ps` on `.193` — all three services `Up`.
- `docker compose -f docker-compose.db.yml ps` on `.194` — `seri-db` `Up` and healthy.
- `https://silkmis.assam.gov.in` loads with a padlock and no certificate warning.
- Log in as the State Admin created in Part 9b, and **change the password immediately**.
- Open Master Data → Map Activity to Product and confirm the Eri/Muga/Mulberry chain is
  populated. If it is empty, Part 9a did not run and no yield can be recorded.
- Register one real farmer and upload a photo, proving file storage works.
- Type a wrong password six times, then log in correctly — it must work. There is no
  account lockout in this system by design.
- From two different machines, log in within the same minute — both must succeed. If the
  second is blocked, the proxy-header configuration did not take effect.
- pgAdmin 4 connects to `192.168.18.194:5432` over the VPN and lists the tables.
- From a machine **not** on the VPN, confirm `192.168.18.194:5432` is unreachable.
- Reboot both VMs, wait two minutes, confirm everything returns on its own.

---

## Finding logs

With no staging environment, server logs are your main evidence when something is reported.
Two places to look:

**Live — the current containers:**

```bash
ssh seri-app "cd /opt/sericulture && docker compose -f docker-compose.prod.yml logs --timestamps --tail=200 backend"
```

**History — archived at each deploy:**

```bash
ssh seri-app "ls -lh ~/logs/"
```

```bash
ssh seri-app "grep -i error ~/logs/predeploy_2026-08-21_143000.log"
```

Why the archive exists: Docker stores a container's logs **with the container**, and deploying
recreates containers — so without archiving, every deploy would erase all evidence of what the
previous version did. `deploy.sh` dumps the full log to `~/logs/predeploy_<timestamp>.log`
immediately before rebuilding.

Each service is capped at 10 MB × 5 files, so logs cannot fill the disk (which on this server
also holds the uploads volume).

> **Do not run `docker compose down`.** It destroys containers *and* their logs with no archive.
> `deploy.sh` deliberately never calls it — use `restart` if you need to bounce a service:
>
> ```bash
> ssh seri-app "cd /opt/sericulture && docker compose -f docker-compose.prod.yml restart backend"
> ```

Two gaps to be aware of, deferred deliberately: there is **no error tracking** (a 500 produces a
log line, not an alert with request context), and **no automated tests or CI**. Neither is built.
If diagnosing production becomes routine, error tracking is the higher-value of the two.

---

## Day-to-day

```bash
ssh seri-app "cd /opt/sericulture && docker compose -f docker-compose.prod.yml ps"
```

```bash
ssh seri-app "cd /opt/sericulture && docker compose -f docker-compose.prod.yml logs -f backend"
```

```bash
ssh seri-db "docker exec seri-db pg_dump -U postgres -Fc sericulture_mis" > ~/backups/seri_$(date +%F).dump
```

Schedule that backup, and keep copies **off** the server. A backup that only exists on the
machine it protects is not a backup.

---

## Things to know

- **The certificate expires.** A department-issued certificate does not renew itself. Put
  the expiry date in a calendar with a reminder a month before — the site goes down with a
  browser security warning the day it lapses.
- **There is no account lockout.** Wrong passwords never lock anyone out; guessing is
  limited to 5 attempts per minute per computer. Password strength matters accordingly.
- **Every deploy is a production deploy.** There is no staging. Part 10 and `deploy.sh` are
  what stand in for it.
- **`192.168.18.194` must never be given a public IP.**
- **The scripts in `backend/scripts/` are dangerous.** Several delete data and most do not
  check which database they are pointed at. `sync_prod_to_local.py` is the exception — it
  refuses to write to production. Do not assume the others do.
- **Uploaded files live in a Docker volume** on the app server, not in the database. They
  are not covered by `pg_dump`; back up the `backend_uploads` volume separately.
