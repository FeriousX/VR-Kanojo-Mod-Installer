"""Read-only component catalog and synthetic planner adapter. No real-target execution API."""
from pathlib import Path
from .validator import safe_relative, stable_hash, no_links, IDENTIFIER, HASH
from .recovery import SyntheticArea, SafetyError, digest, snapshot
from .planner import build_plan
from .release_scope import selection_errors


def catalog_digest(catalog):
    return digest(catalog)


def validate_catalog(catalog):
    if type(catalog) is not dict or catalog.get('schema_version')!=1 or catalog.get('profile')!='real-component-preparation':
        raise SafetyError('unsupported component catalog')
    components=catalog.get('components')
    if type(components) is not list or not 1<=len(components)<=100:
        raise SafetyError('invalid component list')
    ids=set();file_ids=set()
    for c in components:
        if type(c) is not dict or not isinstance(c.get('id'),str) or not IDENTIFIER.fullmatch(c['id']) or c['id'] in ids:
            raise SafetyError('duplicate/invalid component identity')
        ids.add(c['id'])
        if c.get('readiness') not in ('READY','BLOCKED','NEEDS VERIFICATION') or type(c.get('required')) is not bool:
            raise SafetyError('invalid component readiness')
        for key in ('dependencies','conflicts'):
            if type(c.get(key)) is not list or any(not isinstance(v,str) or not IDENTIFIER.fullmatch(v) for v in c[key]):
                raise SafetyError('invalid dependency/conflict list')
        if any(type(c.get(k)) is not dict for k in ('provenance','redistribution')):raise SafetyError('invalid review evidence type')
        if type(c.get('blockers',[])) is not list or any(not isinstance(v,str) for v in c.get('blockers',[])):raise SafetyError('invalid blocker list')
        if type(c.get('files')) is not list or len(c['files'])>10000:raise SafetyError('missing/excessive file mappings')
        for f in c['files']:
            if type(f) is not dict or not isinstance(f.get('id'),str) or f['id'] in file_ids:raise SafetyError('duplicate/missing file ID')
            file_ids.add(f['id']);safe_relative(f['destination'])
            if f.get('staged_source') is not None:safe_relative(f['staged_source'])
            if type(f.get('size')) is not int or f['size']<0 or not isinstance(f.get('sha256'),str) or not HASH.fullmatch(f['sha256']):
                raise SafetyError('invalid file identity')
    for c in components:
        if 'runtime_files' in c:
            if type(c['runtime_files']) is not list or len(c['runtime_files'])>10000:raise SafetyError('invalid runtime file mappings')
            for f in c['runtime_files']:
                if type(f) is not dict:raise SafetyError('invalid runtime file mapping')
                safe_relative(f['destination']);safe_relative(f['staged_source'])
                if type(f.get('size')) is not int or f['size']<0 or not isinstance(f.get('sha256'),str) or not HASH.fullmatch(f['sha256']):raise SafetyError('invalid runtime file identity')
        if any(v not in ids or v==c['id'] for v in c['dependencies']+c['conflicts']):
            raise SafetyError('unknown/self dependency or conflict')
    visited=set()
    def visit(key,chain):
        if key in chain:raise SafetyError('cyclic component dependencies')
        if key in visited:return
        for dep in next(c for c in components if c['id']==key)['dependencies']:visit(dep,chain|{key})
        visited.add(key)
    for key in ids:visit(key,set())
    return {c['id']:c for c in components}


