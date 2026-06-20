# Deploying on Render

This service is a **background worker**, not a web app. Every 30s it:

1. Grabs a frame from the public Ala-Too webcam (`...elcat.kg/.../index.m3u8`),
2. Classifies the 41 parking spots from `spots.json` with `models/best.pt` (YOLO),
3. PUTs each spot's `{available}` to the backend, and
4. (optional) uploads an annotated scheme image to Cloudinary and registers its URL.

It has **no HTTP port and needs no inbound traffic** — only outbound internet.

---

## Cost — read this first

Render's **Hobby workspace is "$0/mo + compute"**: the *plan* is free, but you pay
for each service's **compute**. A **background worker is a paid instance type** —
per Render's docs, *"Background workers don't support Free instances"*
(the free-compute types are only Web Services and Static Sites).

So this deploys on the free Hobby workspace, but the worker itself runs on the
**Starter** instance (~$7/mo compute as of mid-2026 — Render shows the exact price
before you confirm). The free Web Service tier is **not** a usable workaround: it
sleeps after 15 min without inbound traffic (this worker gets none) and is capped
at 512 MB, which PyTorch will likely OOM.

Sources:
- https://render.com/docs/free — *"Background workers don't support Free instances"*
- https://render.com/docs/background-workers
- https://render.com/pricing

---

## Required environment variables

Set these in Render → service → **Environment** (the ones with `sync: false` in
`render.yaml` are intentionally left blank for you to fill). Mirror of `.env.example`;
the `.env` file itself is git-ignored and is NOT used on Render.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `API_KEY` | **Yes** | — | Backend write key. Without it the status PUTs return 401. |
| `BACKEND_BASE` | No | `https://parking-bishkek.onrender.com` | Override only if the backend moves. |
| `LOCATION_ID` | No | `ala-too` | Which location this worker feeds. |
| `PARKING_ID_FORMAT` | No | `spot-{id:02d}` | Must match the spot IDs the backend expects. |
| `CLOUDINARY_CLOUD_NAME` | No* | — | *All three Cloudinary vars are needed together to enable image upload. |
| `CLOUDINARY_API_KEY` | No* | — | If unset, the worker skips the scheme image and still pushes spot statuses. |
| `CLOUDINARY_API_SECRET` | No* | — | |

---

## Deploy steps (Blueprint)

1. **Push this code to a GitHub repo you control.** Render deploys from GitHub, so
   `Dockerfile`, `render.yaml`, `models/best.pt`, and `spots.json` must all be
   committed and pushed. (See "Getting the files to your friend" below.)
2. Render dashboard → **New → Blueprint** → connect the repo/branch.
3. Render reads `render.yaml`, creates the **parking-cv-worker** worker, and shows
   the Starter compute price → confirm.
4. Fill in the blank env vars (`API_KEY`, and Cloudinary keys if wanted) → **Apply**.
5. First build takes a few minutes (PyTorch + Ultralytics are large). There is no
   URL/port — that's expected for a worker.

> Prefer clicking instead of a Blueprint? **New → Background Worker**, connect the
> repo, choose **Docker** as the runtime, pick **Starter**, and add the env vars
> manually. `render.yaml` just automates this.

## Verify it works

Open the worker's **Logs**. A healthy cycle looks like:

```
Loaded 41 spots
Location: https://parking-bishkek.onrender.com/api/locations/ala-too
[HH:MM:SS] Capturing frame...
  → Frame grabbed (1080, 1920, 3), analyzing 41 spots...
  → Pushed 41 spots | Free: 12/41
```

Then confirm the frontend/backend reflects the new statuses. `HTTP 401` → `API_KEY`
is missing/wrong. `Failed to grab frame` → the webcam stream is temporarily down
(the loop retries automatically). If the worker restarts repeatedly right after
boot, suspect an **out-of-memory** on Starter (512 MB) — move it up one instance size.

---

## Notes & gotchas

- **CPU only.** The Dockerfile installs CPU PyTorch on purpose — no GPU needed,
  and it keeps the image far smaller.
- **Always-on.** A worker doesn't scale to zero, so it consumes compute 24/7 —
  that's the ~$7/mo. The cost is for "always running," not the tiny per-cycle work.
- **Single point of failure** is the public webcam URL, not Render.
- The `cv/visualize_*.py`, `cv/roi_tool.py`, and `cv/test_fram.py` scripts are
  local dev/GUI tools and are not used in the container.

---

## Getting the files to your friend

The original clone points at someone else's GitHub repo, so for your friend to
deploy these new files they must live in a repo your friend can connect to Render.

- **Fork it:** fork the repo on GitHub to your account, push this `deploy/render`
  branch (or merge it to `main`), then share that fork — your friend deploys from it.
- **Or** your friend forks and commits these files
  (`Dockerfile`, `.dockerignore`, `render.yaml`, `DEPLOY.md`) into their fork.

Either way, `Dockerfile` and `render.yaml` must be in the deployed repo/branch.
