"""Test-only entry point. Not compiled into the delivered installer."""
import os,sys
import portable_backend

def main():
 if sys.argv[1:2]!=['qual-fault']:return portable_backend.main()
 from hf_payload.runtime_paths import initialize_portable
 initialize_portable()
 import gui_install as gui
 from hf_payload import private_game_bridge as bridge
 job,digest,point=sys.argv[2:]
 gui.bridge,gui.request_for,gui.TRANSPORT_SCOPE,gui.REAL_ALLOWED=bridge,bridge.request_for,'private-game-gui-v1','1'
 def fault(at,index):
  if at==point:os._exit(87)
 gui.run_job(job,digest,extra_fault=fault)
 return 0
if __name__=='__main__':sys.exit(main())
