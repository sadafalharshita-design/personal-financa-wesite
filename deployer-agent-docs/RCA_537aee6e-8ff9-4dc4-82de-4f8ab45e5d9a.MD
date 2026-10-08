# RCA — Wealth (ai-finance-whatif) "preview load failure / blank screen"

## Problem statement
User reports the Emergent **preview** failing to load:
- "[Emergent preview error] Load failure — Failed to load: unknown resource"
- `Failed to load: https://vscode-bd64964f-556e-4fed-aab3-7c232e6d1faf.preview.emergentagent.com/@vite/client`
- `Failed to load: https://vscode-bd64964f-556e-4fed-aab3-7c232e6d1faf.preview.emergentagent.com/src/main.tsx`
- Intended preview URL: `https://ai-finance-whatif.preview.emergentagent.com` (previously worked).

## What the evidence shows
1. **This is a PREVIEW (dev-server) fault, not a production/deployment fault.**
   - `/@vite/client` and `/src/main.tsx` are **Vite dev-server** artifacts. They exist ONLY when the Vite dev server is running in the preview/coding pod; they are never emitted by a production build.
   - They are being requested from a **`vscode-<uuid>` dev-pod host** (`vscode-bd64964f-556e-4fed-aab3-7c232e6d1faf...`), not from the clean preview host. The browser is holding a **stale preview `index.html` that still references a now-dead vscode dev-pod UUID**. When the preview/vscode pod restarts it gets a NEW uuid host; the old uuid no longer resolves to a live dev server, so `/@vite/client` + `/src/main.tsx` 404 → "unknown resource" → blank screen.

2. **Production deployment is LIVE and HEALTHY — ruled out.**
   - `describe_deployment_state`: deployment `active`, latest run `537aee6e-8ff9-4dc4-82de-4f8ab45e5d9a` (type `initial`) `status: success`, frontend_type `kubernetes`, tier_0, cluster-03.
   - `preview_health_check` on `https://ai-finance-whatif.emergent.host/` → **HTTP 200**, 577ms, serving the correct **compiled** bundle `<script type="module" src="/assets/index-B3rOCOcl.js">` with the real `<title>Wealth — Simulate your financial future</title>`. This is a production build (hashed asset), NOT dev-mode — so no stale/raw-TSX issue on the production side.

3. **Ruled out as causes:**
   - **CDN / stale production bundle** — prod serves a correctly hashed built asset and 200s; the failing resources are dev-only files never present in the prod CDN.
   - **Deployment state** — last run succeeded and is the active run; nothing is mid-rollout or failed.
   - **Production routing** — `.emergent.host` resolves and serves the app.
   - The failure is confined to the `.preview.emergentagent.com` / `vscode-<uuid>` **dev** plane.

## Root cause
The browser session at the preview URL is loading a **stale cached `index.html` that points its Vite dev-server module requests (`/@vite/client`, `/src/main.tsx`) at an expired `vscode-<uuid>` dev-pod host**. That old UUID host no longer has a live Vite dev server (preview/vscode pod was recycled → new UUID), so those module loads fail with "unknown resource" and the preview renders blank. This is a **preview-runtime / preview-routing** condition in the dev plane, not a deployment, CDN, or production-config problem.

## Production-side action needed
**None.** The production deployment is live, healthy, and serving the correct built bundle. No redeploy, manifest change, secret, tier, or domain action is warranted — none of these are implicated.

## Fix
- **User:** Hard-refresh / open the preview in an incognito window (and/or clear site data for `*.preview.emergentagent.com`) to drop the cached HTML pinned to the dead `vscode-bd64964f-...` UUID. If it persists, restart the preview/dev environment so the Vite dev server comes back up and the preview URL is re-pointed at the current vscode pod UUID.
- **Platform (Emergent preview plane):** If a fresh/incognito load still requests the dead `vscode-<uuid>` host, the preview proxy is routing `ai-finance-whatif.preview.emergentagent.com` to a recycled dev pod / stale UUID — preview routing needs to re-bind to the live dev pod and the dev (Vite) server restarted. This is outside the deployment pipeline's control.
