import asyncio
import concurrent.futures
import time
from unittest.mock import Mock

import pytest

from memori._config import Config
from memori.memory.augmentation._manager import Manager
from memori.memory.augmentation._runtime import AugmentationRuntime, get_runtime


def test_augmentation_runtime_init():
    runtime = AugmentationRuntime()
    assert runtime.loop is None
    assert runtime.thread is None
    assert runtime.semaphore is None
    assert runtime.max_workers == 50


def test_manager_init():
    config = Config()

    manager = Manager(config)
    manager.max_workers = 75

    assert manager.config == config
    assert manager.augmentations is not None
    assert manager.conn_factory is None
    assert manager.max_workers == 75


def test_manager_start_sets_max_workers():
    config = Config()
    mock_conn = Mock()

    manager = Manager(config)
    manager.max_workers = 75
    manager.start(mock_conn)

    runtime = get_runtime()
    assert runtime.max_workers == 75


def test_manager_start_with_none_conn():
    config = Config()
    manager = Manager(config)

    result = manager.start(None)

    assert result == manager
    assert manager.conn_factory is None
    assert manager._active is False


def test_manager_start_with_conn():
    config = Config()
    manager = Manager(config)
    mock_conn = Mock()

    result = manager.start(mock_conn)

    assert result == manager
    assert manager.conn_factory == mock_conn
    assert manager._active is True


def test_manager_enqueue_inactive():
    from memori.memory.augmentation.input import AugmentationInput

    config = Config()
    manager = Manager(config)
    payload = AugmentationInput(
        conversation_id=None, entity_id=None, process_id=None, conversation_messages=[]
    )

    result = manager.enqueue(payload)

    assert result == manager


def test_manager_enqueue_no_conn_factory():
    from memori.memory.augmentation.input import AugmentationInput

    config = Config()
    manager = Manager(config)
    manager._active = True
    payload = AugmentationInput(
        conversation_id=None, entity_id=None, process_id=None, conversation_messages=[]
    )

    result = manager.enqueue(payload)

    assert result == manager


def test_runtime_ensure_started():
    runtime = get_runtime()
    original_thread = runtime.thread

    runtime.ensure_started(50)

    if original_thread is None:
        assert runtime.thread is not None
        time.sleep(0.1)
        assert runtime.loop is not None
        assert runtime.semaphore is not None


@pytest.mark.asyncio
async def test_manager_process_augmentations_no_augmentations():
    from memori.memory.augmentation.input import AugmentationInput

    config = Config()
    manager = Manager(config)
    manager.conn_factory = Mock()
    manager.augmentations = []
    payload = AugmentationInput(
        conversation_id="123", entity_id=None, process_id=None, conversation_messages=[]
    )

    runtime = get_runtime()
    original_semaphore = runtime.semaphore
    runtime.semaphore = asyncio.Semaphore(10)

    try:
        await manager._process_augmentations(payload)
    finally:
        runtime.semaphore = original_semaphore


def test_manager_wait_no_pending_futures():
    config = Config()
    manager = Manager(config)

    result = manager.wait()

    assert result is True


def test_manager_wait_with_completed_futures():
    config = Config()
    manager = Manager(config)
    mock_conn = Mock()
    manager.start(mock_conn)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(lambda: None)
        manager._pending_futures.append(future)
        future.add_done_callback(lambda f: manager._handle_augmentation_result(f))
        time.sleep(0.1)

        result = manager.wait(timeout=1.0)

        assert result is True


def test_manager_wait_with_timeout():
    config = Config()
    manager = Manager(config)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(time.sleep, 2)
        manager._pending_futures.append(future)

        result = manager.wait(timeout=0.1)

        assert result is False
