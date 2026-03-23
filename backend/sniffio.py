from contextvars import ContextVar


class AsyncLibraryNotFoundError(RuntimeError):
    pass


current_async_library_cvar: ContextVar[str | None] = ContextVar('current_async_library_cvar', default=None)


def current_async_library() -> str:
    value = current_async_library_cvar.get()
    if value is not None:
        return value

    try:
        import asyncio

        asyncio.get_running_loop()
        return 'asyncio'
    except RuntimeError as exc:
        raise AsyncLibraryNotFoundError() from exc
