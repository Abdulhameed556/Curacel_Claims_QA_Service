# Ensure repository root is on sys.path so that the top-level 'src' package can be imported during tests.
import os
import sys

REPO_ROOT = os.path.dirname(__file__)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
