"""Bounded read-only game inspection. Never loads game code or authorizes installation."""
import os
from pathlib import Path
import re
import stat
import struct
from .validator import no_links, safe_relative, stable_hash, linked
from .recovery import SafetyError, digest, shape, SyntheticArea
from .planner import build_plan

LAYOUTS = [('VR_Kanojo.exe', 'VR_Kanojo_Data'), ('VRKanojo.exe', 'VRKanojo_Data')]
MAX_BYTES = 128 * 1024 * 1024
MAX_FILES = 1000


def validation_message(status):
    return {
        'supported': 'Game fingerprint verified. Installation still requires approved mappings, ownership and consent.',
        'recognized-unverified': 'Original-game layout recognized; build/version is unverified. Keep files unchanged and obtain an approved profile.',
        'unsupported': 'This selection does not match a supported original-game identity. Do not rename files to bypass validation.',
        'ambiguous': 'Conflicting layouts or profiles detected. Select one unambiguous executable/data pair.',
        'incomplete': 'Required files are missing, unreadable or unsafe. Select the folder containing the executable and its matching Data folder.'
    }[status]


def desktop_compatibility(detection, selection='neither'):
    names = {'vrkanojo-desktop': 'vrkanojodesktop.dll', 'play-without-vr': 'vrk_playwithoutvr.dll'}
    if selection not in (*names, 'neither'): raise SafetyError('invalid desktop selection')
    found = {key: [r['path'] for r in detection['mod_files'] if Path(r['path']).name.casefold() == name]
             for key, name in names.items()}
    blockers = []
    if all(found.values()): blockers.append('VRKanojoDesktop and VRK_PlayWithoutVR must not coexist')
    if any(len(paths) > 1 for paths in found.values()): blockers.append('duplicate desktop plugin candidates')
    if selection != 'neither' and any(paths for key, paths in found.items() if key != selection):
        blockers.append('selected desktop plugin conflicts with an existing alternative; preserve existing files')
    return {'selection': selection, 'candidates': found, 'blockers': blockers,
            'identity_confidence': 'filename candidates only; renamed plugins and GUID identity unverified',
            'automatic_removal_allowed': False}


def map_destination(detection, scope, relative):
    """Candidate path only; never approve payload equivalence or rename game files."""
    if detection['status'] not in ('supported', 'recognized-unverified') or detection['layout'] is None:
        raise SafetyError('mapping requires an unambiguous recognized layout')
    relative = safe_relative(relative)
    if scope not in ('game', 'data'): raise SafetyError('unknown mapping scope')
    if relative.split('/')[0].casefold() in {d.casefold() for _, d in LAYOUTS}:
        raise SafetyError('hardcoded Data-root mapping requires separate review; no implicit translation')
    dest = relative if scope == 'game' else detection['layout']['data'] + '/' + relative
    return {'scope': scope, 'relative': relative, 'candidate_destination': safe_relative(dest),
            'mapping_approved': False, 'installation_allowed': False}


def sentinels(exe, data):
    return [exe, data + '/app.info', data + '/globalgamemanagers',
            data + '/Managed/Assembly-CSharp.dll', data + '/Managed/UnityEngine.dll',
            data + '/Managed/UnityEngine.UI.dll']


