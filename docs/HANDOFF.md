# IDHTM Handoff Guide

## 1. Download and unpack

Download the attached `IDHTM-built-reaudited.zip` file from the task, then unpack it. The extracted folder contains the project root `IDHTM`.

```bash
unzip IDHTM-built-reaudited.zip
cd IDHTM
```

## 2. Install Node modules

The frontend is a Vite + React + TypeScript application. Install its dependencies from the frontend directory. This recreates `frontend/node_modules` locally; the archive intentionally does not include that generated directory.

```bash
cd frontend
pnpm install
pnpm build
pnpm test
```

If pnpm is unavailable, enable it through Corepack or install it with your preferred Node package manager.

## 3. Start the local project

In one terminal, start the frontend:

```bash
cd IDHTM/frontend
pnpm dev
```

In a second terminal, install the Python dependencies and start FastAPI:

```bash
cd IDHTM/backend
python3 -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:5173`. The UI has an offline local simulator fallback, so the frontend remains explorable when the API is not running. The demo login accepts any valid email and a password with at least six characters; `operator@idhtm.dev` / `demo-flight` is the seeded account.

## 4. Initialize Git

From the project root:

```bash
cd IDHTM
git init
git add .
git commit -m "Build IDHTM drone health and telemetry monitor"
git branch -M main
```

## 5. Create and connect GitHub repository

Create a new empty repository on GitHub without adding a README, license, or gitignore. Replace `YOUR_GITHUB_USERNAME` and `YOUR_REPOSITORY_NAME` with the actual values:

```bash
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME.git
git push -u origin main
```

For SSH instead:

```bash
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME.git
git push -u origin main
```

The repository includes the latest visual repair pass, frontend tests, backend integration tests, migration definition, demo runbook, architecture notes, and final re-audit.

## Latest visual pass

The current build includes the generated drone telemetry logo at `frontend/public/assets/images/branding/idhtm-logo-clean.png`, a single public launch path, a single Live monitor dashboard navigation item, a light operator basemap with route, road, park, water, controls, scale, and attribution, an image-led aircraft health card, contain-fit component thumbnails, a full selected-component image background, and bounded Configured badges on settings rows.

The latest verification is `pnpm build` passed, 10 frontend tests passed, backend compilation passed, 5 backend/integration tests passed, and the source audit found no `target` or `window.open` behavior in the frontend.

## Reference-inspired interaction pass

The public landing page now includes a scroll-driven sticky airframe story. The story progresses through Airframe, Propulsion, Position, and Action checkpoints and swaps the displayed asset and narrative as the visitor scrolls. This is an IDHTM-specific interaction inspired by the requested reference pattern; it does not copy the reference site’s brand, code, or assets.

The live monitor, flight detail, and flight replay screens now share one MapScene implementation, so the basemap, route treatment, road network, park/water shapes, aircraft marker, controls, scale, and attribution remain consistent. The dashboard’s former blank area is filled by the Next Best Action panel, and the aircraft health score is centered with a readable `/ 100` unit.

## Latest requested corrections

The live monitor now places Flight Status directly beside Next Best Action on desktop, with telemetry and alert panels below. The cockpit palette is now a deeper navy and cyan instrument treatment with amber heading/aircraft cues and teal GPS status. The health-detail image treatment preserves visible component imagery while keeping the selected detail copy and compact score meter readable. Replay map layering is isolated inside the replay panel and the controls are explicitly stacked below the map. The public landing airframe story now uses scroll-linked horizontal translation, vertical lift, and gentle rotation in addition to checkpoint image changes, creating a lively aircraft motion effect as the visitor scrolls.

## Exploded-drone product story

The public landing page now includes a Sonic Lamb–inspired but IDHTM-specific exploded-airframe interaction. The full drone remains the anchored core while battery, motors, sensors, GPS, and communications visuals separate outward with labeled callouts as the visitor scrolls. The stage also exposes a live subsystem health callout and narrative checkpoint, while `useReducedMotion` preserves a static accessible composition for users who prefer reduced motion.

## Dominant product-subject scroll interaction

The landing-page scroll section was revised after inspecting the Sonic Lamb reference directly. The drone is now the dominant large foreground subject during the pinned stage, rather than a small image card. As the section progresses, the airframe remains centered while the health-critical subsystem tiles separate outward with larger travel distances: battery, motors, sensors, GPS, and comms. The right-side narrative and subsystem health callout update in sync. The motion uses scroll-linked x/y/rotation values and keeps a reduced-motion fallback.

## Viewport centering correction

The exploded-drone sticky section now uses viewport-aware `svh` sizing and clamp-based spacing. Its headline, dominant drone stage, right narrative column, and first subsystem explanation fit together in the visible frame, while the section retains enough scroll height for the lower subsystem layers and later checkpoints to be reached naturally.
