"""Unit tests for Layer 2: Behavioral & NLP Intent Extraction."""

from app.models.scan import SourceType
from app.pipeline.layer0_normalization import NormalizedData
from app.pipeline.layer2_behavioral import evaluate_layer2


def test_urgency_detection_and_span_offsets():
    """Verify urgency pattern detection and character span offset precision."""
    sample_text = "Dear user, immediate action is required to avoid account deactivation."
    norm = NormalizedData(
        source_type=SourceType.EMAIL,
        raw_input=sample_text,
        cleaned_text=sample_text,
    )
    evidence = evaluate_layer2(norm)
    urgency_items = [e for e in evidence if e.type == "urgency"]
    assert len(urgency_items) >= 1

    # Verify exact character span matching
    item = urgency_items[0]
    assert item.span_start is not None and item.span_end is not None
    extracted_slice = sample_text[item.span_start : item.span_end]
    assert extracted_slice.lower() == item.raw_match.lower()


def test_fear_and_authority_detection():
    """Verify authority impersonation and threat inducement detection."""
    sample_text = "Message from the Security Team: unauthorized access was detected from a foreign IP."
    norm = NormalizedData(
        source_type=SourceType.EMAIL,
        raw_input=sample_text,
        cleaned_text=sample_text,
    )
    evidence = evaluate_layer2(norm)
    types = {e.type for e in evidence}
    assert "authority" in types
    assert "fear" in types


def test_greed_detection():
    """Verify financial bait and reward patterns."""
    sample_text = "Congratulations, you have won an exclusive payout. Claim your prize immediately."
    norm = NormalizedData(
        source_type=SourceType.EMAIL,
        raw_input=sample_text,
        cleaned_text=sample_text,
    )
    evidence = evaluate_layer2(norm)
    greed_items = [e for e in evidence if e.type == "greed"]
    assert len(greed_items) >= 1
