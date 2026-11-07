"""Exact official-native provenance gate; never deletes or substitutes collected DLLs."""
import hashlib,json,zipfile
from pathlib import Path

def qualify(backend, archive, provenance, report):
    backend,archive,provenance,report=map(Path,(backend,archive,provenance,report))
    evidence=json.loads(provenance.read_text(encoding='utf-8-sig'))
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=evidence['source_sha256']:
        raise ValueError('Official runtime archive identity changed')
    approved={row['path'].casefold():row for row in evidence['native_files']}
    good=[];bad=[]
    with zipfile.ZipFile(archive) as z:
        names={n.casefold():n for n in z.namelist()}
        for p in sorted((backend/'_internal').rglob('*')):
            if not p.is_file() or p.suffix.lower() not in ('.dll','.pyd'):continue
            raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest();name=p.name.casefold()
            row=dict(name=p.name,path=p.relative_to(backend).as_posix(),size=len(raw),sha256=sha)
            if name not in names or name not in approved or raw!=z.read(names[name]) or sha!=approved[name]['sha256']:
                bad.append(row)
            else:good.append(row)
    missing=sorted(set(approved)-{r['name'].casefold() for r in good})
    result=dict(status='PASS' if good and not bad and not missing else 'BLOCKED',matched=good,unexpected=bad,missing=missing,archive_sha256=evidence['source_sha256'])
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if result['status']!='PASS':raise ValueError('Native runtime qualification failed; see '+str(report))
    return result
