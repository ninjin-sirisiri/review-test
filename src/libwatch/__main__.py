from __future__ import annotations

import sys

from libwatch.build import build_main
from libwatch.serve import serve_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return build_main()
    if args[0] == "serve":
        return serve_main(args[1:])
    print(f"unknown command: {args[0]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
