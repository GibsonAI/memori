r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import os
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version


class Cache:
    def __init__(self):
        self.conversation_id = None
        self.entity_id = None
        self.process_id = None
        self.session_id = None


class Storage:
    def __init__(self):
        self.cockroachdb = False


class Embeddings:
    def __init__(self):
        self.model = "all-MiniLM-L6-v2"
        self.fallback_dimension = 768


class Config:
    def __init__(self):
        self.api_key = None
        self.augmentation = None
        self.cache = Cache()
        self.debug_truncate = True  # Truncate long content in debug logs
        self.embeddings = Embeddings()
        self.enterprise = False
        self.llm = Llm()
        self.framework = Framework()
        self.platform = Platform()
        self.entity_id = None
        self.process_id = None
        self.raise_final_request_attempt = True
        self.recall_embeddings_limit = 1000
        self.recall_facts_limit = 5
        self.recall_relevance_threshold = 0.1
        self.request_backoff_factor = 1
        self.request_num_backoff = 5
        self.request_secs_timeout = 5
        self.session_id = None
        self.session_timeout_minutes = 30
        self.storage = None
        self.storage_config = Storage()
        self.thread_pool_executor = ThreadPoolExecutor(max_workers=15)
        self.version = version("memori")

    def is_test_mode(self):
        return os.environ.get("MEMORI_TEST_MODE", None) is not None

    def reset_cache(self):
        self.cache = Cache()
        return self


class Framework:
    def __init__(self):
        self.provider = None


class Platform:
    def __init__(self):
        self.provider = None


class Llm:
    def __init__(self):
        self.provider = None
        self.provider_sdk_version = None
        self.version = None
