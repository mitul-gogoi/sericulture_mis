# How to Run Sericulture MIS for a Demo

You have **two separate copies** of this app you can show people:

|                | Where it runs       | Where the data lives       | Who can see it                 |
| -------------- | ------------------- | -------------------------- | ------------------------------ |
| **Local Demo** | Your laptop         | Your laptop's own database | Only you, on your laptop       |
| **Cloud Demo** | Railway (always on) | Supabase (cloud database)  | Anyone with the link, anywhere |

**The most important thing to understand first:** these are two _completely separate_ databases, like two separate notebooks. Writing something in one notebook does NOT automatically appear in the other. If you add a farmer in the Local Demo, it will NOT show up in the Cloud Demo, and the other way around too. Later in this document (Part 4) there's a way to make them match again, but it doesn't happen automatically.

> **⚠️ UAT data reset — 2026-08-10.** A large batch of feature/schema work (redesigned Yield View, Asset Management GPS workflow, threaded notifications, farmer self-service login, sidebar redesign, and more — see the plan file for the full list) was deployed on this date. Because so much had changed since the previous deploy, the old stakeholder-entered UAT test data on Supabase/Railway was intentionally wiped and replaced with a fresh, fully-featured Kamrup Metropolitan demo dataset rather than forward-migrated. If you're looking for test data you entered before this date, it no longer exists on the live Cloud Demo — a courtesy backup was taken first (`supabase_pre_reset_20260810.dump`, kept outside git) in case anything specific needs to be recovered.

---

## Part 1: Which one do I want to show today?

- Showing someone **in person, on your laptop**, with or without internet? → Go to **Part 2: Local Demo**.
- Sending someone **a link to click from anywhere**? → Go to **Part 3: EC2 Demo**.
- Want both to show the **exact same data**? → Do **Part 4: Syncing** first, then go to Part 2 or 3.

---

## Part 2: Local Demo (on your own laptop)

### Step 1 — Open two PowerShell windows

You need two windows open at the same time — one for the "backend" (the brain) and one for the "frontend" (the screen you see).

### Step 2 — In the FIRST window, start the backend

Copy and paste this, then press Enter:

```powershell
cd "C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS"
& "backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --app-dir backend
```

OR

Go to "Sericulture_MIS" folder and open terminal and type the following command and execute:

```powershell
PS C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS> & "backend\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8001 --app-dir backend
```

Wait until you see a line saying `Application startup complete.` — that means it's ready. **Leave this window open.**

### Step 3 — In the SECOND window, start the frontend

Copy and paste this, then press Enter:

```powershell
cd "C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS\frontend"
yarn dev
```

OR

Go to "frontend" folder and open terminal and type the following command and execute:

```powershell
PS C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS\frontend> yarn build
PS C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS\frontend> yarn start
```

Wait until you see a line saying `Ready` — that means it's ready. **Leave this window open too.**

### Step 4 — Open the app

Open your browser and go to:

```
http://localhost:3000
```

### Step 5 — When you're done

Click into each of the two PowerShell windows and press **Ctrl+C** to stop them. It's fine to just close the windows too.

### If something goes wrong here

- **Page won't load at all** — did you wait for both windows to say "ready"? Check both windows for red error text.
- **"Port already in use" error** — you probably already have it running from before. Just open `http://localhost:3000` directly, no need to start again.
- Anything else weird — come back and tell me exactly what the error text says.

---

## Part 3: Cloud Demo (the live version, hosted on Railway)

### Step 1 — Just try the link

Open your browser and go to:

```
https://frontend-production-6eb5.up.railway.app
```

That's it — unlike the old AWS setup, there's no server to "start" or "stop." Railway keeps it running all the time, so the link should just work whenever you open it.

- **It loads and shows the login page?** ✅ Great, go ahead and demo.
- **It shows an error or won't load?** ❌ Come back and tell me exactly what you see, and I'll check the Railway dashboard (`railway.com`, project "sericulture-mis") for what's wrong.

### Good to know

