"""Thread-safe token buffer for SSE streaming."""

import queue

_buffers: dict[str, queue.Queue] = {}
_SENTINEL = object()


def get_or_create_buffer(thread_id: str) -> queue.Queue:
    if thread_id not in _buffers:
        _buffers[thread_id] = queue.Queue()
    return _buffers[thread_id]


def push_token_sync(thread_id: str, token: str) -> None:
    buf = get_or_create_buffer(thread_id)
    buf.put(token)


def push_done_sync(thread_id: str) -> None:
    buf = get_or_create_buffer(thread_id)
    buf.put(_SENTINEL)


async def push_token(thread_id: str, token: str) -> None:
    push_token_sync(thread_id, token)


async def push_done(thread_id: str) -> None:
    push_done_sync(thread_id)


def read_tokens_sync(thread_id: str) -> list[str]:
    """Read all currently buffered tokens without blocking."""
    tokens, _ = read_tokens_with_done_sync(thread_id)
    return tokens


def read_tokens_with_done_sync(thread_id: str) -> tuple[list[str], bool]:
    """Read buffered tokens and report whether the stream has ended."""
    buf = get_or_create_buffer(thread_id)
    tokens: list[str] = []
    done = False
    while True:
        try:
            item = buf.get_nowait()
            if item is _SENTINEL:
                done = True
                break
            tokens.append(item)
        except queue.Empty:
            break
    return tokens, done


def is_done(thread_id: str) -> bool:
    """Check whether the stream has ended without consuming queued tokens."""
    buf = get_or_create_buffer(thread_id)
    temp = []
    found_sentinel = False
    while True:
        try:
            item = buf.get_nowait()
            if item is _SENTINEL:
                found_sentinel = True
                temp.append(item)
                break
            temp.append(item)
        except queue.Empty:
            break
    for item in temp:
        buf.put(item)
    return found_sentinel


def cleanup_buffer(thread_id: str) -> None:
    _buffers.pop(thread_id, None)
