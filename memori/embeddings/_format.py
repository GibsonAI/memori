r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from __future__ import annotations

import json
import struct
from typing import Any


def format_embedding_for_db(embedding: list[float], dialect: str) -> Any:
    if not isinstance(embedding, list):
        raise TypeError(f"embedding must be a list, got {type(embedding).__name__}")

    if not embedding:
        raise ValueError("embedding cannot be empty")

    try:
        binary_data = struct.pack(f"<{len(embedding)}f", *embedding)
    except (struct.error, TypeError) as e:
        raise ValueError(f"embedding values must be numeric floats: {e}") from e

    if dialect == "mongodb":
        try:
            import bson

            return bson.Binary(binary_data)
        except ImportError:
            return binary_data
    if dialect == "oceanbase":
        try:
            from pyobvector.util import Vector

            return Vector._to_db(embedding)
        except Exception:
            return json.dumps(embedding)
    return binary_data
