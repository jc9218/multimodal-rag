import ctypes

import gc

import logging

import resource

logger = logging.getLogger(__name__)


def get_process_memory_mb() -> int:
    """Return the worker's resident set size in megabytes."""

    try:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # On Linux ru_maxrss is in KiB; on macOS it is in bytes.

        return int(usage / 1024) if usage > 1024 else int(usage)

    except Exception:
        return 0


def release_memory() -> None:
    """

    Forces Python garbage collection and returns unused heap arenas back to

    the operating system cgroup via glibc's malloc_trim.

    Crucial for memory-constrained environments such as Render free tier (512MB RAM).

    """

    try:
        gc.collect()

    except Exception:
        pass

    try:
        libc = ctypes.CDLL("libc.so.6")

        libc.malloc_trim(0)

    except Exception:
        pass
