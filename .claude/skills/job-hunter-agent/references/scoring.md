# Vacancy rating (1-5) and verdict

Adapted from career-ops (github.com/career-ops-hq/career-ops). The aggregator computes a first
pass automatically (`Job Hunter Agent/aggregator/assessment.py`); you confirm or correct it from the
real posting before the shortlist. Facts about the candidate come only from the profile and playbook.

## Verdict scale
| Rating | Verdict | Meaning |
|---|---|---|
| ≥ 4.0 | **Apply** | Strong fit, no blockers |
| 3.5–3.9 | **Consider** | Fits with gaps; shortlist, say the gap |
| 2.5–3.4 | **Research first** | Unclear location, stack or legitimacy; check before shortlisting |
| < 2.5 or blocker | **Skip** | Do not shortlist |

## Checks per job (short, from the posting text)
1. **Match (B):** must-have skills vs profile years. A must-have the candidate lacks costs 0.5;
   a missing nice-to-have costs nothing.
2. **Level (C):** Senior / Lead / SDET fits. Junior, intern or manual-only costs 1.0+.
3. **Location and work authorization (blocker):**
   - BLOCK when remote is limited to US / Canada / LATAM / APAC / India / etc. residents, or the
     posting requires authorization to work in a country without offering sponsorship.
   - BLOCK on-site or hybrid outside the home country (`location.home_places` in `config.yml`)
     unless the posting offers relocation / sponsorship.
   - Remote EMEA / Europe / worldwide / GMT+0..+4 is fine. "Worldwide" in marketing copy
     ("athletes worldwide") is not a hiring scope; read the location line and eligibility sentence.
   - UK / EU locations: flag "check right to work"; contracts (B2B, outside IR35) may still work.
   - "No visa sponsorship" is only a flag for remote or contract roles, a blocker for relocation.
4. **Compensation (D):** if a range is posted and its top is below the profile minimum (converted
   at today's rate), cost 0.5 and say so.
5. **Legitimacy (G), signals only:** posted > 30 days ago (−0.3), the same title reposted (−0.3),
   a very thin or generic description (−0.2), no company name, or a recruiter asking for payment or
   personal documents up front (Skip). Report signals; don't call a posting fake.
6. **Duplicate:** already in the applications report or the pipeline → Skip ("already applied").

## Output
In the shortlist line: `4.3/5 Apply` plus at most two flags. In the report entry, log the rating,
verdict and any flags next to the status.
