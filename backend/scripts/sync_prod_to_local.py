"""Copy the production database down to the local development database.

There is no staging environment: the laptop IS the reproduction environment. This script
is what makes that workable — pull real production data down, run the app locally with
docker-compose.prod.yml, and reproduce the bug against the data that actually caused it.

    python backend/scripts/sync_prod_to_local.py --confirm

Requires the SDC VPN to be connected (192.168.18.194 is a private address) and Docker,
which supplies pg_dump/pg_restore at the right major version via a throwaway container —
the same approach used for the Supabase syncs in HOW_TO_DEMO.md.

DIRECTION IS ONE-WAY, ENFORCED. This script only ever reads from production and only ever
writes to a local database. Pointing it the other way is exactly how a production database
gets destroyed, so the production host is hard-blocked as a target below and there is no
flag to override it — if you ever genuinely need to push local data up, do it by hand and
think about it first.

Two things worth knowing about the copy:

  * The local .env must use the SAME AADHAAR_SECRET_KEY as production. The Aadhaar blind
    index and ciphertext are both derived from it, so a different key makes every synced
    Aadhaar unreadable AND silently breaks duplicate detection. See backend/app/core/aadhaar.py.
  * The copy therefore contains real farmers' personal data. Keep full-disk encryption on,
    do not share the .dump files, and delete old ones rather than letting them pile up.
"""
import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PROD_HOST = "192.168.18.194"
PROD_DB = "sericulture_mis"
PROD_USER = "seri_app"

PG_IMAGE = "postgis/postgis:17-3.4"
BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "db_dumps"

# Anything that resolves to the production database server is refused as a TARGET.
FORBIDDEN_TARGETS = {PROD_HOST, "silkmis.assam.gov.in"}


def fail(msg: str) -> "None":
    print(f"\nERROR: {msg}\n", file=sys.stderr)
    raise SystemExit(1)


def local_target(url: str) -> tuple[str, str, str, str, str]:
    """Parse the local DATABASE_URL and refuse anything that is not local."""
    p = urlparse(url.replace("postgresql+psycopg://", "postgresql://"))
    host, db = p.hostname or "", (p.path or "/").lstrip("/")
    if not host or not db:
        fail(f"could not parse a host and database out of DATABASE_URL: {url!r}")
    if host in FORBIDDEN_TARGETS:
        fail(
            f"refusing to run: the TARGET database is {host}, which is production.\n"
            "       This script only ever copies production -> local, never the reverse."
        )
    if host not in ("localhost", "127.0.0.1", "::1", "host.docker.internal"):
        fail(
            f"refusing to run: target host {host!r} is not local.\n"
            "       Point DATABASE_URL at your local PostgreSQL before syncing."
        )
    return host, str(p.port or 5432), db, p.username or "postgres", p.password or ""


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print("    $ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, **kw)


def main() -> None:
    ap = argparse.ArgumentParser(description="Copy production data down to the local database.")
    ap.add_argument("--confirm", action="store_true", help="required; without it nothing runs")
    ap.add_argument("--keep-dump", action="store_true", help="keep the .dump file afterwards")
    args = ap.parse_args()

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.core.config import settings  # noqa: E402  (needs the path above)

    host, port, db, user, password = local_target(settings.DATABASE_URL)

    print("\n  Production (source, read-only) : "
          f"{PROD_USER}@{PROD_HOST}:5432/{PROD_DB}")
    print(f"  Local (target, WILL BE REPLACED): {user}@{host}:{port}/{db}\n")

    if not args.confirm:
        print("  This DROPS and recreates the local database above. Re-run with --confirm.\n")
        raise SystemExit(1)

    if shutil.which("docker") is None:
        fail("docker not found — it supplies pg_dump/pg_restore at the matching version")

    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump = BACKUP_DIR / f"prod_{stamp}.dump"

    print("\n1/3  Dumping production (read-only; safe to run while it is in use)")
    print("     you will be prompted for the production password")
    run([
        "docker", "run", "--rm", "-it",
        "-v", f"{BACKUP_DIR}:/backup", PG_IMAGE,
        "pg_dump", f"postgresql://{PROD_USER}@{PROD_HOST}:5432/{PROD_DB}",
        "-Fc", "--no-owner", "--no-acl", "-f", f"/backup/{dump.name}",
    ])
    if not dump.exists() or dump.stat().st_size == 0:
        fail("the dump is empty — is the VPN connected and 192.168.18.194 reachable?")
    print(f"     {dump.stat().st_size // 1024} KB -> {dump}")

    print("\n2/3  Recreating the local database")
    env = {"PGPASSWORD": password} if password else {}
    admin = f"postgresql://{user}@{host}:{port}/postgres"
    for sql in (f'DROP DATABASE IF EXISTS "{db}"', f'CREATE DATABASE "{db}"'):
        run(["psql", admin, "-v", "ON_ERROR_STOP=1", "-c", sql], env={**dict(**env)} or None)

    print("\n3/3  Restoring into the local database")
    # PostGIS must live in `public` to match production — the same ordering issue that
    # broke the first Supabase restore (see HOW_TO_DEMO.md).
    run(["psql", f"postgresql://{user}@{host}:{port}/{db}", "-v", "ON_ERROR_STOP=1",
         "-c", "CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public"], env=env or None)
    subprocess.run(
        ["pg_restore", "--no-owner", "--no-acl",
         "-d", f"postgresql://{user}@{host}:{port}/{db}", str(dump)],
        env={**env} if env else None,
    )  # not check=True: a `permission denied for table spatial_ref_sys` notice is expected

    if not args.keep_dump:
        dump.unlink(missing_ok=True)
        print(f"\n     removed {dump.name} (pass --keep-dump to retain it)")

    print("\nDone. Local now mirrors production.")
    print("Reminder: your local .env must use the SAME AADHAAR_SECRET_KEY as production,")
    print("or every synced Aadhaar is unreadable and duplicate detection silently fails.\n")


if __name__ == "__main__":
    main()