def propose(catalog, staging, selected, *, reviewed_digest=None, reviewed_components=frozenset(), area=None, receipts=(), approvals=()):
    """Inspect a pinned catalog; only a genuine SyntheticArea may supply destinations.

    Review pins express the caller's separate local review, not authenticated vendor
    ownership. Catalog metadata alone never clears provenance/licensing. The existing
    planner is called only for fixture-mapped sources; all execution remains disabled.
    """
    components=validate_catalog(catalog);staging=Path(staging);no_links(staging)
    if type(selected) is not list or any(not isinstance(k,str) for k in selected) or len(set(selected))!=len(selected):
        raise SafetyError('invalid or duplicate selections')
    if any(k not in components for k in selected):raise SafetyError('unknown component selection')
    if type(reviewed_components) is not frozenset:raise SafetyError('review decisions must be a separate immutable set')
    errors=selection_errors(catalog,selected);rows=[];destinations=[]
    if reviewed_digest!=catalog_digest(catalog):errors.append('Catalog has no matching independent review pin; metadata is not authenticated ownership.')
    for c in components.values():
        if c['required'] and c['id'] not in selected:errors.append('Missing required component: '+c['id'])
    for key in selected:
        c=components[key]
        if catalog.get('release_scope') and key not in catalog['release_scope']['included_components']:continue
        for dep in c['dependencies']:
            if dep not in selected:errors.append(key+': missing dependency '+dep)
        for conflict in c['conflicts']:
            if conflict in selected:errors.append(key+': conflicts with '+conflict)
        if c['readiness']!='READY':errors.append(key+': '+c['readiness']+'; '+'; '.join(c.get('blockers',[])))
        if key not in reviewed_components:errors.append(key+': no separate component review approval')
        if c.get('provenance',{}).get('status')!='verified-official-release':errors.append(key+': unverified provenance')
        if c.get('redistribution',{}).get('status')!='permitted-with-obligations':errors.append(key+': redistribution not cleared')
        chosen_files=c.get('runtime_files',c['files'])
        if not chosen_files:errors.append(key+': no file mappings')
        for f in chosen_files:
            dest=safe_relative(f['destination']);fold=dest.casefold()
            if any(fold==p or fold.startswith(p+'/') or p.startswith(fold+'/') for p in destinations):
                errors.append('Conflicting destination: '+dest)
            destinations.append(fold)
            source=f.get('staged_source')
            if source is None:
                errors.append(key+': unstaged file '+f.get('id',f['destination']));continue
            source=safe_relative(source);path=staging/source
            try:
                actual=stable_hash(path)
                if actual!=(f['size'],f['sha256'].lower()):raise SafetyError('unexpected file hash/size')
            except (ValueError,OSError) as exc:
                errors.append(key+': '+source+': '+str(exc));continue
            rows.append({'component':key,'source':source,'destination':dest,'after':{'size':f['size'],'sha256':f['sha256'].lower()},
                         'before':None,'action':'inspect-destination','owner':key})
    result={'schema_version':1,'scope':'read-only-component-proposal','selected':selected,'proposals':rows,'blockers':errors,
            'planner_plan':None,'execution_allowed':False,'real_installation_allowed':False,'ownership_verified':False}
    if area is not None:
        area=SyntheticArea(area.path)
        if staging.absolute()!= (area.path/'payload').absolute():
            errors.append('Planner requires fixture-mapped payload sources; external stages cannot authorize targets.')
        else:
            # Detect both plugins, including nested copies, without loading assemblies.
            plugin_dir=area.target/'BepInEx/plugins'
            if plugin_dir.exists():
                no_links(plugin_dir)
                candidates=[];pending=[plugin_dir]
                while pending:
                    directory=pending.pop();no_links(directory)
                    for p in directory.iterdir():
                        no_links(p);candidates.append(p)
                        if len(candidates)>1000:raise SafetyError('plugin inspection bound exceeded')
                        if p.is_dir():pending.append(p)
                for p in candidates:
                    if p.name.casefold() in ('vrkanojodesktop.dll','vrk_playwithoutvr.dll'):
                        legacy=p.name.casefold()=='vrk_playwithoutvr.dll'
                        conflict='vrkanojo-desktop' if legacy else 'play-without-vr'
                        if conflict in selected:errors.append('Existing conflicting desktop plugin must be preserved pending separate ownership/backup/consent review: '+str(p.relative_to(area.target)))
            requests=[]
            for row in rows:
                try:before=snapshot(area.target/row['destination'])
                except FileNotFoundError:
                    errors.append('Destination parent layout missing; explicit directory preparation is not implemented: '+row['destination'])
                    continue
                row['before']=before
                row['action']='replace' if before['exists'] else 'create'
                requests.append({k:row[k] for k in ('source','destination','action','owner','after')}|{'before':{k:before[k] for k in ('size','sha256')} if before['exists'] else None})
            if not errors:
                try:
                    result['planner_plan']=build_plan(area,requests,list(receipts),list(approvals),dict(profile='synthetic',compatibility=True,licensing=True,provenance=True,mapping=True)).as_dict()
                except (ValueError,OSError) as exc:errors.append('Existing planner refused: '+str(exc))
    result['status']='Blocked' if errors else ('ValidatedSyntheticProposal' if result['planner_plan'] else 'ReviewedCandidatesOnly')
    return result