def detect(root, profiles=(), trusted_profiles=frozenset()):
    root = Path(os.path.abspath(root))
    result = {'root': str(root), 'status': 'incomplete', 'layout': None, 'game_version': None,
              'unity_version_hint': None, 'profile': None, 'files': [], 'root_files': [],
              'markers': [], 'mod_files': [], 'reasons': [], 'cleanliness': 'unverified',
              'installation_allowed': False, 'layout_verification': 'unverified',
              'installation_state': 'unverified', 'version_confidence': 'unverified'}
    def refuse(status, reason):
        result.update(status=status)
        result['reasons'].append(reason)
        result['validation_message'] = validation_message(status)
        return result
    try:
        no_links(root)
        if not root.is_dir():
            return refuse('incomplete', 'selected root is not a directory')
        initial = root.stat()
        result['root_id'] = [initial.st_dev, initial.st_ino]
        top = list(root.iterdir())
        if len(top) > MAX_FILES:
            raise SafetyError('root inventory limit exceeded')
        names = {}
        for p in top:
            key = p.name.casefold()
            if key in names: return refuse('ambiguous', 'case-insensitive root collision')
            names[key] = p.name
            info = p.lstat()
            if linked(info): raise SafetyError('root child symlink/reparse point refused')
            if stat.S_ISREG(info.st_mode):
                result['root_files'].append({'path': p.name, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns})
        present = [pair for pair in LAYOUTS if pair[0].casefold() in names or pair[1].casefold() in names]
        if len(present) > 1: return refuse('ambiguous', 'mixed original-game layouts')
        if not present: return refuse('unsupported', 'no recognized original-game layout')
        exe, data = present[0]
        result['layout'] = {'executable': exe, 'data': data}
        paths = sentinels(exe, data)
        missing = [p for p in paths if not (root / p).is_file()]
        if missing: return refuse('incomplete', 'missing required files: ' + ', '.join(missing))
        no_links(root / data)
        budget = 0
        def record(relative, group):
            nonlocal budget
            relative = safe_relative(relative)
            path = root / relative
            no_links(path)
            before = path.stat()
            budget += before.st_size
            if budget > MAX_BYTES or len(result['files']) + len(result['mod_files']) >= MAX_FILES:
                raise SafetyError('focused inventory/hash budget exceeded')
            size, sha = stable_hash(path)
            row = {'path': relative, 'size': size, 'sha256': sha, 'mtime_ns': before.st_mtime_ns,
                   'file_id': [before.st_dev, before.st_ino]}
            group.append(row)
            return row
        for path in paths: record(path, result['files'])
        with (root / exe).open('rb') as f:
            header = f.read(64)
            if len(header) < 64 or header[:2] != b'MZ': return refuse('unsupported', 'executable is not a PE image')
            offset = struct.unpack_from('<I', header, 60)[0]
            if offset > 1024 * 1024: return refuse('unsupported', 'PE header offset out of bounds')
            f.seek(offset); pe = f.read(6)
            if len(pe) != 6 or pe[:4] != b'PE\0\0': return refuse('unsupported', 'invalid PE signature')
            result['pe_machine'] = hex(struct.unpack_from('<H', pe, 4)[0])
        if result['pe_machine'] != '0x8664': return refuse('unsupported', 'original-game x64 executable required')
        app = root / data / 'app.info'
        if app.stat().st_size > 4096: raise SafetyError('oversized app identity text')
        result['app_info_hint'] = app.read_text(encoding='utf-8-sig', errors='replace').splitlines()
        with (root / data / 'globalgamemanagers').open('rb') as stream:
            hints = re.findall(rb'\b\d+\.\d+\.\d+[fp]\d+\b', stream.read(4096))
        result['unity_version_hint'] = hints[0].decode() if hints else None
        for marker in ('winhttp.dll', 'version.dll', 'doorstop_config.ini', 'ali21364.dll',
                       'startconfig.xml', 'HF_Patch_version.txt', 'HF_Patch_version', 'HF_Patch_Log.txt'):
            if marker.casefold() in names:
                actual = names[marker.casefold()]
                record(actual, result['mod_files']); result['markers'].append(actual)
        for base in ('BepInEx/core', 'BepInEx/plugins', 'BepInEx/patchers', 'Plugins'):
            start = root / base
            if not start.exists(): continue
            no_links(start)
            if not start.is_dir(): raise SafetyError('mod container is not a directory')
            stack = [(start, 0)]
            directories = 0
            while stack:
                folder, depth = stack.pop(); no_links(folder)
                directories += 1
                if depth > 8 or directories > MAX_FILES: raise SafetyError('mod directory limit exceeded')
                for p in folder.iterdir():
                    no_links(p)
                    if p.is_dir(): stack.append((p, depth+1))
                    else: record(p.relative_to(root).as_posix(), result['mod_files'])
        result['bepinex_present'] = (root / 'BepInEx').is_dir()
        result['framework_identity'] = 'unverified; filenames/hashes only, no assembly loaded'
        core_found = any(r['path'].casefold() == 'bepinex/core/bepinex.dll' for r in result['mod_files'])
        result['framework_status'] = ('present-unverified' if core_found else 'present-incomplete-or-unknown') if result['bepinex_present'] else 'not-detected'
        result['desktop_compatibility'] = desktop_compatibility(result)
        result['cleanliness'] = 'modified-or-third-party-markers-present' if result['markers'] or result['mod_files'] else 'no-known-markers-found; clean identity unverified'
        hashes = {r['path']: {'size': r['size'], 'sha256': r['sha256']} for r in result['files']}
        result['installation_state'] = 'existing-or-modified' if result['markers'] or result['mod_files'] else 'existing; clean state unverified'
        matches, excluded_identity = [], False
        for profile in profiles:
            shape(profile, 'id family version executable data expected')
            if digest(profile) not in trusted_profiles: continue
            if (profile['executable'], profile['data']) != (exe, data): continue
            if profile['family'] != 'original-vr-kanojo-2018' or profile['version'] != '1.31':
                excluded_identity |= profile['expected'] == hashes
                continue
            if profile['expected'] == hashes: matches.append(profile)
        # Rehash only focused evidence to catch observed scan-time changes.
        for row in result['files'] + result['mod_files']:
            p = root / row['path']
            if (stable_hash(p) != (row['size'], row['sha256']) or [p.stat().st_dev, p.stat().st_ino] != row['file_id']
                    or p.stat().st_mtime_ns != row['mtime_ns']):
                raise SafetyError('evidence changed during inspection')
        no_links(root)
        if [root.stat().st_dev, root.stat().st_ino] != result['root_id']: raise SafetyError('root identity changed')
        if len(matches) > 1: return refuse('ambiguous', 'multiple trusted profiles match')
        if not matches:
            if excluded_identity: return refuse('unsupported', 'fingerprint identifies an unsupported family/version')
            return refuse('recognized-unverified', 'candidate layout; no trusted supported-version fingerprint match')
        result.update(status='supported', game_version=matches[0]['version'], profile=matches[0]['id'],
                      layout_verification='verified-by-pinned-profile', version_confidence='verified-by-pinned-profile',
                      validation_message=validation_message('supported'))
        return result
    except (OSError, ValueError) as exc:
        return refuse('incomplete', 'read-only inspection refused: ' + str(exc))


