# Apache Superset 4.1.x + Oracle — Install Guide (Red Hat / Rocky / Alma on VMware)

Repo: [https://github.com/Nassimbhs/superset.git](https://github.com/Nassimbhs/superset.git)  
Branch: `superset-4.1.1`  
Stack: Docker Compose (non-dev) + Oracle Instant Client (`cx_Oracle`)

---

## 0. VM requirements (do this first)


| Resource | Minimum                         | Recommended                   |
| -------- | ------------------------------- | ----------------------------- |
| Disk     | 40 GB                           | **60–80 GB**                  |
| RAM      | 4 GB                            | **8 GB**                      |
| CPU      | 2 cores                         | 2–4 cores                     |
| Browser  | Modern Chrome / Edge / Chromium | **Not** old Firefox (e.g. 68) |


### After resizing the VMware disk

```bash
df -h /
lsblk
sudo dnf install -y cloud-utils-growpart
sudo growpart /dev/nvme0n1 3          # adjust disk/partition if needed
findmnt -no FSTYPE /
# if xfs:
sudo xfs_growfs /
# if ext4:
# sudo resize2fs /dev/nvme0n1p3
df -h /
```

You need **~20 GB free** before building images.

### RHEL subscription (if using RHEL, not Rocky/Alma)

```bash
sudo subscription-manager register --username YOUR_REDHAT_LOGIN
sudo subscription-manager attach --auto
sudo subscription-manager refresh
sudo subscription-manager repos --list-enabled
```

If repos are empty, `dnf install` will fail.

### Browser — install Google Chrome (required on RHEL)

Superset 4.1 UI needs a modern browser. On RHEL, system Firefox is often too old and will show errors like `TypeError: undefined is not a constructor`.

Install Google Chrome:

```bash
cd /tmp
curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
sudo dnf install -y ./google-chrome-stable_current_x86_64.rpm
google-chrome http://localhost:8088
```

Or open from Windows Chrome/Edge: `http://<VM-IP>:8088`

---



## 1. Install Docker

```bash
sudo dnf install -y dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Log out and log in, then:

```bash
docker --version
docker compose version
```

---



## 2. Install Git (if missing)

```bash
sudo dnf install -y git
git --version
```

---



## 3. Clone the repo (Superset 4.1.x)

```bash
cd ~
git clone https://github.com/Nassimbhs/superset.git
cd superset
git checkout superset-4.1.1
```

---



## 4. Add Oracle Instant Client zip

Must sit in the **repo root** (same folder as `docker-compose.oracle.yml`), exact name:

```bash
cd ~/superset

curl -L -o instantclient-basic-linux.x64-23.26.0.0.0.zip \
  "https://download.oracle.com/otn_software/linux/instantclient/2326000/instantclient-basic-linux.x64-23.26.0.0.0.zip"

ls -lh instantclient-basic-linux.x64-23.26.0.0.0.zip
```

Official packages page:  
[https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html](https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html)

---



## 5. Create `docker/.env`

```bash
cd ~/superset
ls docker/.env
```

If missing:

```bash
cat > docker/.env << 'EOF'
COMPOSE_PROJECT_NAME=superset
DATABASE_DB=superset
DATABASE_HOST=db
DATABASE_PASSWORD=superset
DATABASE_USER=superset
EXAMPLES_DB=examples
EXAMPLES_HOST=db
EXAMPLES_USER=examples
EXAMPLES_PASSWORD=examples
EXAMPLES_PORT=5432
DATABASE_PORT=5432
DATABASE_DIALECT=postgresql
POSTGRES_DB=superset
POSTGRES_USER=superset
POSTGRES_PASSWORD=superset
PYTHONPATH=/app/pythonpath:/app/docker/pythonpath_dev
REDIS_HOST=redis
REDIS_PORT=6379
FLASK_DEBUG=false
SUPERSET_ENV=production
SUPERSET_LOAD_EXAMPLES=no
CYPRESS_CONFIG=false
SUPERSET_PORT=8088
MAPBOX_API_KEY=
SUPERSET_SECRET_KEY=CHANGE_ME_TO_A_LONG_RANDOM_SECRET
EOF
```

Change `SUPERSET_SECRET_KEY` for anything beyond a quick test.  
If you restore an old metadata DB later, use the **same** `SUPERSET_SECRET_KEY`.

---



## 6. Optional — French / custom config

File: `docker/pythonpath_dev/superset_config.py`

Example:

```python
BABEL_DEFAULT_LOCALE = "fr"
LANGUAGES = {
    "fr": {"flag": "fr", "name": "French"},
    "en": {"flag": "us", "name": "English"},
}
```

If you changed this only locally and never pushed, copy the file onto the server.

---



## 7. Build and start (Oracle + non-dev)

```bash
cd ~/superset

# free Docker space if a previous build failed
docker system prune -af
docker builder prune -af

docker compose -f docker-compose-non-dev.yml -f docker-compose.oracle.yml up -d --build
```

Watch init:

```bash
docker compose -f docker-compose-non-dev.yml -f docker-compose.oracle.yml logs -f superset-init
```

When init is done:

```bash
docker compose -f docker-compose-non-dev.yml -f docker-compose.oracle.yml ps
```

All main services should be `Up` / `healthy`.

---



## 8. Open Superset

- On the VM: `http://localhost:8088` (**Chrome**, not old Firefox)
- From Windows: `http://<VM-IP>:8088`

Get VM IP:

```bash
ip -4 addr show | grep "inet "
```

Ignore Docker IPs (`172.17.x`, `172.18.x`).

Default login:

- **user:** `admin`
- **password:** `admin`

---



## 9. Connect Oracle 11g

In UI: **Settings → Database connections → + Database**

SQLAlchemy URI examples:

```text
oracle+cx_oracle://USER:PASSWORD@HOST:1521/?service_name=ORCL
```

or with SID:

```text
oracle+cx_oracle://USER:PASSWORD@HOST:1521/SID
```

Test connection, then create datasets / import dashboards.

**Note:** Stay on Superset **4.1.x** with Oracle 11g. Do not upgrade to 5/6 without upgrading Oracle.

---



## 10. Import existing dashboards

