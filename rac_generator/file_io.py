from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile


@contextmanager
def atomic_text_file(path: str | Path, *, encoding: str = "utf-8"):
    """Replace a saved file only after its complete new contents reach disk."""
    path = Path(path)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding=encoding, newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            yield handle
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