def preflight(root, requests, approvals, gates, profiles=(), trusted_profiles=frozenset(), area=None, receipts=None, desktop_selection='neither'):
    """Real roots produce blocked dry-run reports only; existing planner stays synthetic."""
    detection = detect(root, profiles, trusted_profiles)
    blockers = []
    compatibility = desktop_compatibility(detection, desktop_selection)
    blockers.extend(compatibility['blockers'])
    requested_desktop = set()
    for request in requests:
        if request.get('action') in ('create', 'replace'):
            name = Path(safe_relative(request['destination'])).name.casefold()
            if name == 'vrkanojodesktop.dll': requested_desktop.add('vrkanojo-desktop')
            if name == 'vrk_playwithoutvr.dll': requested_desktop.add('play-without-vr')
    if len(requested_desktop) > 1:
        blockers.append('operation proposals select both mutually exclusive desktop plugins')
    for selected in requested_desktop:
        blockers.extend(desktop_compatibility(detection, selected)['blockers'])
    if detection['status'] != 'supported': blockers.append('supported game identity not established')
    if not isinstance(gates, dict) or any(gates.get(k) is not True for k in ('compatibility','licensing','provenance','mapping')):
        blockers.append('required compatibility/rights/mapping approvals unresolved')
    plan = None
    if area is None:
        blockers.append('real-target planner/ownership/payload integration is not implemented; no execution authorized')
    elif not blockers:
        checked = SyntheticArea(area.path)
        if Path(os.path.abspath(root)) != checked.target: raise SafetyError('planner target does not match detected synthetic area')
        plan = build_plan(checked, requests, receipts or [], approvals, gates).as_dict()
    return {'mode':'read-only-dry-run', 'detection':detection, 'desktop_compatibility':compatibility, 'requested_operations':requests,
            'blockers':blockers, 'synthetic_plan':plan, 'installation_allowed':False, 'execution_authorized':False}
