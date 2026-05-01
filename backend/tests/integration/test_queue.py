"""Integration tests for the queue module."""

import pytest

from taramail.queue import QueueEmpty


async def test_queue_send_receive(queue, unique):
    """Sending a message to a queue should be the next received message."""
    topic = unique("text")
    async with queue.connect(topic) as session:
        await session.publish(topic, "test")
        result = await session.receive(5)
    assert result == "test"


async def test_queue_receive_empty(queue, unique):
    """Receiving from an empty queue should raise a QueueEmpty error."""
    topic = unique("text")
    async with queue.connect(topic) as session:
        with pytest.raises(QueueEmpty):
            await session.receive()
