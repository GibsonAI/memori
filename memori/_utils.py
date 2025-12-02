r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import hashlib
import json
import re


def bytes_to_json(obj):
    if isinstance(obj, bytes):
        obj = obj.decode()

        if not isinstance(obj, str):
            return obj

        try:
            return json.loads(obj)
        except json.JSONDecodeError:
            return obj
    elif isinstance(obj, dict):
        return {bytes_to_json(k): bytes_to_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [bytes_to_json(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(bytes_to_json(i) for i in obj)
    elif isinstance(obj, set):
        return {bytes_to_json(i) for i in obj}
    else:
        if not isinstance(obj, str):
            return obj

        try:
            return json.loads(obj)
        except json.JSONDecodeError:
            return obj


def generate_uniq(terms: list):
    if terms is None or len(terms) == 0:
        return None

    sha256 = hashlib.sha256()
    sha256.update(re.sub(r"[^a-z0-9]", "", "".join(terms).lower()).encode("utf-8"))

    return sha256.hexdigest()


def merge_chunk(data: dict, chunk: dict):
    for key, chunk_value in chunk.items():
        if key in data:
            data_value = data[key]

            if isinstance(data_value, list) and isinstance(chunk_value, list):
                data[key].extend(chunk_value)
            elif isinstance(data_value, dict) and isinstance(chunk_value, dict):
                merge_chunk(data_value, chunk_value)
            else:
                data[key] = chunk_value
        else:
            data[key] = chunk_value

    return data
