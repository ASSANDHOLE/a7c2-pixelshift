import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
if __name__=="__main__":
 from a7c2_persistent import main
 try:raise SystemExit(main())
 except (Exception,KeyboardInterrupt) as e:
  print("STOPPED:",type(e).__name__+": "+str(e),file=sys.stderr);raise SystemExit(2)
