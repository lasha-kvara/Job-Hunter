import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class JobPost:
    """Standardized job posting representation across all platforms."""
    title: str
    company: str
    job_url: str
    source: str
    location: str = ""
    date_posted: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[str] = "yearly"
    job_type: Optional[str] = None
    is_remote: bool = False
    description: str = ""
    fit_score: int = 0
    fit_reasons: List[str] = field(default_factory=list)
    fit_grade: str = ""
    applied: bool = False
    id: str = ""

    def __post_init__(self):
        if not self.id:
            # Generate deterministic content hash from canonical company + title
            key = f"{self.company.lower().strip()}||{self.title.lower().strip()}"
            self.id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]

    @property
    def salary_str(self) -> str:
        """Format salary range nicely."""
        if not self.salary_min and not self.salary_max:
            return "Not specified"
        cur = self.salary_currency or "$"
        period = f" / {self.salary_period}" if self.salary_period else ""
        if self.salary_min and self.salary_max:
            if self.salary_min == self.salary_max:
                return f"{cur}{self.salary_min:,.0f}{period}"
            return f"{cur}{self.salary_min:,.0f} - {cur}{self.salary_max:,.0f}{period}"
        elif self.salary_min:
            return f"From {cur}{self.salary_min:,.0f}{period}"
        elif self.salary_max:
            return f"Up to {cur}{self.salary_max:,.0f}{period}"
        return "Not specified"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["salary_str"] = self.salary_str
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobPost":
        """Instantiate from dictionary."""
        clean_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**clean_data)
