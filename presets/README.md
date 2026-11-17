# Profession presets

A preset tells Job-Hunter what your profession looks like in job titles and descriptions. Pick one
in `config.yml`:

```yaml
preset: frontend
```

or try one for a single run without changing anything:

```bash
python search_jobs.py --preset devops --sources ats
python search_jobs.py --list-presets
```

| Preset | Default search | Typical titles it keeps |
|---|---|---|
| `qa-automation` | QA Automation Engineer | QA Engineer, SDET, Test Automation Engineer |
| `frontend` | Frontend Engineer | Frontend / Front-End Developer, React Developer, UI Engineer |
| `backend` | Backend Engineer | Backend Engineer, Java / Go / Python / Node.js / .NET Developer |
| `fullstack` | Full Stack Engineer | Full Stack Engineer, Product Engineer |
| `mobile` | Mobile Engineer | iOS / Android Engineer, React Native, Flutter |
| `devops` | DevOps Engineer | DevOps, SRE, Platform, Cloud / Infrastructure Engineer |
| `data-engineer` | Data Engineer | Data Engineer, Analytics Engineer, Data Platform |
| `data-analyst` | Data Analyst | Data / BI / Product Analyst |
| `ml-engineer` | Machine Learning Engineer | ML / AI Engineer, Data Scientist, Applied Scientist |
| `product-designer` | Product Designer | Product / UX / UI Designer, UX Researcher |
| `product-manager` | Product Manager | Product Manager, Product Owner, Head of Product |

## What a preset contains

Everything under `role:` (see `config.example.yml` for the shared defaults):

| Key | Used for |
|---|---|
| `default_query` | `search_jobs.py --query` default |
| `target_roles` | +20 when a title contains one; fallback when your profile lists no target roles |
| `title_keywords` | company-board scan: a title must contain at least one |
| `title_exclude` | ... and none of these (removes look-alikes such as "Data Quality" for QA) |
| `title_penalties` | role-specific minus points, added to the shared ones (intern, junior, ...) |
| `fallback_skills` | skill weights, used only when `candidate-profile.md` has no Skills section |

## Tuning or adding a preset

- Change a few keys for yourself: put them under `role:` in your `config.yml`; they override the preset.
- New profession: copy the closest preset to `presets/<name>.yml`, edit it, set `preset: <name>`.
  Run `python test_regression.py` and add sample titles for it to the preset test (section 3.10)
  if you open a pull request.
- Titles are matched as whole words (`ml` does not match `HTML`), case-insensitively.
