# IDHTM UI Specification

## 1. Product Identity

**Product:** IDHTM — Intelligent Drone Health & Telemetry Monitor

**Core idea:**
> We are not building software that records telemetry. We are building software that understands drones.

IDHTM should feel like a modern aerospace engineering product: precise, calm, trustworthy, technical and premium.

The visual identity is **light-first**. Dark mode is not the primary experience. A darker immersive mode may be used selectively for the Cockpit screen if it improves readability and realism.

---

## 2. Visual Direction

### Desired aesthetic

- Premium aerospace / aviation engineering
- Real-world industrial technology
- Photorealistic imagery
- Bright, clean interfaces
- Precise engineering details
- Calm and trustworthy
- Minimal but sophisticated
- High-quality whitespace
- Restrained motion

### Avoid

- Generic dark SaaS dashboard
- Cyberpunk
- Hacker aesthetic
- Neon-heavy interfaces
- Glowing cards everywhere
- Sci-fi command centers
- Excessive glassmorphism
- Random futuristic decorations
- Artificial-looking AI website styling
- Generated UI inside images

### Visual philosophy

The physical world is supplied by generated photography.

The application UI supplies the intelligence layer:

**PHOTO + UI + TELEMETRY + DATA + ANIMATION**

Do not embed application UI into generated images.

---

## 3. Color System

### Primary

- Warm white / ivory background
- White surfaces
- Very light gray secondary surfaces
- Graphite / near-black primary text
- Cool gray secondary text
- Restrained aviation blue as primary accent

### Status

- Green — healthy / operational
- Amber — warning / attention
- Red — critical
- Blue — informational / active

Status colors should be used deliberately, not decoratively.

### Borders and depth

Use:

- Fine light borders
- Very subtle shadows
- Small elevation differences
- Soft gradients only when useful

Cards should feel like carefully engineered surfaces, not floating neon panels.

---

## 4. Typography

Use a modern premium sans-serif.

Typography hierarchy:

### Display

Large, confident hero headings.

### UI

Clean readable interface typography.

### Metrics

Numbers should have stronger visual distinction and an engineering/instrument feel.

Examples:

- 94%
- 124 m
- 43 km/h
- 274°
- 18 ms

Do not use decorative display fonts.

---

## 5. Global Layout

The application should have a consistent shell:

### Public website

- Top navigation
- Large editorial sections
- Strong whitespace
- Full-width imagery
- Scroll-triggered transitions
- Responsive CTA placement

### Authenticated application

- Persistent sidebar on desktop
- Top status bar
- Main content region
- Optional contextual right-side panel
- Responsive collapse on smaller screens

---

## 6. Public Routes

Required public routes:

- `/`
- `/product`
- `/how-it-works`
- `/architecture`
- `/future-ai`
- `/login`
- `/register`

---

## 7. Homepage Structure

### Section 1 — Hero

Headline concept:

**Understand Your Drone Before It Fails.**

Supporting message should communicate intelligent health monitoring for real-world flight operations.

Visual:

- Realistic drone photograph
- Bright / natural environment
- Large negative space for typography
- React-rendered telemetry overlays
- Primary CTA: Launch Monitor

Interaction:

- Subtle cursor response
- Telemetry markers can appear progressively
- Scroll transitions move from physical drone imagery into product intelligence

---

### Section 2 — The Problem

Show the transformation:

**Telemetry → Information → Understanding → Decision**

Raw measurements:

- Battery
- GPS
- IMU
- Altitude
- Speed
- Vibration
- Signal
- Motor output

should visually converge into meaningful health information.

Use scroll-triggered transitions rather than static cards.

---

### Section 3 — Silent Degradation

Explain gradual degradation of:

- Battery
- Motor bearings
- Signal
- Sensors

The visual should demonstrate that failures may begin as small trends.

Use charts / visual trends rendered by the application, not baked into images.

---

### Section 4 — Intelligence

Demonstrate examples:

**Battery draining faster**
→ Recommend maintenance

**Signal unstable**
→ Suggest Return-To-Home

**Motor vibration increasing**
→ Alert for possible bearing wear

**GPS accuracy degrading**
→ Flag possible sensor drift

The user should understand that IDHTM turns measurements into decisions.

---

### Section 5 — Product Showcase

Show the five core product modules:

- Live Dashboard
- Cockpit View
- Flight History
- Health Analytics
- Reports & Alerts

Prefer large interactive product previews over a wall of small cards.

---

### Section 6 — Architecture

Show:

**Pixhawk / MAVLink**
→ **Telemetry Adapter**
→ **FastAPI**
→ **Database**
→ **Rule Engine**
→ **Frontend**

Architecture should be rendered using real HTML/SVG/React components, not generated images.

---

### Section 7 — Future AI

Clearly distinguish future AI capabilities:

- Anomaly detection
- Fault prediction
- Predictive maintenance
- Intelligent health scoring

