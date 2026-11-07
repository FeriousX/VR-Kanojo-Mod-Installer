"""Bounded, presentation-only projection of the existing GUI transaction records."""
from collections import Counter

DESKTOP={'neither':'Standard VR (no desktop plugin)', 'vrkanojo-desktop':'VR Kanojo Desktop by FeriousX',
         'play-without-vr':'Original Play Without VR by ManlyMarco'}

def presentation(meta,state,success=False):
    prepared=meta.get('prepared',{});parts=meta.get('binding','0|neither|').split('|',2)
    mask=int(parts[0]);mode=parts[1]
    components=[]
    if mask&1:components.append('BepInEx 5.4.12 x64 and loader settings')
    if mask&8:components.append('Message Center 1.1.1')
    if mask&16:components.append('Mute In Background 1.1 (enable its native configuration after installation)')
    if mask&32:components.append('FPS Counter 3.1')
    if mask&64:components.append('Graphics Settings 1.2.1 (startup config; no advanced menu)')
    components.append(DESKTOP[mode])
    counts=Counter(row['action'] for row in prepared.get('operations',[]))
    preserved=counts['preserve']+counts['protect'];changed=counts['create']+counts['replace']+counts['delete']
    title={'Prepared':'Ready to install', 'Blocked':'Installation cannot proceed', 'Validating':'Validating installation',
           'BackingUp':'Preparing verified backups', 'Applying':'Installing selected files', 'Verifying':'Verifying installation',
           'Completed':'Installation completed successfully!', 'Failed':'Installation was not completed',
           'RecoveryRequired':'Recovery review required'}[state]
    if prepared.get('status')=='AlreadyPresent':title='Selected components are already installed'
    message='Review your selections, then confirm installation. The game will not be launched.'
    if state=='Blocked':message=prepared.get('summary','No installation is authorized.')
    elif state=='Completed':
        if not success:raise ValueError('presentation success requires verified completion')
        backup=meta.get('ui_result',{}).get('backups_verified',False)
        message=('Installation files were verified. '+('Backups verified; recovery records retained.' if backup else 'See technical details for backup and recovery status.')+' Gameplay has not been automatically tested.')
    elif state in ('Failed','RecoveryRequired'):message='No successful installation is claimed. Keep recovery records and inspect technical details before retrying.'
    elif state!='Prepared':message='Please wait. Detailed diagnostics are available without interrupting the transaction.'
    return dict(display_protocol='1',display_title=title,display_target=prepared.get('synthetic_root',parts[2]),
        display_components='; '.join(components),display_message=message,
        files_create=str(counts['create']),files_replace=str(counts['replace']),files_preserve=str(preserved),
        files_remove=str(counts['delete']),files_total=str(sum(counts.values())),
        files_applied=str(meta.get('ui_applied',changed if success else 0)),files_to_apply=str(changed))
