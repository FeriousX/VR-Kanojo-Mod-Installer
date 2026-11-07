"""Read-only final release configuration validation. Does not build or install."""
import hashlib,json
from pathlib import Path
from hf_payload.validator import safe_relative,no_links
from hf_payload.recovery import SafetyError

def load_final_config(root, version='1.1.1'):
 root=Path(root);no_links(root)
 if type(version) is not str or version not in ('1.1.0','1.1.1'):raise SafetyError('unsupported final release version')
 kind={'1.1.0':'FINAL110','1.1.1':'FINAL111'}[version]
 numeric=version+'.0'
 value=json.loads((root/('manifests/final-v'+version+'.json')).read_text(encoding='utf-8-sig'))
 required={'schema_version':1,'version':version,'numeric_version':numeric,'build_kind':kind,'exe_name':'VRK-Mod-Installer-v'+version+'.exe','source_name':'VRK-Mod-Installer-v'+version+'-Source.zip','published':False}
 if any(value.get(k)!=v or type(value.get(k)) is not type(v) for k,v in required.items()):raise SafetyError('invalid final configuration for '+version)
 for key in ('bundle_dir','build_dir','report_dir','distribution_dir'):
  safe_relative(value[key])
 if (value['bundle_dir'],value['build_dir'],value['report_dir'],value['distribution_dir'])!=('out/'+kind,'build/'+kind,'out/final-v'+version,'out/FinalRelease_v'+version):raise SafetyError('unexpected final output mapping')
 from hf_payload.real_components import catalog_digest
 catalog=json.loads((root/'manifests/real-components.json').read_text())
 if catalog_digest(catalog)!=value['catalog_digest'] or set(value['approved_components'])!=set(catalog['release_scope']['included_components']):raise SafetyError('final component review changed')
 return value

def source_export_plan(root):
 root=Path(root);no_links(root);rules_path=root/'manifests/source-export-rules.json';rules=json.loads(rules_path.read_text())
 if type(rules.get('schema_version')) is not int or rules.get('schema_version')!=1 or rules.get('mode')!='explicit-source-only':raise SafetyError('unsupported source rules')
 rows=[];seen=set()
 approved_archives=set(rules['approved_source_archive_sha256'])
 for row in rules['files']:
  rel=safe_relative(row['path']);parts=Path(rel).parts
  if any(p.casefold() in {'out','build','cache','payload','.git','__pycache__','journals','backups','receipts','credentials','state'} for p in parts):raise SafetyError('private/generated source input')
  if parts[0] not in {'src','tools','tests','templates','manifests','third_party','docs'} and rel not in {'README.md','CONTRIBUTING.md','RELEASE_NOTES.md','THIRD_PARTY_NOTICES.md','CREDITS.md','LICENSE','CHANGELOG.md','pyproject.toml','build-requirements.txt','release-status.json','.gitattributes','.gitignore'}:raise SafetyError('unapproved source location')
  if rel.casefold() in seen:raise SafetyError('duplicate source destination')
  seen.add(rel.casefold());path=root/rel;no_links(path)
  if path.suffix.lower() in {'.exe','.dll','.pyd','.pdb','.log','.key'}:raise SafetyError('binary/private source input')
  raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
  if sha!=row['sha256']:raise SafetyError('source input changed: '+rel)
  if path.suffix.lower()=='.zip' and sha not in approved_archives:raise SafetyError('archive not approved corresponding source')
  rows.append({'path':rel,'sha256':sha,'bytes':len(raw)})
 # The policy itself is copied and hashed separately; no self-hash cycle.
 rows.append({'path':'manifests/source-export-rules.json','sha256':hashlib.sha256(rules_path.read_bytes()).hexdigest(),'bytes':rules_path.stat().st_size})
 return rows
