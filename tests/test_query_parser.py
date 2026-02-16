"""Unit tests for the deterministic query parser."""

from app.services.query_parser import parse_query


class TestOrthodonticsKeywords:
    """Orthodontics/braces queries must map to dental/orthodontics."""

    def test_orthodontic_treatment(self):
        result = parse_query("orthodontic treatment")
        assert result.benefit_type == "dental"
        assert result.service_category == "orthodontics"

    def test_braces(self):
        result = parse_query("braces")
        assert result.benefit_type == "dental"
        assert result.service_category == "orthodontics"

    def test_invisalign(self):
        result = parse_query("invisalign")
        assert result.benefit_type == "dental"
        assert result.service_category == "orthodontics"

    def test_orthodontics_not_preventive(self):
        """Orthodontics must NOT fall through to preventive_dental."""
        result = parse_query("Is orthodontic treatment covered for me?")
        assert result.service_category == "orthodontics"
        assert result.service_category != "preventive_dental"

    def test_braces_not_preventive(self):
        result = parse_query("Is braces covered for me?")
        assert result.service_category == "orthodontics"
        assert result.service_category != "preventive_dental"


class TestMajorDentalKeywords:
    """Crown/bridge/bridges must map to dental/major_dental per CL-031."""

    def test_crown(self):
        result = parse_query("crown")
        assert result.benefit_type == "dental"
        assert result.service_category == "major_dental"

    def test_crown_treatment(self):
        result = parse_query("crown treatment")
        assert result.benefit_type == "dental"
        assert result.service_category == "major_dental"

    def test_crowns(self):
        result = parse_query("crowns")
        assert result.benefit_type == "dental"
        assert result.service_category == "major_dental"

    def test_bridge(self):
        result = parse_query("bridge")
        assert result.benefit_type == "dental"
        assert result.service_category == "major_dental"

    def test_bridges(self):
        result = parse_query("bridges")
        assert result.benefit_type == "dental"
        assert result.service_category == "major_dental"

    def test_crown_not_restorative(self):
        """Crown must NOT map to restorative_dental (CL-031: crowns are Major)."""
        result = parse_query("I need a crown")
        assert result.service_category == "major_dental"
        assert result.service_category != "restorative_dental"

    def test_bridge_not_restorative(self):
        """Bridge must NOT map to restorative_dental (CL-031: bridges are Major)."""
        result = parse_query("I need a bridge")
        assert result.service_category == "major_dental"
        assert result.service_category != "restorative_dental"


class TestServiceKeywordPriority:
    """Service-specific keywords should be checked before benefit-level."""

    def test_dental_cleaning_is_preventive(self):
        result = parse_query("dental cleaning")
        assert result.benefit_type == "dental"
        assert result.service_category == "preventive_dental"

    def test_root_canal(self):
        result = parse_query("root canal treatment")
        assert result.benefit_type == "dental"
        assert result.service_category == "root_canal"

    def test_mri(self):
        result = parse_query("I need an MRI")
        assert result.benefit_type == "outpatient"
        assert result.service_category == "diagnostic_imaging"

    def test_therapy(self):
        result = parse_query("therapy session")
        assert result.benefit_type == "mental_health"
        assert result.service_category == "therapy_session"
