"""Same versioned GUI transport, connected to the real-component fixture preparer."""
import gui_install as gui
from hf_payload import real_file_bridge

def main():
 old_bridge,old_request=gui.bridge,gui.request_for
 gui.bridge,gui.request_for=real_file_bridge,real_file_bridge.request_for
 try:return gui.main()
 finally:gui.bridge,gui.request_for=old_bridge,old_request
if __name__=='__main__':raise SystemExit(main())
