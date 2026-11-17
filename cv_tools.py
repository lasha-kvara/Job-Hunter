#!/usr/bin/env python3
"""CV tools: tailor your master CV to a vacancy and render it as a designed PDF and an ATS PDF.

    python cv_tools.py build  spec.json [--pages 1]   tailor + fact-check + both PDFs (the usual command)
    python cv_tools.py tailor spec.json               only the tailored HTML copy (+ fact-check)
    python cv_tools.py check  path/to/CVindex.html    fact-check a tailored copy against the master
    python cv_tools.py master [--pages 1]             PDFs of the master CV itself
    python cv_tools.py designed in.html out.pdf       designed (two-column) PDF of any CV HTML
    python cv_tools.py ats in.html out.pdf [--pages 1]  single-column A4 ATS PDF of any CV HTML

Where things are (config.yml):  cv.dir (folder with the master and tailored/), cv.master (file name,
default CVindex.html), candidate.cv_file_name (name of every generated PDF).
The master HTML uses the class names of cv/master.example.html; copy that template to start.

spec.json (paths relative to cv.dir):
{
  "folder":   "tailored/2026-11-18-acme-backend",        # output folder, created if missing
  "subtitle": "Senior Backend Engineer",                 # optional headline under the name
  "summary":  "...",                                     # optional; numbers must exist in the master
  "skills":   {"Languages": ["Go", "Python"]},           # optional: new order per group (subset of the master)
  "bullets":  {"Acme Corp": [2, 0, 1]},                  # optional: new order of a job's bullets by index
  "tags":     {"Acme Corp": ["Go", "AWS"]}               # optional: new order of a job's tags (subset)
}
Only reorders, removals and a rewritten summary / subtitle are possible, and `check` rejects any
changed employer, title, date, contact, unknown skill or tag, and any number that is not in the master.
"""
import argparse
import html as htmlmod
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Job Hunter Agent"))

from bs4 import BeautifulSoup  # noqa: E402

try:
    from aggregator import settings  # noqa: E402
except Exception:  # settings are optional for the pure functions (tests, other repos)
    settings = None


# ---------------------------------------------------------------- configuration

def cv_settings() -> dict:
    s = settings.get() if settings else {}
    cv = dict(s.get("cv") or {})
    folder = Path(os.path.expandvars(os.path.expanduser(str(cv.get("dir") or "my-cv"))))
    cv["dir"] = folder if folder.is_absolute() else ROOT / folder
    cv["master"] = cv.get("master") or "CVindex.html"
    cv["file_name"] = (s.get("candidate") or {}).get("cv_file_name") or "CV.pdf"
    return cv


def fail(msg: str):
    raise SystemExit(f"cv_tools: {msg}")


# ---------------------------------------------------------------- reading a CV (no browser)

