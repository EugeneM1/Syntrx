# Deploying Syntrx to the web

The cleanest free setup:

| Layer    | Host    | Free tier        | Auto-deploy from GitHub |
|----------|---------|------------------|-------------------------|
| Backend  | Render  | 512 MB / sleeps after 15 min idle | yes |
| Frontend | Vercel  | 100 GB bandwidth | yes |

Total time: about 15 minutes. Both platforms watch your `main` branch and
redeploy whenever you push.

---

## Step 1 — push the latest changes to GitHub

```bash
cd ~/Syntrx/Syntrx
git add .
git commit -m "Configure for Render + Vercel deploys"
git push
```

Wait for the GitHub push to finish before continuing.

---

## Step 2 — deploy the backend on Render

1. Sign in at https://render.com using your GitHub account.
2. Click **New + → Blueprint**.
3. Select your `Syntrx` repository.
4. Render reads `render.yaml` and proposes a service called `syntrx-api`.
   Click **Apply**.
5. Wait ~3 minutes for the first build. When the service shows **Live**,
   copy the URL — it'll look like `https://syntrx-api.onrender.com`.
6. (Optional) In **Settings → Environment**:
   - To enable the real LLM narrator, set `LLM_PROVIDER=anthropic` and
     paste your key into `ANTHROPIC_API_KEY`.
   - Update `CORS_ORIGINS` once you have your Vercel URL (next step).

**Verify it's up:** open `<your-render-url>/api/health` in the browser —
you should see JSON like `{"status":"ok","catalog":{"total":49}, ...}`.

---

## Step 3 — deploy the frontend on Vercel

1. Sign in at https://vercel.com using your GitHub account.
2. Click **Add New… → Project**.
3. Select your `Syntrx` repository.
4. **Important — Root Directory:** click **Edit** and set it to `frontend`.
   Vercel will auto-detect Vite and fill in the rest.
5. Expand **Environment Variables** and add:
   - `VITE_API_URL` = the Render URL from step 2 (e.g. `https://syntrx-api.onrender.com`)
6. Click **Deploy**. Wait ~90 seconds.
7. Copy your Vercel URL (e.g. `https://syntrx.vercel.app`).

---

## Step 4 — point the backend at the Vercel URL

Back in Render → your service → **Environment**:

- Set `CORS_ORIGINS` to your Vercel URL (e.g. `https://syntrx.vercel.app`).
- Save — Render will redeploy automatically.

---

## Step 5 — open it

Visit your Vercel URL. The app loads. Drop a sample file from
`backend/data/sample/` into the upload card. You should see the same report
you saw locally.

The first request after Render's free instance has been idle for 15 min
takes ~30 seconds (cold start). Subsequent requests are fast.

---

## Updating

After step 1 you never need to touch the platforms again. Push to `main`
and both services rebuild within a minute:

```bash
cd ~/Syntrx/Syntrx
git add .
git commit -m "what changed"
git push
```

---

## Custom domain (optional)

Both Vercel and Render support custom domains on their free tier.

- **Vercel:** Project → Settings → Domains → add `syntrx.yourdomain.com`.
  Vercel gives you DNS records to paste at your registrar.
- **Render:** Service → Settings → Custom Domain → same idea.

If you put both on the same root domain (frontend on `syntrx.com`,
backend on `api.syntrx.com`), update Render's `CORS_ORIGINS` accordingly.

---

## Troubleshooting

**Frontend loads but every API call fails / blank report page**
The `VITE_API_URL` env var on Vercel is wrong, or you forgot to redeploy
after setting it. Vercel only injects env vars at build time — go to
**Deployments → ⋯ → Redeploy** after adding/changing them.

**Browser console: `CORS error`**
Render's `CORS_ORIGINS` doesn't include your Vercel URL. The default
also matches `*.vercel.app` via regex, so this usually means you set
the regex to something stricter. Verify in Render → Environment.

**Render shows "Application failed to respond"**
Check **Logs** tab. Most likely cause: the Dockerfile rebuilt but pypdf
or another dep failed to install. Rerun the build.

**First request is slow (~30s)**
Expected on Render's free tier. The instance sleeps after 15 min idle
and cold-starts on the next request. To eliminate, upgrade to the $7/mo
"Starter" plan or use a free uptime pinger like UptimeRobot to ping
`/api/health` every 10 minutes.

**Reports disappear after a Render redeploy**
Render's free tier has an ephemeral filesystem — the JSON report files
in `data/reports/` are wiped on every deploy. For a portfolio demo this
is fine. To persist, attach a Render disk (paid) or migrate the report
store to Postgres (the SQLAlchemy models in `app/db/models.py` are ready;
flip `DATABASE_URL` to a Render-managed Postgres instance).
