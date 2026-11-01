"""Owner-approved plugin-only scope; no licensing, ownership or execution authority."""
from .validator import safe_relative
from .recovery import SafetyError
SCOPE_ID='plugins-original-2018-initial-v1'

def validate_scope(scope,components):
 if type(scope) is not dict or scope.get('id')!=SCOPE_ID or scope.get('schema_version')!=1:raise SafetyError('unknown release scope')
 for field in ('included_components','required_components','excluded_components'):
  values=scope.get(field)
  if type(values) is not list or any(not isinstance(x,str) for x in values) or len(set(values))!=len(values) or not set(values)<=set(components):raise SafetyError('invalid scope component set')
 allowed=set(scope['included_components']);excluded=set(scope['excluded_components'])
 if allowed & excluded or allowed|excluded != set(components) or not set(scope['required_components'])<=allowed:raise SafetyError('incomplete/conflicting release scope')
 if not {'bepinex','loader-config'}<=set(scope['required_components']):raise SafetyError('essential plugin scope requirements missing')
 if 'configuration-manager' in allowed:raise SafetyError('legacy Configuration Manager is excluded from this release')
 if allowed & {'game-repair','uncensor-pack','full-save','helper'}:raise SafetyError('omitted historical payload cannot enter initial release')
 return scope

def apply_scope(catalog,scope):
 components={c['id']:c for c in catalog['components']};validate_scope(scope,components)
 catalog['release_scope']=scope
 for c in components.values():
  c.setdefault('historical_required',c['required'])
  c['required']=c['id'] in scope['required_components']
  c['initial_release_included']=c['id'] in scope['included_components']
  if not c['initial_release_included']:c['initial_release_disposition']='Excluded by owner scope; retain historical evidence; do not investigate asset rights for this release.'
  if c['id']=='uncensor-loader':
   c['external_asset_requirements']='Optional loader only. Compatible assets must be obtained and installed separately by the user; no model/asset collection is bundled.'
 catalog['runtime_required_components']=list(scope['required_components'])
 return catalog

def selection_errors(catalog,selected):
 scope=catalog.get('release_scope')
 if scope is None:
  return ['Owner release scope missing from real catalog'] if catalog.get('original_payload_entries')==140 else []
 components={c['id']:c for c in catalog['components']};validate_scope(scope,components);errors=[]
 for key in scope['required_components']:
  if key not in selected:errors.append('Missing release requirement: '+key)
 for key in selected:
  if key not in scope['included_components']:
   errors.append('Excluded from initial plugin-only release: '+key);continue
  c=components[key]
  for f in c.get('runtime_files',c.get('files',[])):
   dest=safe_relative(f['destination']);parts=dest.split('/');root=parts[0].casefold()
   if not ((len(parts)>1 and root in ('bepinex','hf_patch_notices')) or (len(parts)==1 and root in ('winhttp.dll','doorstop_config.ini','changelog.txt'))):
    errors.append('Destination outside plugin-only scope: '+dest)
 return errors
