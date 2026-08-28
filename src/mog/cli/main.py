"""Placeholder entry point.

The real CLI surface is specified in docs/SPEC-cli.md and lands in M1.
"""

import sys

from mog import __version__

_NOTICE = f"""mogestrator {__version__} — planning-phase placeholder.

Nothing is implemented yet. This release exists to reserve the package name
while the design is finalised.

  Design docs: https://github.com/prayag2301/Orchestration/tree/main/docs
  Roadmap:     https://github.com/prayag2301/Orchestration/blob/main/docs/ROADMAP.md
"""


def app() -> int:
    """Print the placeholder notice. Replaced by the real CLI in M1."""
    if "--version" in sys.argv[1:]:
        print(__version__)
        return 0
    print(_NOTICE, file=sys.stderr)
    return 69  # EX_UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(app())
