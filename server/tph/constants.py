"""
File holding constants. Do not import non stdlib packages here.
"""
import platform


IS_PYODIDE = platform.system() == "Emscripten"
# prefix for indexeddb files
# FIXME
INDEXEDDB_PREFIX = "2023-"
