import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# Los tests nunca deben tocar la red ni la cache real del repositorio.
os.environ.pop("POLYGON_API_KEY", None)
os.environ.setdefault("POLYGON_SNAPSHOT_TTL_MIN", "60")
