"""Bounded structural checks, not clean-game authenticity or v1.31 certification."""
import hashlib
import struct
from .recovery import SafetyError, file_id
from .validator import no_links, stable_hash

MANAGED = ('Assembly-CSharp', 'UnityEngine', 'UnityEngine.UI', 'mscorlib',
           'Assembly-CSharp-firstpass', 'System.Xml.Linq', 'System.Core', 'System.Xml', 'System', 'ArabicSupport')

def managed_metadata(raw, name):
    """Validate PE/CLI metadata bounds without loading or executing managed code."""
    try:
        if raw[:2]!=b'MZ':raise ValueError()
        pe=struct.unpack_from('<I',raw,60)[0]
        if raw[pe:pe+4]!=b'PE\0\0':raise ValueError()
        sections=struct.unpack_from('<H',raw,pe+6)[0]
        optional=pe+24;size=struct.unpack_from('<H',raw,pe+20)[0]
        magic=struct.unpack_from('<H',raw,optional)[0]
        if magic not in (0x10b,0x20b) or not 1<=sections<=96:raise ValueError()
        directory=optional+(96 if magic==0x10b else 112)
        if size < directory-optional+15*8:raise ValueError()
        cli,cli_size=struct.unpack_from('<II',raw,directory+14*8)
        def offset(rva,length):
            for i in range(sections):
                section=optional+size+i*40
                _,va,n,ptr=struct.unpack_from('<IIII',raw,section+8)
                if va<=rva and rva-va+length<=n and ptr+rva-va+length<=len(raw):return ptr+rva-va
            raise ValueError()
        if cli_size<72:raise ValueError()
        c=offset(cli,72);metadata,length=struct.unpack_from('<II',raw,c+8)
        m=offset(metadata,length)
        if length<20 or raw[m:m+4]!=b'BSJB':raise ValueError()
        n=struct.unpack_from('<I',raw,m+12)[0]
        if not 1<=n<=256 or 16+n>length:raise ValueError()
        if raw[m+16:m+16+n].rstrip(b'\0')!=b'v2.0.50727':raise ValueError()
        if (name.encode()+b'\0') not in raw[m:m+length]:raise ValueError()
    except (ValueError,struct.error,IndexError):
        raise SafetyError('Unsupported or damaged CLR 2.0 managed dependency: '+name+'.dll')

def dependency_evidence(root,data):
    paths=[data+'/Managed/'+name+'.dll' for name in MANAGED]
    paths += [data+'/Mono/mono.dll',data+'/Mono/etc/mono/config']
    evidence=[];budget=0
    for relative in paths:
        path=root/relative;no_links(path)
        if not path.is_file():raise SafetyError('Missing required game dependency: '+relative)
        stat=path.stat();budget+=stat.st_size
        if not 0<stat.st_size<=64*1024*1024 or budget>128*1024*1024:raise SafetyError('Dependency inspection budget exceeded: '+relative)
        raw=path.read_bytes()
        if '/Managed/' in relative:managed_metadata(raw,path.stem)
        elif relative.endswith('mono.dll'):
            try:
                p=struct.unpack_from('<I',raw,60)[0]
                if raw[:2]!=b'MZ' or raw[p:p+6]!=b'PE\0\0\x64\x86':raise ValueError()
            except (ValueError,struct.error):raise SafetyError('Native x64 Mono runtime required: '+relative)
        sha=hashlib.sha256(raw).hexdigest()
        if stable_hash(path)!=(len(raw),sha) or file_id(path)!=[stat.st_dev,stat.st_ino]:raise SafetyError('Game dependency changed during inspection: '+relative)
        evidence.append(dict(path=relative,size=len(raw),sha256=sha,file_id=[stat.st_dev,stat.st_ino],mtime_ns=stat.st_mtime_ns))
    return evidence
