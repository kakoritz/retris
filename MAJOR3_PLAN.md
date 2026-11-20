# RETRIS — Major 3: Web Portal & Multiplayer Platform

**Status:** PLANNED — execute when user says "begin Major 3"  
**Scope:** Full web application, PC-first, multiplayer, persistent global leaderboards

---

## Vision

A competitive web game that drives traffic and earns street cred. Easy to play during a lunch break, compelling enough to keep coming back for daily/weekly score chases. Full-name player accounts, real-time global rankings, social sharing of scores.

**Reference games:** Tetris Effect (visual polish), Jstris (competitive speed, minimal UI, global leaderboards), TETR.IO (accounts, rankings, multiplayer rooms), 1v1.LOL (dead simple to enter, keeps players).

---

## Tech Stack

### Backend
- **Python FastAPI** — REST API + WebSocket server
- **PostgreSQL** (via SQLAlchemy or asyncpg) — player accounts, scores, sessions
- **Redis** — real-time leaderboard caching, session state, rate limiting
- **Alembic** — database migrations
- **JWT auth** — lightweight account tokens (no OAuth to start)

### Frontend
- **Pygame-WASM via Pygbag** — port existing Python game to browser, OR
- **React + HTML5 Canvas** — custom web renderer consuming a game state API
  - Recommended: Pygbag first (zero rewrite), JS renderer in v3.1 for multiplayer latency
- **WebSocket** — real-time multiplayer, score streaming, live leaderboard updates

### Hosting
- **Fly.io** or **Railway** — zero-config containers, free tier to start
- **Supabase** or **Neon** — managed Postgres (free tier)
- **Cloudflare** — CDN, DDoS protection, free tier

---

## Feature Scope

### v3.0 — Core Web Game
- [ ] Pygbag WASM build: existing Python game runs in browser
- [ ] Player accounts: username (full name, not initials) + email, no OAuth
- [ ] Score submission via API after each game (JWT-authenticated)
- [ ] Global leaderboards: All-Time Top 100, Daily, Weekly, Monthly
- [ ] Guest play (no account): scores shown but not saved
- [ ] Splash screen and menu adapted for PC (mouse-driven, wider layout)
- [ ] Keyboard controls primary, mouse secondary

### v3.1 — Competitive Features
- [ ] Real-time live leaderboard (WebSocket updates while others play)
- [ ] "Playing now" counter — shows active players
- [ ] Personal stats page: avg score, total games, level progression, best streaks
- [ ] Share button: generate score image card for social (og:image)
- [ ] Daily challenge: fixed seed board, everyone gets same piece sequence

### v3.2 — Multiplayer
- [ ] 1v1 rooms: see opponent's board in side panel (ghost view)
- [ ] Garbage lines sent on line clears (standard competitive mechanic)
- [ ] Spectator mode: watch any active match
- [ ] Room codes: create/join/share link
- [ ] Match history

---

## Leaderboard Design

### Scoring periods
- **All-Time:** persists forever, never resets
- **Monthly:** resets 1st of each month (archive kept)
- **Weekly:** resets Monday 00:00 UTC
- **Daily:** resets midnight UTC

### Each leaderboard shows Top 100 with:
- Rank, Player Name, Score, Level, Lines, Time, Date

### Personal board: player sees their own rank even if outside Top 100

---

## Database Schema (simplified)

```sql
players   (id, username, email_hash, created_at, games_played, best_score)
scores    (id, player_id, score, level, lines, duration_s, seed, submitted_at)
-- Leaderboard views computed from scores with window functions + Redis cache
```

---

## PC Layout Notes (not mobile)

Full browser window available. Proposed layout:
```
┌─────────────────────────────────────────────────────────┐
│  RETRIS  [Play]  [Leaderboard]  [Profile]  [Login]      │  header
├──────────┬──────────────────────┬───────────────────────┤
│ NEXT     │                      │  LIVE  LEADERBOARD    │
│ HOLD     │   Game Board         │  1. playerX  315,240  │
│ SCORE    │   (larger, HD)       │  2. kakoritz 298,100  │
│ LEVEL    │                      │  ▶ You: #47  182,500  │
│ LINES    │                      │  ...                   │
└──────────┴──────────────────────┴───────────────────────┘
```

- Wider board, bigger cells (CELL=40+)
- Sidebar can hold full next queue, hold, full stats
- Live leaderboard panel shows current daily/weekly top 10 updating in real-time
- Animated particle effects, same NES aesthetic, full screen visuals

---

## Marketing / Traffic Plan (Phase 4)

- Submit to: itch.io, Newgrounds, Kongregate, CrazyGames, HTML5Games.com
- SEO: "free online Tetris" / "Tetris game unblocked" targeting
- Reddit: r/WebGames, r/Tetris, r/gamedev showcase post
- Discord: gaming servers, dev communities
- "Score of the Day" auto-post to Twitter/X with score card image
- Challenge a friend: share link opens game with rival score highlighted

---

## When to Begin

User says: **"begin Major 3"**

Kick-off sequence:
1. Set up Python FastAPI project in `/vscode/retris-web/`
2. Pygbag proof-of-concept: existing game in browser in <2 hours
3. PostgreSQL schema + Alembic migrations
4. Score submission API (JWT auth)
5. Global leaderboard endpoint
6. Frontend HTML wrapper with Pygbag embed
7. Deploy to Fly.io
8. Iterative: multiplayer, social features, marketing

---

*This document is the brief. Nothing starts until "begin Major 3."*