- The backend API lives at `https://backend-production-526c.up.railway.app` (you won't normally need this directly — the frontend talks to it automatically).
- There's no AWS Console, no EC2 instance, no Elastic IP, no Security Groups to think about anymore — Railway handles all of that.
- The site runs over `https://` (secure padlock), unlike the old `http://18.60.213.161` link.
- The old AWS EC2 instance (`sericulture-mis-uat`) has been stopped (not deleted) and is no longer used for demos — this Railway link is now the one live "internet" demo.

---

## Part 4: Keeping the two databases in sync (optional)

⚠️ **Read this whole warning box before doing anything below.**

Syncing means: "copy everything from one database, and completely erase-and-replace the other database with it." This is a **one-way, all-or-nothing** copy — not a merge. Whichever database you pick as the _target_ gets wiped and replaced. Anything that only exists in the target (and not in the source) will be **permanently lost**. So before syncing, make sure you're OK losing whatever's only in the target side, and make sure nobody else is actively using that target demo at the same moment you're syncing it.

You'll need **Docker Desktop open and running** on your laptop for this (the whale icon in your system tray should be steady, not animating).

### Option A: Copy your Laptop's data UP to Supabase (cloud gets erased and replaces with laptop's data)

Use this when: you've been testing locally and want the EC2 demo to show what's on your laptop.

Open PowerShell and run:

```powershell
cd "C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS"
docker run --rm -v "${PWD}:/backup" postgres:17 pg_dump "postgresql://postgres:postgres@host.docker.internal:5432/sericulture_mis" -Fc --no-owner --no-acl -f /backup/sync_to_supabase.dump
docker run --rm -v "${PWD}:/backup" postgres:17 pg_restore --clean --if-exists --no-owner --no-acl -d "postgresql://postgres.vgsqiqjlbljaaupomvfm:serimisSmart4ever@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres" /backup/sync_to_supabase.dump
```

**What "normal" output looks like:** the first command runs quietly. The second command may print a couple of lines mentioning `spatial_ref_sys` or "permission denied" for that one table — that's expected and harmless (it's a small internal map-related table, not your actual data). Anything mentioning `farmers`, `figs`, `districts`, or `users` failing would be a real problem — stop and tell me if you see that.

### Option B: Copy Supabase's data DOWN to your Laptop (laptop gets erased and replaces with cloud's data)

Use this when: something happened on the live EC2 demo (someone added real data during a demo) and you want your laptop to match it.

Open PowerShell and run:

```powershell
cd "C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS"
docker run --rm -v "${PWD}:/backup" postgres:17 pg_dump "postgresql://postgres.vgsqiqjlbljaaupomvfm:serimisSmart4ever@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres" -Fc --no-owner --no-acl -f /backup/sync_from_supabase.dump
docker run --rm -v "${PWD}:/backup" postgres:17 pg_restore --clean --if-exists --no-owner --no-acl -d "postgresql://postgres:postgres@host.docker.internal:5432/sericulture_mis" /backup/sync_from_supabase.dump
```

Same expected-output notes as Option A apply here.

### After syncing

If your Local Demo (Part 2) is already running in its two PowerShell windows, stop it (Ctrl+C in both) and start it again fresh, so it picks up the new data. The Railway Demo doesn't need a restart — it will just show the new data the next time you refresh the page (Railway's backend reads straight from Supabase on every request, same as the app always has).

---

### FIX BUGS/ENHANCEMENTS (CODE CHANGE), COMMIT and REDEPLOY TO RAILWAY

A) After you've copied Supabase data down to your local PostgreSQL database (Part 4, Option B), fix the bug or make the enhancement locally as normal, then commit and push:

```powershell
cd "C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS"
git commit -m "<Your Message>"
git push origin master
```

B) Redeploy to Railway (the Supabase database is already the one both Local and Railway share, so no separate schema-push step is needed — the backend runs its own `alembic upgrade head` automatically on every startup):

```powershell
cd "C:\Users\Sewa Setu\Documents\MY WORKSPACES\Sericulture_MIS"
railway up backend --path-as-root --service backend --environment production
railway up frontend --path-as-root --service frontend --environment production
```

Then open `https://frontend-production-6eb5.up.railway.app` and log in with your State Admin account (`1111111111` / `sa@123`). If that works and you can see your data, the redeploy is fully live.

## Login details (work on both versions, as long as you haven't synced away the accounts)

Current as of the 2026-08-10 data reset — the fresh Kamrup Metropolitan demo dataset (15 farmers across 3 FIGs).

| Role                                                     | Mobile number | Password       |
| -------------------------------------------------------- | ------------- | -------------- |
| State Admin (Director)                                   | `1111111111`  | `sa@123`       |
| District Admin (Bhaskar Saikia, Kamrup Metropolitan)     | `8123456780`  | `District@123` |
| FIG President (Anil Talukdar, Hatigaon Muga Rearers FIG) | `9854100012`  | `Fig@123`      |
| Farmer (Manoj Sonowal, self-service login)               | `9854100014`  | `farmer@123`   |

---

## Quick summary card

**Demo locally:** open 2 PowerShell windows (backend + frontend commands in Part 2) → go to `localhost:3000`.

**Demo on the internet:** open `https://frontend-production-6eb5.up.railway.app` — always on, nothing to start.

**Make both show the same data:** pick a direction in Part 4, run the two commands, wait for it to finish, then restart whichever demo you're about to show.
