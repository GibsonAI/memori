import pytest

from memori.utils.validators import DataValidator, ValidationError


def test_validator_namespace_with_None():
    assert DataValidator.validate_namespace(None) == "default"


def test_validator_namespace_with_empty_string():
    assert (DataValidator.validate_namespace("")) == "default"


def test_validator_namespace_with_invalid_value():
    with pytest.raises(ValidationError):
        assert DataValidator.validate_namespace(value=2)


def test_validator_namespace_with_valid_value():
    assert DataValidator.validate_namespace("user_data") == "user_data"


def test_validator_namespace_with_long_characters():
    with pytest.raises(ValidationError):
        assert DataValidator.validate_namespace("d" * 78)
