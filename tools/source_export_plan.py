"""Print the validated source-only file plan. Does not export files or build a ZIP."""
from pathlib import Path
import json,sys
W=Path(__file__).resolve().parents[1];sys.path[:0]=[str(W/'src'),str(W/'tools')]
from release_config import load_final_config,source_export_plan
if __name__=='__main__':
 cfg=load_final_config(W);rows=source_export_plan(W)
 print(json.dumps({'version':cfg['version'],'mode':'VALIDATION_ONLY','file_count':len(rows),'files':rows,'source_zip_created':False},indent=2))
