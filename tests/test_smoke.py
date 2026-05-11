from __future__ import annotations

import smoke_test


def test_smoke_main() -> None:
    assert smoke_test.main() == 0
