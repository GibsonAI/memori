from unittest.mock import Mock

from memori.memory.augmentation._db_writer import DbWriterRuntime, WriteTask


class TestWriteTask:
    def test_write_task_execution(self):
        mock_driver = Mock()
        mock_method = Mock(return_value="success")
        mock_driver.conversation.message.create = mock_method

        task = WriteTask(
            method_path="conversation.message.create",
            args=(1, 2),
            kwargs={"key": "value"},
        )

        result = task.execute(mock_driver)

        mock_method.assert_called_once_with(1, 2, key="value")
        assert result == "success"


class TestDbWriterRuntime:
    def test_enqueue_write_success(self):
        import queue as queue_module

        runtime = DbWriterRuntime()
        runtime.queue = queue_module.Queue(maxsize=1000)
        task = WriteTask(method_path="conversation.message.create")

        result = runtime.enqueue_write(task, timeout=1.0)

        assert result is True
        assert runtime.queue.qsize() == 1

    def test_enqueue_write_full_queue(self):
        import queue as queue_module

        runtime = DbWriterRuntime()
        runtime.queue = Mock()
        runtime.queue.put = Mock(side_effect=queue_module.Full("Queue full"))
        runtime.queue.maxsize = 1000

        task = WriteTask(method_path="conversation.message.create")
        result = runtime.enqueue_write(task, timeout=1.0)

        assert result is False
