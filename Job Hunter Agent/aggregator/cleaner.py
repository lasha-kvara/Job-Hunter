import re
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from typing import List, Set, Tuple
from .models import JobPost


TRACKING_PARAMS = {
    # Standard UTM
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    # LinkedIn
    "refid", "trackingid", "midsig", "eid", "trk", "tracking_id", "originalsubdomain",
    "position", "pagenum", "start",
    # Greenhouse / Lever / Workday
    "gh_src", "source", "ref", "lever-source", "lever-origin",
    # Ad trackers
    "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "_hsenc", "_hsmi",
    "vero_id", "vero_conv", "nr_email_referer", "rb_clickid", "s_cid", "mkt_tok",
    "twclid", "yclid", "igshid", "spjobid", "spreportid",
}



def clean_job_url(raw_url: str) -> str:
    """
    Strips tracking query parameters and extracts canonical job URLs.
    """
    if not raw_url:
        return ""

    try:
        parsed = urlparse(raw_url)
        # Check for LinkedIn view url
        if "linkedin.com" in parsed.netloc:
            # Check if /jobs/view/<job_id>
            match = re.search(r'/jobs/view/(\d+)', parsed.path)
            if match:
                return f"https://www.linkedin.com/jobs/view/{match.group(1)}/"
            # Check currentJobId param
            qs = parse_qs(parsed.query)
            if "currentJobId" in qs:
                return f"https://www.linkedin.com/jobs/view/{qs['currentJobId'][0]}/"

        # Check for Indeed viewjob url
        if "indeed.com" in parsed.netloc:
            qs = parse_qs(parsed.query)
            if "jk" in qs:
                return f"https://www.indeed.com/viewjob?jk={qs['jk'][0]}"

        # Standard param filtering
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {
            k: v for k, v in qs.items()
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
        }
        
        # Rebuild query
        new_query = urlencode(clean_qs, doseq=True)
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            ""  # drop fragment
        ))
        return clean_url
    except Exception:
        return raw_url


def normalize_string(text: str) -> str:
    """Normalize company name or title for fuzzy deduplication."""
    if not text:
        return ""
    # Lowercase
    t = text.lower()
    # Common abbreviations
    t = re.sub(r'\binc\.?|\bllc\.?|\bltd\.?|\bcorp\.?|\bco\.?|\bgmbh\b', '', t)
    t = re.sub(r'\bsr\.?\b', 'senior', t)
    t = re.sub(r'\bjr\.?\b', 'junior', t)
    t = re.sub(r'\bqa\b', 'quality assurance', t)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return " ".join(t.split())


def deduplicate_jobs(jobs: List[JobPost]) -> List[JobPost]:
    """
    Deduplicates job postings based on:
    1. Canonical URL
    2. Normalized (company + title) signature
    """
    seen_urls: Set[str] = set()
    seen_signatures: Set[str] = set()
    unique_jobs: List[JobPost] = []

    for job in jobs:
        # 1. Clean URL
        canonical_url = clean_job_url(job.job_url)
        job.job_url = canonical_url

        if canonical_url and canonical_url in seen_urls:
            continue

        # 2. Normalized signature including location to prevent dropping distinct openings across offices/regions
        norm_company = normalize_string(job.company)
        norm_title = normalize_string(job.title)
        norm_location = normalize_string(job.location)
        signature = f"{norm_company}___{norm_title}___{norm_location}"

        if signature in seen_signatures and norm_company != "":
            continue

        if canonical_url:
            seen_urls.add(canonical_url)
        if norm_company:
            seen_signatures.add(signature)


        unique_jobs.append(job)

    return unique_jobs
