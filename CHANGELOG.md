# Changelog

All notable changes. Format: [Keep a Changelog](https://keepachangelog.com/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Any profession:** 11 presets in `presets/` (QA automation, frontend, backend, full-stack, mobile,
  DevOps, data engineer, data analyst, ML engineer, product designer, product manager), chosen with
  `preset:` in `config.yml` or `search_jobs.py --preset`; `--list-presets`.
- **Any country:** `config.yml` (template `config.example.yml`) holds role, home country and cities,
  friendly / locked / check regions, time-zone window, reply language, CV file name, sources and
  thresholds. Nothing about one candidate is hard-coded any more.
- **Company boards:** `--sources ats` scans ~200 companies through the public Greenhouse, Ashby,
  Lever, SmartRecruiters and Recruitee APIs (no browser, no CAPTCHA, full text, ~30 s).
- **1–5 rating and verdicts** (Apply / Consider / Research first / Skip) with flags; blockers for
  region-locked remote, required work authorization or security clearance, on-site abroad without
  relocation, and jobs already in the report; legitimacy signals (stale, reposted, thin description).
  `--hide-skip`, `--min-rating`, `--ats-days`.
- **One-command setup:** `init.py` (venv, packages, Chromium, templates, `config.yml` wizard,
  `.mcp.json`, `.env`) and `doctor.py` health check (`--online`, `--json`).
- **Claude Code:** skills in `.claude/skills/`, Playwright MCP browser (headed + headless, shared
  profile), first-run onboarding that fills the profile from your CV; tailored CV per external
  application; salary conversion at today's rate; work mode verified on the job page.
- Screening-playbook template; docs in `docs/`; Georgian README; contributing guide and GitHub templates.

### Changed
- README rewritten around the Claude Code workflow and `init.py`.
- LinkedIn Easy Apply keeps the CV already stored on LinkedIn (no duplicate uploads).

## [0.1.0] - 2026-09-13

### Added
- Multi-source aggregator (`search_jobs.py`): LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google
  Jobs via JobSpy, and jobs.ge; tracking-parameter cleaning, deduplication, 0–100 fit scoring.
- LinkedIn agent: terminal pipeline manager, profile-grounded reply drafts (templates or Gemini),
  interview-slot scheduling, tiered prompt context.
- Agent skill and rule templates, privacy-first git-ignored personal files, regression test suite.
