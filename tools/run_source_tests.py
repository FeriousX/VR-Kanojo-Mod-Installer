from pathlib import Path
import sys,unittest
w=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(w/'tests'),str(w/'src'),str(w/'tools')]
suite=unittest.TestSuite()
for name in ('test_planner','test_single_packaging','test_gui_install','test_gui_polish'):
 sys.path[:]=[str(w/'tests'),str(w/'src'),str(w/'tools')]+[p for p in sys.path if p not in (str(w/'tests'),str(w/'src'),str(w/'tools'))]
 suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
r=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not r.wasSuccessful())
