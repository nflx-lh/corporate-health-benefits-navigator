"""Deterministic query parser – keyword mapping for benefit type and service category."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Keyword maps – single source of truth
# ---------------------------------------------------------------------------

# Maps lowercased keywords/phrases -> (benefit_type, service_category | None)
# More specific entries (with service_category) are checked first.
SERVICE_KEYWORDS: list[tuple[list[str], str, str]] = [
    # dental service categories
    (["orthodontic", "orthodontics", "braces", "invisalign"], "dental", "orthodontics"),
    (["root canal", "root_canal", "endodontic"], "dental", "root_canal"),
    (["crown", "bridge", "filling", "restoration", "restorative"], "dental", "restorative_dental"),
    (["cosmetic dentistry", "cosmetic dental", "teeth whitening", "veneer"], "dental", "cosmetic_dental"),
    (["major dental", "wisdom tooth", "extraction", "dental surgery"], "dental", "major_dental"),
    (["cleaning", "scaling", "polishing", "checkup dental", "dental checkup", "preventive dental"], "dental", "preventive_dental"),
    # outpatient service categories
    (["mri", "ct scan", "x-ray", "xray", "ultrasound", "diagnostic imaging", "radiology"], "outpatient", "diagnostic_imaging"),
    (["day surgery", "day_surgery", "minor surgery"], "outpatient", "day_surgery"),
    (["specialist", "specialist consult", "referral"], "outpatient", "specialist_consult"),
    (["cosmetic", "elective", "cosmetic procedure", "cosmetic surgery"], "outpatient", "cosmetic_procedure"),
    (["experimental", "experimental treatment", "clinical trial"], "outpatient", "experimental_treatment"),
    # mental health service categories
    (["couples counseling", "couples therapy", "marriage counseling"], "mental_health", "couples_counseling"),
    (["intensive therapy", "intensive counseling", "psychiatric"], "mental_health", "intensive_therapy"),
    (["therapy", "therapist", "counseling", "counselor", "psychologist", "therapy session"], "mental_health", "therapy_session"),
    # mental health benefit-level
    (["mental health", "mental_health", "mental wellness"], "mental_health", "therapy_session"),
]

BENEFIT_KEYWORDS: list[tuple[list[str], str]] = [
    (["dental", "dentist", "tooth", "teeth"], "dental"),
    (["mental", "therapy", "counseling", "psycholog", "psychiatr"], "mental_health"),
    (["outpatient", "clinic", "gp", "general practitioner", "doctor", "consult", "checkup", "check-up", "medical"], "outpatient"),
]


@dataclass
class ParsedQuery:
    benefit_type: Optional[str] = None
    service_category: Optional[str] = None


def parse_query(query: str) -> ParsedQuery:
    """Extract benefit_type and service_category from free-text query."""
    q = query.lower().strip()

    # 1) Try service-specific keywords first (more specific match)
    for keywords, b_type, s_cat in SERVICE_KEYWORDS:
        for kw in keywords:
            if kw in q:
                return ParsedQuery(benefit_type=b_type, service_category=s_cat)

    # 2) Fall back to broad benefit-type keywords
    for keywords, b_type in BENEFIT_KEYWORDS:
        for kw in keywords:
            if kw in q:
                return ParsedQuery(benefit_type=b_type, service_category=None)

    # 3) Nothing matched
    return ParsedQuery(benefit_type=None, service_category=None)