def _t(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ") if el else "").strip()


def extract(html: str) -> dict:
    """Structured content of a CV built from the master template."""
    soup = BeautifulSoup(html, "html.parser")
    sel = lambda root, css: root.select(css)

    def section(label):
        for sec in soup.select(".right-section"):
            if _t(sec.select_one(".section-label")).lower() == label.lower():
                return sec
        return None

    def items(sec):
        return [{
            "title": _t(it.select_one(".tl-title")),
            "period": _t(it.select_one(".tl-period")),
            "company": _t(it.select_one(".tl-company")),
            "bullets": [_t(li) for li in sel(it, ".tl-bullets li")],
            "tags": [_t(t) for t in sel(it, ".tl-tag")],
        } for it in sel(sec, ".tl-item")] if sec else []

    name = _t(soup.select_one(".name")).title()
    return {
        "name": name,
        "subtitle": _t(soup.select_one(".name-subtitle")),
        "contacts": [_t(c) for c in soup.select(".contact-item .contact-text")],
        "summary": _t(soup.select_one(".summary-text")),
        "highlights": [_t(li) for li in soup.select(".summary-highlights li")],
        "skills": [{"label": _t(g.select_one(".skill-group-label")), "items": [_t(b) for b in g.select(".badge")]}
                   for g in soup.select(".skill-group")],
        "competencies": [_t(li) for li in soup.select(".soft-list li")],
        "experience": items(section("Work Experience")),
        "education": items(section("Education")),
        "languages": [f"{_t(r.select_one('.lang-name'))} ({_t(r.select_one('.lang-level'))})" for r in soup.select(".lang-row")],
    }


# ---------------------------------------------------------------- ATS rendering

# Fitting levels (ATS-safe at every level: A4, one column, standard headings, plain text).
# Bullets are cut from the end of each job (tailoring puts the most relevant first); older jobs first.
LEVELS = [
    {"font": 10.5, "lh": 1.38, "margin": 16, "compact": False, "caps": []},
    {"font": 10, "lh": 1.3, "margin": 13, "compact": True, "caps": []},
    {"font": 10, "lh": 1.25, "margin": 12, "compact": True, "caps": [4, 4, 4, 3, 1]},
    {"font": 10, "lh": 1.22, "margin": 12, "compact": True, "caps": [4, 3, 3, 2, 1]},
    {"font": 9.5, "lh": 1.22, "margin": 12, "compact": True, "caps": [3, 3, 3, 2, 0]},
    {"font": 9.5, "lh": 1.2, "margin": 11, "compact": True, "caps": [3, 2, 2, 1, 0]},
    {"font": 9, "lh": 1.2, "margin": 10, "compact": True, "caps": [3, 2, 2, 1, 0]},
]


def render_ats(d: dict, L: dict = LEVELS[0]) -> str:
    esc = lambda s: htmlmod.escape(str(s), quote=False)
    cap = lambda i: L["caps"][i] if 0 <= i < len(L["caps"]) else 10 ** 6

    def job(j, i):
        bullets = j["bullets"][: cap(i)]
        return (
            '<div class="job"><div class="job-head">'
            f'<span class="job-title">{esc(j["title"])}</span><span class="job-period">{esc(j["period"].replace("—", "–"))}</span></div>'
            + (f'<div class="job-company">{esc(j["company"])}</div>' if j["company"] else "")
            + (f'<ul>{"".join(f"<li>{esc(b)}</li>" for b in bullets)}</ul>' if bullets else "")
            + (f'<div class="job-tech">Technologies: {esc(", ".join(j["tags"]))}</div>' if j["tags"] else "")
            + "</div>"
        )

    s = 0.6 if L["compact"] else 1
    font = L["font"]
    highlights = ""
    if d["highlights"]:
        highlights = (f'<p><b>Highlights:</b> {esc("; ".join(d["highlights"]))}</p>' if L["compact"]
                      else f'<ul>{"".join(f"<li>{esc(h)}</li>" for h in d["highlights"])}</ul>')
    skills = "".join(f'<p><b>{esc(g["label"])}:</b> {esc(", ".join(g["items"]))}</p>' for g in d["skills"])
    if d["competencies"]:
        skills += f'<p><b>Competencies:</b> {esc("; ".join(d["competencies"]))}</p>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{esc(d['name'])} – CV</title>
<style>
  @page {{ size: A4; margin: {L['margin']}mm; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: {font}pt; line-height: {L['lh']}; color: #111; margin: 0; }}
  h1 {{ font-size: {18 if L['compact'] else 20}pt; margin: 0; }}
  .headline {{ font-size: {11 if L['compact'] else 12}pt; font-weight: bold; margin: 2px 0 {4 * s}px; }}
  .contact {{ font-size: {min(10, font)}pt; margin-bottom: {6 * s}px; }}
  h2 {{ font-size: {11 if L['compact'] else 11.5}pt; text-transform: uppercase; letter-spacing: .5px; border-bottom: 1px solid #444; margin: {14 * s}px 0 {6 * s}px; padding-bottom: 2px; }}
  p {{ margin: 0 0 {4 * s}px; }}
  ul {{ margin: 2px 0 0 18px; padding: 0; }}
  li {{ margin: 0 0 {2 * s}px; }}
  .skills p {{ margin: 0 0 2px; }}
  .job {{ margin: 0 0 {9 * s}px; page-break-inside: avoid; }}
  .job-head {{ display: flex; justify-content: space-between; gap: 12px; }}
  .job-title {{ font-weight: bold; }}
  .job-period {{ white-space: nowrap; }}
  .job-company {{ font-style: italic; }}
  .job-tech {{ font-size: {max(8.5, font - 1)}pt; margin-top: 2px; }}
</style></head><body>
  <h1>{esc(d['name'])}</h1>
  <div class="headline">{esc(d['subtitle'])}</div>
  <div class="contact">{' | '.join(esc(c) for c in d['contacts'])}</div>
  <h2>Professional Summary</h2>
  <p>{esc(d['summary'])}</p>
  {highlights}
  <h2>Skills</h2>
  <div class="skills">{skills}</div>
  <h2>Work Experience</h2>
  {''.join(job(j, i) for i, j in enumerate(d['experience']))}
  <h2>Education</h2>
  {''.join(job(j, -1) for j in d['education'])}
  {f"<h2>Languages</h2><p>{esc(', '.join(d['languages']))}</p>" if d['languages'] else ''}
</body></html>"""


def count_pdf_pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf))


# ---------------------------------------------------------------- PDFs (Playwright Chromium)

def _browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        fail("Playwright is not installed: pip install -r requirements.txt")
    return sync_playwright()


def designed_pdf(src: Path, out: Path) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    with _browser() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.emulate_media(media="print")
        page.set_viewport_size({"width": 960, "height": 2000})
        page.goto(src.resolve().as_uri(), wait_until="networkidle")
        height = page.evaluate("""() => {
            document.documentElement.style.cssText = 'margin:0;padding:0;overflow:hidden;';
            document.body.style.cssText = 'margin:0;padding:0;display:block;min-height:0;overflow:hidden;';
            const w = document.querySelector('.cv-wrapper');
            w.style.cssText += ';margin:0!important;border-radius:0!important;box-shadow:none!important;min-height:0!important;width:960px!important;';
            void w.offsetHeight; return w.offsetHeight; }""")
        page.set_viewport_size({"width": 960, "height": height})
        page.pdf(path=str(out), width="960px", height=f"{height}px", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    return f"designed PDF: {out} (960 x {height}px)"


def ats_pdf(src: Path, out: Path, max_pages: int = 2) -> str:
    data = extract(src.read_text(encoding="utf-8"))
    if not data["name"] or not data["experience"]:
        fail(f"could not read the name or work experience from {src} (class names as in cv/master.example.html?)")
    out.parent.mkdir(parents=True, exist_ok=True)
    with _browser() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for level, L in enumerate(LEVELS):
            html = render_ats(data, L)
            page.set_content(html, wait_until="load")
            pdf = page.pdf(format="A4", print_background=False, prefer_css_page_size=True)
            pages = count_pdf_pages(pdf)
            if pages <= max_pages:
                break
        browser.close()
    out.write_bytes(pdf)
    out.with_suffix(".html").write_text(html, encoding="utf-8")
    return f"ATS PDF: {out} ({pages} page{'s' if pages > 1 else ''}, fit level {level})"


# ---------------------------------------------------------------- tailoring (reorder / remove only)

def _div_end(html: str, start: int) -> int:
    """Index just after the </div> that closes the <div ...> opening at `start`."""
    depth, i = 0, start
    for m in re.finditer(r"<div\b|</div>", html[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return start + m.end()
    fail("unbalanced <div> in the master CV")


def _job_span(html: str, company: str):
    for m in re.finditer(r'<div class="tl-item">', html):
        end = _div_end(html, m.start())
        block = html[m.start():end]
        comp = re.search(r'<div class="tl-company">(.*?)</div>', block, re.S)
        if comp and re.sub(r"\s+", " ", htmlmod.unescape(comp.group(1))).strip().startswith(company):
            return m.start(), end
    fail(f"job not found: {company}")


def reorder_badges(html: str, label: str, wanted: list) -> str:
    m = re.search(r'(<div class="skill-group-label">' + re.escape(label) + r'</div>\s*<div class="badge-grid">)(.*?)(</div>)', html, re.S)
    if not m:
        fail(f"skill group not found: {label}")
    existing = re.findall(r'<span class="badge">(.*?)</span>', m.group(2))
    for w in wanted:
        if w not in existing:
            fail(f"'{w}' is not in skill group '{label}' (has: {existing})")
    indent = (re.search(r"\n(\s*)<span", m.group(2)) or re.search(r"()", "")).group(1)
    body = "".join(f'\n{indent}<span class="badge">{w}</span>' for w in wanted) + "\n" + indent[:-2]
    return html[: m.start(2)] + body + html[m.end(2):]


def reorder_job(html: str, company: str, order=None, tags=None) -> str:
    start, end = _job_span(html, company)
    block = html[start:end]
    if order is not None:
        ul = re.search(r'(<ul class="tl-bullets">)(.*?)(\s*</ul>)', block, re.S)
        items = re.findall(r"\s*<li>.*?</li>", ul.group(2), re.S)
        for i in order:
            if not 0 <= i < len(items):
                fail(f"bullet index {i} out of range for {company} ({len(items)} bullets)")
        block = block[: ul.start(2)] + "".join(items[i] for i in order) + block[ul.end(2):]
    if tags is not None:
        tg = re.search(r'(<div class="tl-tags">\s*)(.*?)(\s*</div>)', block, re.S)
        existing = re.findall(r'<span class="tl-tag">(.*?)</span>', tg.group(2))
        for t in tags:
            if t not in existing:
                fail(f"tag '{t}' not in {company} (has: {existing})")
        block = block[: tg.start(2)] + "".join(f'<span class="tl-tag">{t}</span>' for t in tags) + block[tg.end(2):]
    return html[:start] + block + html[end:]


def tailor_html(master_html: str, spec: dict, master_dir: Path, out_dir: Path) -> str:
    html = master_html
    # Relative images (photo) must still resolve from the tailored folder.
    def fix_src(m):
        src = m.group(2)
        if re.match(r"^(https?:|data:|/|[A-Za-z]:)", src):
            return m.group(0)
        return m.group(1) + Path(os.path.relpath(master_dir / src, out_dir)).as_posix() + m.group(3)
    html = re.sub(r'(<img[^>]*\bsrc=")([^"]+)(")', fix_src, html)
    if "subtitle" in spec:
        html, n = re.subn(r'(<div class="name-subtitle">).*?(</div>)', lambda m: m.group(1) + htmlmod.escape(spec["subtitle"], quote=False) + m.group(2), html, count=1)
        if not n:
            fail("subtitle (name-subtitle) not found")
    if "summary" in spec:
        html, n = re.subn(r'(<p class="summary-text">\s*).*?(\s*</p>)', lambda m: m.group(1) + htmlmod.escape(spec["summary"], quote=False) + m.group(2), html, count=1, flags=re.S)
        if not n:
            fail("summary (summary-text) not found")
    for label, wanted in (spec.get("skills") or {}).items():
        html = reorder_badges(html, label, wanted)
    for company in set(spec.get("bullets") or {}) | set(spec.get("tags") or {}):
        html = reorder_job(html, company, (spec.get("bullets") or {}).get(company), (spec.get("tags") or {}).get(company))
    return html


# ---------------------------------------------------------------- fact check

NUM_RE = re.compile(r"\d[\d,.]*")


def _numbers(text: str) -> set:
    return {n.rstrip(".,").replace(",", "") for n in NUM_RE.findall(text)}


def fact_check(master_html: str, tailored_html: str, profile_text: str = "") -> tuple:
    """(errors, warnings): what a tailored CV changed compared with the master.
    A skill or tag that is not in the master is accepted with a warning when it is a rename of a
    master item ("Selenium" -> "Selenium WebDriver") or appears in candidate-profile.md."""
    profile_low = profile_text.lower()
    m, t = extract(master_html), extract(tailored_html)
    errors, warnings = [], []
    for key in ("name", "contacts", "languages"):
        if m[key] != t[key]:
            errors.append(f"{key} changed: {t[key]!r} (master: {m[key]!r})")
    jobs = lambda d: [(j["title"], j["period"], j["company"]) for j in d]
    if jobs(m["experience"]) != jobs(t["experience"]):
        errors.append("employers, titles or dates changed in Work Experience")
    if jobs(m["education"]) != jobs(t["education"]):
        errors.append("Education changed")
    master_badges = {b for g in m["skills"] for b in g["items"]}
    master_items = master_badges | {tag for j in m["experience"] for tag in j["tags"]}

    def judge(item, known, where):
        if item in known:
            return
        low = item.lower()
        if any(re.search(r"(?<!\w)" + re.escape(k.lower()) + r"(?!\w)", low) for k in master_items if k):
            warnings.append(f"renamed {where}: {item!r} (check it means the same as the master)")
        elif low in profile_low:
            warnings.append(f"{where} from candidate-profile.md, not the master: {item!r}")
        else:
            errors.append(f"{where} not in the master or the profile: {item!r}")

    for g in t["skills"]:
        for b in g["items"]:
            judge(b, master_badges, "skill")
    by_company = {j["company"]: j for j in m["experience"]}
    for j in t["experience"]:
        mj = by_company.get(j["company"])
        if not mj:
            continue
        for tag in j["tags"]:
            judge(tag, set(mj["tags"]), f"tag ({j['company'][:30]})")
        for b in j["bullets"]:
            if b not in mj["bullets"]:
                warnings.append(f"reworded bullet ({j['company'][:30]}): {b[:80]}")
    master_text = " ".join([m["summary"], m["subtitle"], *m["highlights"],
                            *[b for j in m["experience"] for b in j["bullets"]], *m["competencies"]])
    known = _numbers(master_text)
    new_text = " ".join([t["summary"], t["subtitle"], *t["highlights"], *[b for j in t["experience"] for b in j["bullets"]]])
    for n in sorted(_numbers(new_text) - known):
        errors.append(f"number not in the master: {n}")
    if t["summary"] != m["summary"]:
        warnings.append("summary rewritten: review it against the master")
    return errors, warnings


# ---------------------------------------------------------------- commands

def profile_text() -> str:
    """The candidate's own fact files: a second allowed source for skills (see tailored-cv.md)."""
    parts = []
    for rel in ("Linkedin Agent/candidate-profile.md", "Job Hunter Agent/screening-playbook.md"):
        f = ROOT / rel
        if f.exists():
            parts.append(f.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def cmd_tailor(spec_path: Path, quiet=False) -> Path:
    cv = cv_settings()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    master = cv["dir"] / cv["master"]
    if not master.exists():
        fail(f"master CV not found: {master} (set cv.dir in config.yml or copy cv/master.example.html there)")
    if not spec.get("folder"):
        fail("spec needs a 'folder' (e.g. tailored/2026-11-18-acme-backend)")
    out_dir = cv["dir"] / spec["folder"]
    out_dir.mkdir(parents=True, exist_ok=True)
    master_html = master.read_text(encoding="utf-8")
    html = tailor_html(master_html, spec, master.parent, out_dir)
    errors, warnings = fact_check(master_html, html, profile_text())
    for w in warnings:
        print("  ! " + w)
    if errors:
        fail("fact check failed, nothing written:\n  - " + "\n  - ".join(errors))
    out = out_dir / "CVindex.html"
    out.write_text(html, encoding="utf-8")
    if not quiet:
        print(f"tailored CV: {out}")
    return out


def cmd_check(path: Path) -> int:
    cv = cv_settings()
    master = cv["dir"] / cv["master"]
    errors, warnings = fact_check(master.read_text(encoding="utf-8"), path.read_text(encoding="utf-8"), profile_text())
    for w in warnings:
        print("  ! " + w)
    for e in errors:
        print("  ✗ " + e)
    print("✓ facts match the master" if not errors else "✗ fact check failed")
    return 1 if errors else 0


def cmd_build(spec_path: Path, pages: int) -> None:
    cv = cv_settings()
    html = cmd_tailor(spec_path)
    folder = html.parent
    print(designed_pdf(html, folder / cv["file_name"]))
    print(ats_pdf(html, folder / "ats" / cv["file_name"], pages))


def cmd_master(pages: int) -> None:
    cv = cv_settings()
    master = cv["dir"] / cv["master"]
    print(designed_pdf(master, cv["dir"] / cv["file_name"]))
    print(ats_pdf(master, cv["dir"] / "ats" / cv["file_name"], pages))


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Tailor the master CV and render designed / ATS PDFs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "tailor"):
        p = sub.add_parser(name)
        p.add_argument("spec", type=Path)
        if name == "build":
            p.add_argument("--pages", type=int, default=2)
    sub.add_parser("check").add_argument("html", type=Path)
    sub.add_parser("master").add_argument("--pages", type=int, default=2)
    d = sub.add_parser("designed")
    d.add_argument("src", type=Path)
    d.add_argument("out", type=Path)
    a = sub.add_parser("ats")
    a.add_argument("src", type=Path)
    a.add_argument("out", type=Path)
    a.add_argument("--pages", type=int, default=2)
    args = ap.parse_args(argv)

    if args.cmd == "build":
        cmd_build(args.spec, args.pages)
    elif args.cmd == "tailor":
        cmd_tailor(args.spec)
    elif args.cmd == "check":
        return cmd_check(args.html)
    elif args.cmd == "master":
        cmd_master(args.pages)
    elif args.cmd == "designed":
        print(designed_pdf(args.src, args.out))
    elif args.cmd == "ats":
        print(ats_pdf(args.src, args.out, args.pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
