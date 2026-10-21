from types import SimpleNamespace

from memori.llm.invoke.iterator import Iterator as MemoriIterator
from memori.llm.pipelines import post_invoke


def _payload():
    return {
        "messages": [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "text": "hi there"},
        ]
    }


def test_run_post_invoke_augments_memory_when_configured(mocker):
    augmentation = object()
    config = SimpleNamespace(
        augmentation=augmentation,
        entity_id=1,
        process_id=2,
        session_id="session-1",
    )
    invoke = SimpleNamespace(config=config)
    payload = _payload()

    execute = mocker.patch("memori.memory._manager.Manager.execute")
    handle = mocker.patch("memori.memory.augmentation._handler.handle_augmentation")

    post_invoke.run_post_invoke(invoke, {"model": "gpt-4o"}, payload)

    execute.assert_called_once_with(payload)
    handle.assert_called_once()
    kwargs = handle.call_args.kwargs
    assert kwargs["config"] is config
    assert kwargs["augmentation_manager"] is augmentation
    assert kwargs["kwargs"] == {"model": "gpt-4o"}
    assert [m.role for m in kwargs["payload"].messages] == ["user", "assistant"]


def test_run_post_invoke_skips_augmentation_when_disabled(mocker):
    config = SimpleNamespace(
        augmentation=None,
        entity_id=1,
        process_id=2,
        session_id="session-1",
    )
    invoke = SimpleNamespace(config=config)
    payload = _payload()

    execute = mocker.patch("memori.memory._manager.Manager.execute")
    handle = mocker.patch("memori.memory.augmentation._handler.handle_augmentation")

    post_invoke.run_post_invoke(invoke, {}, payload)

    execute.assert_called_once_with(payload)
    handle.assert_not_called()


def test_streaming_iterator_augments_when_exhausted(mocker):
    config = SimpleNamespace(
        framework=SimpleNamespace(provider="openai"),
        llm=SimpleNamespace(provider="openai", version="gpt-4o"),
        augmentation=object(),
    )
    invoke = SimpleNamespace(
        config=config, _uses_protobuf=False, _injected_message_count=0
    )

    mocker.patch("memori.llm.invoke.iterator.format_payload", return_value=_payload())
    run_post_invoke = mocker.patch("memori.llm.invoke.iterator.run_post_invoke")

    iterator = (
        MemoriIterator(config, iter(()))
        .configure_invoke(invoke)
        .configure_request({}, 0)
    )
    assert list(iterator) == []

    run_post_invoke.assert_called_once()
    assert run_post_invoke.call_args.args[0] is invoke
    assert run_post_invoke.call_args.args[1] == {}
    assert run_post_invoke.call_args.args[2] == _payload()
