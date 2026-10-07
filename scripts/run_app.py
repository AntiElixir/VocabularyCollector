"""PyInstaller entry script: imports the package so relative imports work."""

from vocab_collector.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())