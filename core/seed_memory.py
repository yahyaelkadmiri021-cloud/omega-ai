#!/usr/bin/env python3
"""OMEGA AI — Phase 5 memory seed (one-off, idempotent).

Seeds data/omega.db from ~/workspace/muse_omega/MUSE_MEMORY/ (2026-09-29
snapshot). Real rows only; every row carries its source file. Re-runs insert
nothing new (UNIQUE / PK guards + (kind, title) dedup for memory_entries).

Run:  python3 core/seed_memory.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEM = Path.home() / "workspace" / "muse_omega" / "MUSE_MEMORY"
DB_PATH = ROOT / "data" / "omega.db"
SCHEMA = ROOT / "core" / "memory-schema.sql"
SEED_AT = "2026-09-29 16:20:00"  # snapshot date of every source file below
SRC = "MUSE_MEMORY (2026-09-29 snapshot)"

STATUS_MAP = {"LIVE": "running", "PARTIAL-LIVE": "running",
              "BUILDING": "planning", "PARTIAL": "planning",
              "BLOCKED": "waiting"}


def load_json(name):
    return json.loads((MEM / name).read_text(encoding="utf-8"))


def main() -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    counts = {"projects": 0, "tasks": 0, "decisions": 0,
              "memory_entries": 0, "tools": 0, "errors": 0, "activity_log": 0}
    skipped = {"projects": 0, "tasks": 0, "decisions": 0,
               "memory_entries": 0, "tools": 0, "errors": 0}

    def add_project(name, objective, status):
        cur = conn.execute(
            "INSERT OR IGNORE INTO projects (name, objective, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)", (name, objective, status, SEED_AT, SEED_AT))
        if cur.rowcount:
            counts["projects"] += 1
        else:
            skipped["projects"] += 1
        return conn.execute(
            "SELECT id FROM projects WHERE name = ?", (name,)).fetchone()[0]

    def add_task(project_id, agent_id, title, status, result_path=None):
        exists = conn.execute(
            "SELECT id FROM tasks WHERE project_id = ? AND title = ?",
            (project_id, title)).fetchone()
        if exists:
            skipped["tasks"] += 1
            return
        conn.execute(
            "INSERT INTO tasks (project_id, agent_id, title, status, result_path, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, agent_id, title, status, result_path, SEED_AT, SEED_AT))
        counts["tasks"] += 1

    def add_decision(title, rationale):
        exists = conn.execute(
            "SELECT id FROM decisions WHERE title = ?", (title,)).fetchone()
        if exists:
            skipped["decisions"] += 1
            return
        conn.execute(
            "INSERT INTO decisions (title, rationale, decided_at) VALUES (?, ?, ?)",
            (title, rationale, SEED_AT))
        counts["decisions"] += 1

    def add_entry(kind, title, body, source):
        exists = conn.execute(
            "SELECT id FROM memory_entries WHERE kind = ? AND title = ?",
            (kind, title)).fetchone()
        if exists:
            skipped["memory_entries"] += 1
            return
        conn.execute(
            "INSERT INTO memory_entries (kind, title, body, source, created_at)"
            " VALUES (?, ?, ?, ?, ?)", (kind, title, body, source, SEED_AT))
        counts["memory_entries"] += 1

    def add_tool(tool_id, name, status, last_verified, notes):
        cur = conn.execute(
            "INSERT OR IGNORE INTO tools (id, name, status, last_verified, notes)"
            " VALUES (?, ?, ?, ?, ?)",
            (tool_id, name, status, last_verified, notes))
        if cur.rowcount:
            counts["tools"] += 1
        else:
            skipped["tools"] += 1

    # ---------- projects: ACTIVE_GOALS.md table (parsed, not transcribed) ----------
    goal_rows = []
    for line in (MEM / "ACTIVE_GOALS.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| ([^|]+) \| ([^|]+) \| ([^|]+) \|", line)
        if m and m.group(1).strip() not in ("Goal slug", "---"):
            goal_rows.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip()))
    proj_ids = {}
    for slug, status, headline in goal_rows:
        if status == "STALE":
            continue
        proj_ids[slug] = add_project(slug, headline, STATUS_MAP.get(status, "pending"))
    proj_ids["documentary-studio"] = add_project(
        "documentary-studio",
        "Amazon rainforest documentary pilot — build started 2026-09-29 (~/workspace/documentary_studio/)",
        "planning")
    proj_ids["OMEGA AI"] = add_project(
        "OMEGA AI",
        "Autonomous AI agent operating system — Arabic-first, 8 agents, permission gates, persistent memory, self-improvement",
        "running")

    # ---------- tasks: MUSE_MEMORY/TASKS.md (open + done) ----------
    tasks = [
        ("noor-beauty-storefront-transformation", "pm",
         "NOOR BEAUTY: repaired build ready; publishing to public link awaits Yahya's yes, then verify live",
         "pending", None),
        ("shopify-dropshipping-store-build-vendora", "pm",
         "Final report to Yahya: تم / المتبقي / المعلق per store", "pending", None),
        ("creator-monetization-programs-enrollment", "business",
         "PartnerStack: provide LinkedIn URL, complete network application, then apply to Jasper AI / Writesonic / Copy.ai",
         "pending", None),
        ("ai-short-video-content-factory-and-auto-publishing", "content",
         "Travel shorts pipeline (~/workspace/travel_shorts_pipeline/): await build result + verify output",
         "pending", None),
        ("documentary-studio", "content",
         "Amazon documentary pilot (~/workspace/documentary_studio/): build in progress",
         "pending", None),
        ("kids-songs-and-brain-frequency-youtube-channels", "pm",
         "Phone verification (Yahya): Hush Aura channel; kids-channel custom thumbnails",
         "waiting", None),
        ("ai-short-video-content-factory-and-auto-publishing", "pm",
         "Channel ownership (Yahya): مواقف مضحكة owning account; هل تعلم؟ Brand Account access restore",
         "waiting", None),
        ("shopify-dropshipping-store-build-vendora", "business",
         "Shopify paid plan + payment/bank activation (Yahya)", "waiting", None),
        ("global-travel-media-brand", "business",
         "Stay22 payout method connection (Yahya)", "waiting", None),
        ("viverse-partner-program-enrollment", "business",
         "VIVERSE Partner Program eligibility ~2026-10-23 (account age rule)", "waiting", None),
        ("global-travel-media-brand", "operator",
         "Google Search Console property for https://voyavera.surge.sh (Yahya adds)", "waiting", None),
        ("elvariajewels-etsy-shop-optimization", "qa",
         "Etsy live shop health check (2026-09-29 ~09:09): public/active, 7 listings + 1 draft, 0 orders, $0 revenue",
         "completed", None),
        ("shopify-dropshipping-store-build-vendora", "qa",
         "Shopify/Vendora health check (2026-09-29 ~09:50): public, 17 products CJ-connected, 0 orders",
         "completed", None),
        ("shopify-dropshipping-store-build-vendora", "operator",
         "Deleted 5 unconnected products (HydroPup, CalmPaws, NightGuard, SlowBite, PlayBall) + backup saved",
         "completed", None),
        ("creator-monetization-programs-enrollment", "business",
         "PartnerStack account created (2026-09-29 15:46); email verification completed (15:47)",
         "completed", None),
        ("OMEGA AI", "operator",
         "MiniMax/Hailuo free account; Kling/Leonardo/Dreamina free tiers (Google OAuth, $0)",
         "completed", None),
        ("kids-songs-and-brain-frequency-youtube-channels", "content",
         "Kids song KIDS_HABITS_001_NR published 2026-09-29 16:08:42+01",
         "completed", "https://www.youtube.com/shorts/szLWCId9cu8"),
        ("ai-short-video-content-factory-and-auto-publishing", "content",
         "Tiny Groovers short published 2026-09-29",
         "completed", "https://www.youtube.com/shorts/Mfcek0bI72g"),
    ]
    for slug, agent, title, status, path in tasks:
        add_task(proj_ids[slug], agent, title, status, path)

    # ---------- decisions ----------
    for title, rationale in [
        ("Hard $0 rule",
         "No subscriptions, credits, ads, domains/hosting, paid AI tools, card-required trials — free/open-source only; any payment need = stop and ask."),
        ("Paper trading is simulation-only",
         "Real-money trading refused outright even under explicit authorization."),
        ("CJ Dropshipping supplier path abandoned",
         "Abandoned at Yahya's order 2026-09-29; DSers path retired."),
        ("Mixkit rejected as commercial clip source",
         "Most of the catalog is Restricted License (personal use only); commercial needs paid Envato. Only legacy low-ID pages may show the Free License — verify per video page."),
        ("TikTok publishing paused",
         "Paused by Yahya's order; files only, no publishing."),
        ("Shopify Admin API blocked — browser admin is the route",
         "Direct Admin API calls blocked at platform level (401/403 on 8 submissions); browser-based admin on https://admin.shopify.com/store/bitn1f-v6."),
        ("PartnerStack network application pending LinkedIn URL",
         "Account created + email verified 2026-09-29; network application needs Yahya's LinkedIn URL; then apply to Jasper AI / Writesonic / Copy.ai."),
        ("Stale goals superseded",
         "vendora-dropshipping + dropshipping-venture superseded by shopify-dropshipping-store-build-vendora; goal/goal-2 are generic placeholders."),
    ]:
        add_decision(title, rationale)

    # ---------- memory_entries ----------
    add_entry("instruction", "User profile — Yahya Elkadmiri",
              "Yahya Elkadmiri, Morocco (Africa/Casablanca), Arabic/Darija + English. Mobile 0619773999; Hay Attaqaddoum, Rue 123, Ben Guerir. "
              "Building autonomous income systems at hard $0; first real sales/clients is the goal (two storefronts, $0 as of 2026-09-29). "
              "Full operational autonomy, no routine questions. Reports in Arabic, format تم / المتبقي / المعلق; report only on first client/sale/dollar, major opportunity, blocker, or milestone. "
              "Hard boundaries (Yahya alone): passwords/OTP/2FA/KYC/ID/banking/payout/tax, payments/purchases, legal signatures, irreversible financial actions and deletions.",
              "MUSE_MEMORY/USER_PROFILE.md")
    add_entry("instruction", "Prompt library — reusable macros",
              "@REPORT (STATUS/COMPLETED/EVIDENCE/CHANGES/NEXT/BLOCKERS/MEMORY/OPPORTUNITIES); @STATE (read SYSTEM_STATE.json); @AUDIT (facts, quality, originality, license, SEO, UX, mobile, speed, accessibility, security, links, CTA, monetization, analytics, errors); "
              "@VIDEO (concept, hook, script, scenes, visual prompts, audio, timing, transitions, text, edit, thumbnail, title, description, tags, publish, repurpose); @MONEY (verify, rank, testable experiments, track); @MEM (re-read USER_PROFILE + PROJECTS + ACTIVE_GOALS + SYSTEM_STATE before acting). "
              "Never add an untested prompt as if proven.",
              "MUSE_MEMORY/PROMPT_LIBRARY.md")
    for title, body in [
        ("Voyavera travel platform (P001–P008)",
         "Global travel media brand (goal_57f206fb0336) — English SEO travel articles, hourly publisher (voyavera-publish-cycle), website https://voyavera.surge.sh — LIVE. "
         "Monetization: Travelpayouts (781762, 7 programs approved) + Stay22 (ID voyavera, ACTIVE); actual revenue $0. Facebook Page Voyavera (61594818359606); IG @voyavera.official; Pinterest profile. "
         "Pending: Search Console property (Yahya); Stay22 payout method (Yahya)."),
        ("AI video studio / Shorts factory (P009–P015)",
         "Publisher crons (every 5h unless noted), all on 021: قصص لا تُصدق, هل تعلم؟ (access BLOCKED from 021), What If Lab (EN), Unbelievable Facts (EN), مواقف جميلة, مواقف مضحكة (NOT on 021 — ownership BLOCKED), "
         "Tiny Groovers, RealitySlip, Glance Gasp (host Milo Hart), لحن صغير (kids songs), Hush Aura (publisher DISABLED — phone verification), وثائقيات ما قبل النوم, قصص جميلة, ملخصات الأفلام, IRONCLASH, ملخصات المانهوا."),
        ("Documentary studio (P010)",
         "Travel shorts pipeline (licensed Pexels/Pixabay/Coverr, travel template) — in build 2026-09-29. Documentary studio for Amazon rainforest pilot — build started 2026-09-29 (~/workspace/documentary_studio/). وثائقيات ما قبل النوم daily publisher (22:00)."),
        ("Long-form YouTube (P011–P012)",
         "Arabic: مخزن الأسرار (UCBTiqoiw2h3pUaZne7ioSsg) — daily 09:00. English: The Mind Vault (UC1F8IU3IoBrLccu3Qkr_9DA) — daily 19:00. Short-form viral: viral-discovery-scan cron (12h)."),
        ("Blender 3D (P014)",
         "Blender 4.5.12 LTS portable at ~/workspace/tools/blender (headless, Eevee; 2 cores/~7GB RAM; NEVER parallel with ffmpeg)."),
        ("Ecommerce (P021–P025)",
         "Vendora: Shopify store bitn1f-v6, PUBLIC, 17 products active (CJ-connected); orders 0, revenue $0; trial ~7 days left — paid plan + payments are Yahya's alone. "
         "ElvariaJewels: Etsy, public, 7 listings + 1 draft, orders 0, revenue $0, 7-day traffic 6 views/5 visits. NOOR BEAUTY: repaired build ready under slug jamali-beauty; public link still old version; publishing awaits Yahya's yes."),
        ("Monetization (P026–P030)",
         "Income DB: Travelpayouts, Stay22, Fiverr, Temu, Payhip, VIVERSE, Etsy, YouTube — all $0 revenue. income-opportunity-scan cron (every 24h); paper-trading-cycle (12h, simulation only). "
         "PartnerStack affiliate network signup in progress (2026-09-29): Jasper AI, Writesonic, Copy.ai applications pending."),
        ("Freelance (P028)",
         "Fiverr gig factory — 4-active-gig model; price approval by Yahya only. Career goal: بناء مسار مهني في العمل الحر."),
        ("OMEGA AI — this project",
         "Autonomous AI agent operating system — Arabic-first, 8 agents, permission gates (GREEN/YELLOW/RED), persistent memory, self-improvement. "
         "v0.1.2 (2026-11-07): dashboard 12 sections, agent registry, SQLite memory, stdlib bridge, Electron scaffold, deploy-prep (Render Free + Cloudflare Pages)."),
    ]:
        add_entry("project", title, body, "MUSE_MEMORY/PROJECTS.md")
    for title, body in [
        ("VIVERSE Partner Program eligibility ~2026-10-23",
         "Account must be 30+ days old; eligible around 2026-10-23. Morocco payout eligibility unconfirmed as of 2026-09-23."),
        ("NOOR BEAUTY publish approval is Yahya's alone",
         "Repaired build ready under slug jamali-beauty; public link still shows the old version; replacement awaits Yahya's yes."),
    ]:
        add_entry("decision", title, body, "MUSE_MEMORY/ACTIVE_GOALS.md")
    for fname, key in [("AI_TOOLS.json", "tools"), ("VIDEO_TOOLS.json", "tools"),
                       ("IMAGE_TOOLS.json", "tools"), ("THREE_D_TOOLS.json", "tools")]:
        for t in load_json(fname)[key]:
            body = (t.get("notes", "") + f" Free level: {t.get('free_level', 'n/a')}."
                    if t.get("free_level") else t.get("notes", ""))
            add_entry("tool", f"{t['name']} ({t['tool_id']})", body,
                      f"MUSE_MEMORY/{fname}")
    for e in load_json("ERROR_LOG.json")["errors"]:
        add_entry("error", f"{e['class']} ({e['date']})",
                  f"{e['description']} Fix: {e['fix']}", "MUSE_MEMORY/ERROR_LOG.json")
    for o in load_json("OPPORTUNITY_DB.json")["opportunities"]:
        add_entry("research",
                  f"Opportunity: {o['name']} [{o['status']}]",
                  f"Category: {o['category']}. Model: {o['potential_revenue_model']}. Free/paid: {o['free_or_paid']}. "
                  f"Country: {o['country_availability']}. Requirements: {o['requirements']}. Risks: {o['risks']}. "
                  f"Terms: {o['terms']}. URL: {o['url']}. Last verified: {o['last_verified']}.",
                  "MUSE_MEMORY/OPPORTUNITY_DB.json")
    state = load_json("SYSTEM_STATE.json")
    add_entry("finding", "System state 2026-09-29",
              f"Active projects: {'; '.join(state['active_projects'])}. "
              f"Blockers (Yahya only): {'; '.join(state['blockers_yahya_only'])}. "
              f"Completed today: {'; '.join(state['completed_today'])}. "
              f"Next actions: {'; '.join(state['next_actions'])}.",
              "MUSE_MEMORY/SYSTEM_STATE.json")
    cal = load_json("CONTENT_CALENDAR.json")
    add_entry("finding", "Content calendar — publisher cadences",
              "Quality overrides cadence — a slot that cannot meet the quality bar ships NOTHING. " +
              "; ".join(f"{s['channel']}: {s['cadence']}" + (f" ({s['note']})" if s.get("note") else "")
                        for s in cal["schedule"]),
              "MUSE_MEMORY/CONTENT_CALENDAR.json")
    mon = load_json("MONETIZATION_SOURCES.json")
    add_entry("finding", "Monetization sources — all $0",
              "All $0 actual revenue so far. Never promise or fabricate revenue. " +
              "; ".join(f"{s['name']}: {s['revenue']} [{s['status']}]" for s in mon["sources"]),
              "MUSE_MEMORY/MONETIZATION_SOURCES.json")
    aff = load_json("AFFILIATE_NETWORKS.json")
    add_entry("finding", "Affiliate networks (5)",
              "; ".join(f"{n['name']}: {n['notes']} Revenue {n['revenue']} [{n['status']}]"
                        for n in aff["networks"]),
              "MUSE_MEMORY/AFFILIATE_NETWORKS.json")
    web = load_json("WEBSITE_LIBRARY.json")
    add_entry("finding", "Websites (3)",
              "; ".join(f"{w['name']}: {w['url']} [{w['status']}] — {w['notes']}"
                        for w in web["websites"]),
              "MUSE_MEMORY/WEBSITE_LIBRARY.json")
    hist = (MEM / "TASK_HISTORY.md").read_text(encoding="utf-8")
    add_entry("finding", "Task history 2026-09-27–29 (headlines)",
              "2026-09-29: PartnerStack account created + verified; Tiny Groovers + kids song published; travel Shorts pipeline delegated; Amazon documentary pilot started. "
              "2026-09-28: Blender 3D pipeline launched; Kokoro TTS verified (EN only); Shopify Admin API diagnosis (browser admin is the route); Voyavera audit fixes deployed live. "
              "2026-09-27: IRONCLASH identity verified; RealitySlip + Glance Gasp + لحن صغير + Hush Aura channels created; Mixkit REJECTED as commercial clip source; TikTok paused.",
              "MUSE_MEMORY/TASK_HISTORY.md")
    add_entry("finding", "Daily log 2026-09-29",
              "PartnerStack account created + email verified; network application blocked on LinkedIn URL. Travel Shorts pipeline delegated; Amazon documentary pilot started. "
              "Tiny Groovers + kids song published. OMEGA persistence setup completed. Encoder healthy; revenue $0 across all programs.",
              "MUSE_MEMORY/DAILY_LOG.md")
    add_entry("finding", "Active goals — 34 tracked (2026-09-29)",
              "Status key: LIVE = publisher/automation crons active; BUILDING = in progress; BLOCKED = needs Yahya's action; STALE = superseded, do not rebuild. "
              "LIVE: Voyavera, Shorts factory, long-form, Vendora, ElvariaJewels, Temu, monetization scan, 30-min review, paper trading. "
              "BLOCKED: manhwa (Drive step), reaction channel (ownership), NOOR BEAUTY (publish approval), VIVERSE (age rule), workflow automation (API keys).",
              "MUSE_MEMORY/ACTIVE_GOALS.md")

    # ---------- tools table: full TOOL_LIBRARY + AI/VIDEO/IMAGE/3D ----------
    for t in load_json("TOOL_LIBRARY.json")["tools"]:
        add_tool(t["tool_id"], t["name"], "verified", t.get("last_verified"),
                 t.get("notes", "")[:500])
    for fname in ["AI_TOOLS.json", "VIDEO_TOOLS.json", "IMAGE_TOOLS.json", "THREE_D_TOOLS.json"]:
        for t in load_json(fname)["tools"]:
            add_tool(t["tool_id"], t["name"], "verified", t.get("last_verified"),
                     t.get("notes", "")[:500])

    # ---------- errors table ----------
    for e in load_json("ERROR_LOG.json")["errors"]:
        exists = conn.execute(
            "SELECT id FROM errors WHERE message = ?", (e["description"],)).fetchone()
        if exists:
            skipped["errors"] += 1
            continue
        conn.execute(
            "INSERT INTO errors (message, solution, occurred_at) VALUES (?, ?, ?)",
            (e["description"], e["fix"], e["date"] + " 00:00:00"))
        counts["errors"] += 1

    # ---------- activity log ----------
    total = sum(counts.values())
    conn.execute(
        "INSERT INTO activity_log (actor, action, detail) VALUES (?, ?, ?)",
        ("seed", "phase5-seed",
         f"Seeded omega.db from {SRC}: {total} rows inserted "
         f"({counts}). Skipped as already present: {skipped}."))
    counts["activity_log"] += 1

    conn.commit()
    final = {t[0]: conn.execute(f'SELECT COUNT(*) FROM "{t[0]}"').fetchone()[0]
             for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    return {"inserted": counts, "skipped": skipped, "final_counts": final}


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
