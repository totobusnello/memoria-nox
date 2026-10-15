import importlib.util
import os

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "analyze.py")
_spec = importlib.util.spec_from_file_location("analyze", _p)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
unit_deltas, decide = _mod.unit_deltas, _mod.decide
