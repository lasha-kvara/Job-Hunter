# Job sources

| Source (`--sources`) | How | Notes |
|---|---|---|
| `ats` | public APIs of Greenhouse, Ashby, Lever (US + EU), SmartRecruiters, Recruitee | ~200 company boards, full posting text, no login, no CAPTCHA, ~30 s |
| `linkedin`, `indeed`, `glassdoor`, `zip_recruiter`, `google` | [python-jobspy](https://pypi.org/project/python-jobspy/) | broad reach; LinkedIn ignores its own Remote filter, so the agent re-checks the job page |
| `jobs_ge` | jobs.ge IT category (Georgia) | example of a local job site provider |

In Claude Code the agent can also browse any other site live (recruiter.ge, company career pages).

## Adding company boards (no code)

Find the board in the company's "Apply" link, then add the token to
`Job Hunter Agent/ats-boards.local.json` (yours, git-ignored) or, for a pull request, to
`ats-boards.json`:

| ATS | URL looks like | Token | Key |
|---|---|---|---|
| Greenhouse | `boards.greenhouse.io/acme`, `job-boards.eu.greenhouse.io/acme` | `acme` | `greenhouse` |
| Ashby | `jobs.ashbyhq.com/acme` | `acme` (case-sensitive) | `ashby` |
| Lever | `jobs.lever.co/acme` / `jobs.eu.lever.co/acme` | `acme` | `lever` / `lever_eu` |
| SmartRecruiters | `jobs.smartrecruiters.com/Acme` | `Acme` | `smartrecruiters` |
| Recruitee | `acme.recruitee.com` | `acme` | `recruitee` |

```json
{
  "greenhouse": ["acme"],
  "ashby": ["SomeStartup"],
  "lever": [], "lever_eu": [], "smartrecruiters": [], "recruitee": []
}
```

Check it answers: `python search_jobs.py --sources ats --min-score 0`. Boards that fail are listed
as "did not answer" in the output. Workday, Workable and custom career sites have no usable public
API; the agent handles them in the browser.

## Adding a new source (code)

1. Create `Job Hunter Agent/aggregator/sources/<name>_provider.py` with a class whose `search(...)`
   returns a list of `JobPost` (see `models.py`). Fill `title`, `company`, `job_url`, `source`,
   `location`, `date_posted` (ISO), `is_remote` and as much `description` as you can.
2. Register it in `engine.py` (`AggregatorEngine.search`) and in the `--sources` choices of
   `search_jobs.py`.
3. Add a mocked test in `test_regression.py` (no network in tests).

Deduplication, scoring, the 1–5 rating, blockers and the duplicate check against your report run
automatically on whatever the provider returns.
