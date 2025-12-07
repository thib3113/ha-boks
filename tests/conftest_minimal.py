import sys
import asyncio
import pytest

# Force selector policy for Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Attempt to disable socket protection if the plugin is loaded
try:
    from pytest_socket import enable_socket
    def pytest_runtest_setup():
        enable_socket()
except ImportError:
    pass