Do not falsely represent future AI as already implemented.

---

### Section 8 — CTA

Finish with a strong product CTA:

**Launch Monitor**

Secondary action may be:

**Explore Demo**

---

## 8. Authentication

### Login

Design:

- Bright aerospace operations environment
- Clean light interface
- Minimal fields
- Clear primary CTA
- No generic dark auth page

### Login interaction

Sequence:

1. User submits credentials
2. Authentication state appears
3. System initializes
4. Drone identity loads
5. Health state loads
6. Telemetry connection appears
7. Dashboard enters

Example system messaging:

- AUTHENTICATED
- IDHTM SYSTEM ONLINE
- DRONE-01 CONNECTED
- HEALTH CHECK
- MONITORING ACTIVE

Use subtle transitions.

---

## 9. First-Time Onboarding

After first login:

**Welcome to IDHTM**

Offer:

- Connect Pixhawk
- Use Simulator
- Explore Demo

Do not force hardware connection during development.

---

## 10. Application Routes

Authenticated routes:

- `/app`
- `/app/dashboard`
- `/app/cockpit`
- `/app/health`
- `/app/alerts`
- `/app/flights`
- `/app/flights/:id`
- `/app/maintenance`
- `/app/reports`
- `/app/connections`
- `/app/settings`

---

## 11. Application Navigation

Desktop navigation:

### Monitoring

- Overview
- Live Monitor
- Cockpit
- Health
- Alerts

### Flight Operations

- Flights
- Flight Replay

### Operations

- Maintenance
- Reports

### System

- Connections
- Settings

Global top area:

- Current drone
- Connection status
- Telemetry status
- Notifications
- User menu

---

## 12. Dashboard

The main dashboard must include:

- Health score
- Battery
- Altitude
- Speed
- GPS state
- Signal strength
- Flight mode
- Temperature
- Warning indicators
- Live telemetry charts
- Map / position visualization
- Current flight information

Recommended composition:

**Health**
+ **Live map**
+ **Flight status**
+ **Telemetry metrics**
+ **Live graphs**
+ **Alerts**

---

## 13. Live Telemetry

The dashboard must behave as live software.

Values should update over time:

- Battery decreases gradually
- Altitude changes
- Speed varies
- Signal fluctuates
- GPS state changes
- Temperature changes
- Vibration changes
- Health score reacts

Charts should animate continuously without becoming distracting.

---

## 14. Cockpit View

The cockpit should resemble real flight instrumentation.

Required:

- Artificial horizon
- Heading
- Altitude
- Airspeed
- Vertical speed
- Estimated remaining flight time

Optional immersive mode:

- Slightly darker interface
- Higher contrast
- Fullscreen
- Larger instrumentation

This is the one part of the product where a darker visual mode is acceptable and purposeful.

---

## 15. Health Monitoring

Components:

- Battery
- Motors
- GPS
- Sensors
- Communication

Each component should expose:

- Health score
- Current state
- Relevant metrics
- Trend
- Alerts
- Recommendation

Example:

**Motor 2**

- Health: 76
- Vibration: Increasing
- Temperature: Normal
- RPM consistency: Slight deviation
- Status: Potential bearing wear
- Recommendation: Inspect motor bearing before next extended flight

Clicking a component opens a detailed analysis panel.

---

## 16. Alert System

Alert categories:

- Low battery
- Weak communication signal
- High vibration
- GPS loss
- Temperature warnings
- Return-To-Home recommendation

Alert hierarchy:

### Informational

Low urgency

### Warning

Requires attention

### Critical

Requires immediate action

Alert UI should use:

- Subtle colored indicator
- Clear title
- Short explanation
- Current value
- Recommendation
- Action button

Example:

**COMMUNICATION SIGNAL DEGRADING**

Signal strength: 38%

Recommendation:
Prepare Return-To-Home.

Actions:
- View Telemetry
- Acknowledge

---

## 17. Notifications

Global notification center:

- Recent alert
- Maintenance recommendation
- Flight report ready
- System state changes

Clicking a notification should navigate directly to relevant context.

---

## 18. Flight History

Display:

- Flight identifier
- Date
- Duration
- Health score
- Alerts
- Summary

Clicking a flight opens:

- Historical telemetry
- Flight map
- Alerts
- Health changes
- Maintenance events
- Replay

---

## 19. Flight Replay

Interactive replay:

- Timeline
- Play / Pause
- Speed controls
- Drone position
- Telemetry synchronization
- Alert timestamps

When replaying:

- Map position moves
- Charts move
- Metrics update
- Alerts appear at their original timestamps

---

## 20. Maintenance

Maintenance system should convert recommendations into actionable records.

Example:

**Motor 2**

Potential bearing degradation

Detected:
August 21

Severity:
Medium

Recommended:
Inspect bearing

Actions:

- Create Maintenance Task
- Mark In Progress
- Mark Completed

Maintain maintenance history.

