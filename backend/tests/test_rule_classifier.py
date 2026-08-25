import pytest

from app.services.classification import RuleBasedClassifier
from app.services.classification.normalizer import contains_phrase, normalize


@pytest.fixture
def classifier():
    return RuleBasedClassifier()


# --- Normalizer ---

def test_normalize_strips_case_and_punctuation():
    assert normalize("Villagers need CLEAN Water!") == "villagers need clean water"


def test_contains_phrase_word_boundaries():
    text = normalize("Particles in the air")
    assert contains_phrase(text, "particle") is False
    assert contains_phrase(text, "air") is True


def test_contains_phrase_multiword():
    assert contains_phrase(normalize("No safe drinking water"), "drinking water")


# --- Classification ---

def test_water_challenge_classified(classifier):
    result = classifier.classify(
        title="Village near Barpeta has contaminated drinking water during the summer.",
        description="Residents fetch water from a pond; children fall sick frequently.",
        location="Barpeta, Assam",
    )
    assert result.primary_domain == "water_sanitation"
    assert result.subdomain == "Drinking Water Quality"
    assert result.problem_type is not None
    assert result.geographic_context == "rural"
    assert result.urgency.value == "high"  # "summer"
    assert "Residents" in result.affected_stakeholders
    assert "Children" in result.affected_stakeholders
    assert "Water purification" in result.potential_solution_areas
    assert "Environmental Engineering" in result.required_expertise
    # 3 distinct terms -> exactly the review threshold (see rule_classifier).
    assert result.confidence_score == 0.45
    assert result.signals["water_sanitation"]  # explainable evidence


def test_agriculture_challenge_classified(classifier):
    result = classifier.classify(
        title="Farmers cannot measure soil moisture",
        description="Farmers waste water irrigating crops with no soil data.",
        location="Nashik, Maharashtra",
    )
    assert result.primary_domain == "agriculture"
    assert "Farmers" in result.affected_stakeholders
    assert "IoT soil sensing" in result.potential_solution_areas


def test_multiple_domain_signals_pick_primary_and_secondary(classifier):
    # Strongly water-related, but sewage/disease terms also touch healthcare.
    result = classifier.classify(
        title="Sewage water mixing with drinking water supply",
        description="Contaminated water causing disease outbreak near hospital patients.",
        location="Patna, Bihar",
    )
    assert result.primary_domain in ("water_sanitation", "healthcare")
    assert len(result.secondary_domains) <= 2
    if result.secondary_domains:
        assert result.primary_domain not in result.secondary_domains


def test_unknown_problem_returns_no_domain_and_low_confidence(classifier):
    result = classifier.classify(
        title="Something feels wrong",
        description="The situation in our area is not good at all lately.",
        location="Somewhere",
    )
    assert result.primary_domain is None
    assert result.confidence_score == 0.0
    assert result.keywords == []
    assert result.potential_solution_areas == []


def test_empty_input_is_safe(classifier):
    result = classifier.classify(title="", description="", location="")
    assert result.primary_domain is None
    assert result.confidence_score == 0.0


def test_critical_urgency_detected(classifier):
    result = classifier.classify(
        title="Disease outbreak in village",
        description="An epidemic is spreading and needs immediate attention.",
        location="X",
    )
    assert result.urgency.value == "critical"


def test_classifier_labels_are_honest(classifier):
    result = classifier.classify(
        title="Water problem", description="contaminated wells", location="X"
    )
    assert result.generated_by.value == "deterministic_baseline"
    assert RuleBasedClassifier.VERSION.startswith("rule-baseline-")


def test_classification_is_deterministic(classifier):
    args = (
        "Borewells are failing",
        "Farming families lose crops every summer due to water shortage.",
        "Anantapur",
    )
    first = classifier.classify(*args)
    second = classifier.classify(*args)
    assert first.model_dump() == second.model_dump()


# --- Confidence model (0.15 per distinct matched term, capped at 0.85) ---

def test_confidence_zero_matches(classifier):
    result = classifier.classify(
        title="Something feels wrong",
        description="The situation is not good lately.",
        location="Somewhere",
    )
    assert result.confidence_score == 0.0


def test_confidence_single_weak_match_is_flagged_low(classifier):
    result = classifier.classify(
        title="Soil problem in our area",
        description="The ground quality is bad.",
        location="X",
    )
    assert result.primary_domain == "agriculture"
    assert result.confidence_score == 0.15


def test_confidence_two_matches_still_weak(classifier):
    result = classifier.classify(
        title="Farmers report soil problems",
        description="The situation is getting worse.",
        location="X",
    )
    assert result.primary_domain == "agriculture"
    assert result.confidence_score == 0.3


def test_confidence_three_matches_crosses_review_threshold(classifier):
    result = classifier.classify(
        title="Farmers report soil problems",
        description="Their crops are failing.",
        location="X",
    )
    assert result.primary_domain == "agriculture"
    assert result.confidence_score == 0.45


def test_confidence_strong_multi_signal_problem_caps_at_max(classifier):
    result = classifier.classify(
        title="Contaminated drinking water and broken borewells",
        description=(
            "Water supply failed; sewage contamination affects sanitation "
            "and groundwater quality."
        ),
        location="Barpeta",
    )
    assert result.confidence_score == 0.85
    assert len(result.keywords) >= 5


# --- Domain tie-breaking (no alphabetical bias) ---

def test_equal_score_tie_breaks_by_first_occurrence(classifier):
    # One matched term each; 'school' occurs first -> education must win,
    # even though 'healthcare' sorts after 'education' alphabetically.
    result = classifier.classify(
        title="School and hospital issue",
        description="Reported near the school.",
        location="X",
    )
    assert result.primary_domain == "education"


def test_equal_score_tie_break_follows_input_order(classifier):
    result = classifier.classify(
        title="Hospital and school issue",
        description="Reported near the hospital.",
        location="X",
    )
    assert result.primary_domain == "healthcare"


def test_more_evidence_beats_earlier_occurrence(classifier):
    # Healthcare appears first but education has more matched terms.
    result = classifier.classify(
        title="Clinic reports nearby school dropout crisis",
        description="Students stopped learning; teachers left the classroom.",
        location="X",
    )
    assert result.primary_domain == "education"
