from datetime import datetime
from pathlib import Path

import pytest

from eventradar.model import TAIPEI

FIXTURES = Path(__file__).parent / "fixtures"

# 測試資料抓取時間為 2026-10-19 17:51，固定「現在」讓結果可重現
NOW = datetime(2026, 10, 19, 18, 0, tzinfo=TAIPEI)


@pytest.fixture
def now():
    return NOW


@pytest.fixture
def fixture_bytes():
    return lambda name: (FIXTURES / name).read_bytes()
