"""
Entry point for the 'capsule' CLI command when running from source (without pip install).
Usage: python capsule_cli.py <command> [args]
Or after pip install: capsule <command> [args]
"""
from cli.__main__ import main

if __name__ == "__main__":
    main()
