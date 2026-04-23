import os
import tempfile

import pytest

from src.core.config import Config, reset_config


@pytest.fixture
def temp_data_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        data_dir = os.path.join(td, "gf-agent")
        config = Config(data_dir=data_dir)
        config.ensure_dirs()
        yield data_dir
        reset_config()


@pytest.fixture
def config(temp_data_dir):
    return Config(data_dir=temp_data_dir)
