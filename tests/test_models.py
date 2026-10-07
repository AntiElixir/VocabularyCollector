import pytest
from pydantic import ValidationError

from vocab_collector.models import VocabResult


def test_valid_dict_validates():
    result = VocabResult.model_validate(
        {"english": "robustness", "chinese": "稳健性", "domain": "AI"}
    )
    assert result.english == "robustness"
    assert result.chinese == "稳健性"
    assert result.domain == "AI"


def test_values_are_stripped():
    result = VocabResult(english="  x ", chinese=" y  ", domain=" z ")
    assert (result.english, result.chinese, result.domain) == ("x", "y", "z")


@pytest.mark.parametrize("field", ["english", "chinese", "domain"])
def test_whitespace_only_field_rejected(field):
    data = {"english": "a", "chinese": "b", "domain": "c"}
    data[field] = "   "
    with pytest.raises(ValidationError):
        VocabResult.model_validate(data)


def test_extra_key_rejected():
    with pytest.raises(ValidationError):
        VocabResult.model_validate(
            {"english": "a", "chinese": "b", "domain": "c", "extra": "d"}
        )


def test_json_round_trip():
    result = VocabResult.model_validate_json(
        '{"english":"a","chinese":"b","domain":"c"}'
    )
    assert result.domain == "c"