---

## 21. Reports

Reports should consolidate:

- Flight summary
- Overall health
- Component health
- Alerts
- Maintenance recommendations

Provide a clean report view and later allow generation/export through the backend.

---

## 22. Telemetry Connection

Connection page should support:

- Pixhawk / MAVLink
- ArduPilot SITL
- Simulator

Show:

- Connection state
- Packet rate
- Latency
- Message count
- Last update
- Source

Example:

**Status: Connected**

Packets/sec: 42
Latency: 18 ms

---

## 23. Demo Mode

A dedicated Demo Mode is strongly recommended.

Scenarios:

- Normal Flight
- Low Battery
- GPS Loss
- Signal Degradation
- Motor Vibration
- Multi-Fault

The selected scenario should affect live telemetry and trigger corresponding health / alert behavior.

Example:

**Motor Vibration**

Vibration increases
→ Motor health decreases
→ Health score reacts
→ Alert appears
→ Recommendation appears

This mode must work without physical drone hardware.

---

## 24. Animation System

Animation should be purposeful.

### Global

- Smooth page transitions
- Gentle section reveals
- Soft hover states
- Animated counters

### Hero

- Progressive appearance
- Subtle image movement
- Telemetry markers appearing
- Scroll-based transitions

### Dashboard

- Live graph movement
- Health changes
- Status transitions
- Alert entrance animations

### Cockpit

- Instrument movement
- Heading rotation
- Horizon movement
- Vertical speed response

### Flight Replay

- Timeline motion
- Map movement
- Synchronized telemetry

### Alerts

- Slide / fade
- Subtle emphasis only

Avoid:

- Constant floating elements
- Excessive parallax
- Bouncing UI
- Giant glows
- Animation on every element

---

## 25. Micro-interactions

Include:

- Button hover
- Card hover
- Navigation selection
- Tooltip appearance
- Dropdown transition
- Modal entrance
- Notification read state
- Toggle state
- Loading state
- Success / failure feedback

Interactions should feel physical and precise.

---

## 26. Responsive Design

### Desktop

Primary design target.

Use the full application shell.

### Laptop

Reduce panel density while keeping core information visible.

### Tablet

Collapse sidebar into a drawer.

### Mobile

Prioritize:

- Health
- Battery
- Signal
- Altitude
- Speed
- Critical alerts

Charts become simplified.

Cockpit becomes vertically arranged.

Avoid trying to reproduce the desktop cockpit literally on a phone.

---

## 27. Accessibility

Required:

- Semantic HTML
- Keyboard navigation
- Focus states
- Sufficient contrast
- ARIA labels where necessary
- Reduced-motion support
- Status information not communicated only through color

---

## 28. Loading States

All important screens need proper loading states.

Use:

- Skeletons
- Progress indicators
- Connection indicators
- Initialization messaging

Avoid blank screens.

---

## 29. Empty States

Empty states should explain what the user can do.

Example:

**No Flights Yet**

Connect a drone or run the simulator to create your first flight.

Action:
**Launch Simulator**

---

## 30. Error States

Errors must be human-readable.

Example:

**Telemetry Connection Lost**

The system has stopped receiving telemetry.

Show:

- Last packet time
- Connection state
- Retry action

Do not expose raw stack traces in the UI.

---

## 31. Imagery Rules

Generated images are stored in:

`frontend/public/assets/images/`

Categories:

- hero
- drones
- components
- environments
- cockpit
- maintenance
- backgrounds

Use the images as photographic layers.

Do not regenerate UI inside them.

UI, telemetry and overlays must remain HTML/SVG/React.

---

## 32. Performance Rules

- Lazy-load large images
- Use WebP/AVIF where appropriate
- Compress assets
- Avoid unnecessary re-renders
- Animate with transform/opacity when possible
- Do not run expensive animation loops unnecessarily
- Keep dashboard telemetry updates efficient
- Keep map rendering isolated where possible

---

## 33. Design Consistency

All application surfaces should share:

- Consistent spacing
- Consistent typography
- Consistent borders
- Consistent corner treatment
- Consistent status colors
- Consistent animation timing
- Consistent interaction patterns

Do not create a completely different visual language for each page.

---

## 34. Core Product Principle

The application must repeatedly reinforce:

**Telemetry**
→ **Information**
→ **Understanding**
→ **Decision**
→ **Action**

The public website communicates this transformation.

The authenticated application demonstrates it.

---

## 35. Non-Negotiable UI Rules

1. Primary visual mode is light.
2. Do not default to a dark cybersecurity dashboard.
3. Do not use cyberpunk styling.
4. Do not use neon as the primary visual language.
5. Do not place generated UI text into generated images.
6. Use real HTML/SVG/React for interface elements.
7. Keep animation purposeful.
8. Keep the interface premium and restrained.
9. Maintain believable aerospace/engineering visual language.
10. Every major interaction should communicate system state or product intelligence.
