# Configuration

Three layers, later ones win:

1. `config.example.yml`: every key, documented, with example values (tracked).
2. `presets/<preset>.yml`: the profession (the `role` section). See [presets/README.md](../presets/README.md).
3. `config.yml`: **your** settings, git-ignored. Only keys you want to change. `init.py` writes it.

Lists are replaced as a whole; maps (`seniority_bonus`, `title_penalties`, `fallback_skills`) are
merged key by key. Check the result with `python doctor.py`.

Facts about you (experience, skills, salary, contacts, CV) do **not** go here: they live in
`Linkedin Agent/candidate-profile.md` and `Job Hunter Agent/screening-playbook.md`.

## Keys

### `preset`
Profession preset name, e.g. `frontend`. `python search_jobs.py --list-presets` lists them.

### `candidate`
| Key | Example | Used for |
|---|---|---|
| `reply_language` | `en`, `ka`, `de` | language the agents use with you (recruiters get replies in their own language) |
| `timezone` | `"GMT+4"` | interview-scheduling messages |
| `timezone_window` | `[0, 4]` | UTC offsets you can work with; "GMT+2" / "UTC+3" in a posting counts as friendly |
| `cv_file_name` | `"Jane_Doe_CV.pdf"` | file name of the CVs you upload |

### `role` (normally from the preset)
| Key | Used for |
|---|---|
| `default_query` | default `--query` for job sites |
| `target_roles` | +20 when a title contains one; fallback when the profile lists none |
| `title_keywords` / `title_exclude` | company-board scan: title must contain one keyword and no excluded phrase |
| `seniority_bonus` | points for senior / lead / staff / principal titles |
| `title_penalties` | minus points for intern, junior, ... (and role-specific ones) |
| `fallback_skills` | skill weights, used only when the profile has no Skills section |

### `location`
| Key | Used for |
|---|---|
| `home_country`, `home_places` | on-site / hybrid jobs here are fine; local job sites |
| `home_exclude` | look-alikes that are not home (e.g. the US state of Georgia) |
| `open_to_relocation` | on-site abroad is still blocked unless the posting offers relocation |
| `friendly_regions` | remote scopes you can work under (worldwide, EMEA, Europe, ...) |
| `locked_regions` | remote limited to these = blocker (you can't live / work there) |
| `check_regions` | flag "check right to work", but don't block (contracts may still work) |

`init.py` removes the regions you live in from `locked_regions` / `check_regions` automatically
(for example US for a US resident, EU for an EU citizen).

### `search`
`sources` (default list for `search_jobs.py`), `indeed_country`, `min_score`, `remote_only`.

### `scoring`
`stale_days` (older postings lose 0.3), `repost_gap_days`, and the `verdicts` thresholds
(`apply` 4.0, `consider` 3.5, `research` 2.5).

## Environment variables

| Variable | Effect |
|---|---|
| `JOB_HUNTER_CONFIG` | path to another user config instead of `config.yml` |
| `JOB_HUNTER_PRESET` | preset for this process (what `--preset` sets) |
| `GEMINI_API_KEY`, `LINKEDIN_AGENT_MODEL` | optional AI drafts in `Linkedin Agent/run.py` (`.env`) |
| `CDP_PORT` | Chrome remote-debugging port for the LinkedIn CLI (default 9222) |

## Examples

Data analyst in Germany, open to EU remote, no relocation:

```yaml
preset: data-analyst
candidate: {reply_language: de, timezone: "GMT+1", timezone_window: [-1, 3], cv_file_name: "Max_Muster_CV.pdf"}
location:
  home_country: Germany
  home_places: [germany, berlin, munich, hamburg, deutschland]
  home_exclude: []
  open_to_relocation: false
  check_regions: [uk, united kingdom, london]     # EU removed: an EU citizen can work there
```

Same profession, but also catch "Analytics Engineer" titles:

```yaml
role:
  title_keywords: [data analyst, product analyst, bi analyst, analytics engineer]
```
