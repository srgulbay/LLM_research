import sys
import os

# Ensure project root is on sys.path so tests can import top-level modules like `app`.
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)
