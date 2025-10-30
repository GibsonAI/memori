import sys
from pathlib import Path

import pytest

# Add the root project folder to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from memori.core.memory import Memori


def test_conscious_memory_limit_valid_values():
    """Valid conscious_memory_limit values should not raise errors"""
    try:
        Memori(conscious_memory_limit=1)
        Memori(conscious_memory_limit=500)
        Memori(conscious_memory_limit=1500)
        Memori(conscious_memory_limit=2000)
    except Exception as e:
        pytest.fail(f"Unexpected exception raised: {e}")


def test_conscious_memory_limit_invalid_low():
    """Values below 1 should raise ValueError"""
    with pytest.raises(ValueError):
        Memori(conscious_memory_limit=0)


def test_conscious_memory_limit_invalid_high():
    """Values above 2000 should raise ValueError"""
    with pytest.raises(ValueError):
        Memori(conscious_memory_limit=3000)


@pytest.mark.parametrize("invalid_value", ["high", 3.14, None, True, False])
def test_conscious_memory_limit_invalid_types(invalid_value):
    """Non-integer or boolean types should raise TypeError"""
    with pytest.raises(TypeError):
        Memori(conscious_memory_limit=invalid_value)
