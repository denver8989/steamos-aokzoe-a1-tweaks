"""Adapter-gated power-save trial. No driver replacement or automatic speed claim."""
import json,os,pathlib,re,subprocess,tempfile
IDS={'0x0608':'RZ608 / MT7921K','0x7961':'MT7921','0x0616':'RZ616 / MT7922','0x7922':'MT7922'}
UUID=re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}')
def adapters(root=pathlib.Path('/sys/class/net')):
 result=[]
 for interface in sorted(root.iterdir()):
  if not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,15}',interface.name):continue
  try:
   device=interface/'device';vendor=(device/'vendor').read_text().strip().lower();card=(device/'device').read_text().strip().lower()
   if vendor!='0x14c3' or card not in IDS or (device/'driver').resolve().name!='mt7921e' or not (interface/'phy80211').exists():continue
   result.append({'interface':interface.name,'vendor':vendor,'device':card,'driver':'mt7921e','label':IDS[card]})
  except OSError:continue
 return result

def run(*args):
 try:return subprocess.run(args,check=True,capture_output=True,text=True,timeout=30,env={**os.environ,'LC_ALL':'C'}).stdout.strip()
 except (OSError,subprocess.SubprocessError):raise RuntimeError('Wi-Fi command failed: '+args[0]+'. The saved trial can be restored from A1 Extras.') from None

def connection(interface):
 value=run('nmcli','--get-values','GENERAL.CON-UUID','device','show',interface)
 if not UUID.fullmatch(value):raise RuntimeError('Connect this MediaTek adapter to Wi-Fi first, then try again.')
 return value

def profile_value(uuid):
 if not UUID.fullmatch(uuid):raise RuntimeError('Invalid saved connection identifier')
 value=run('nmcli','--get-values','802-11-wireless.powersave','connection','show','uuid',uuid)
 match=re.fullmatch(r'([0-3])(?:\s+\([^\n]*\))?',value)
 if not match:raise RuntimeError('Unknown NetworkManager power-saving setting; no change was made.')
 return int(match[1])

def radio_value(interface):
 match=re.fullmatch(r'Power save:\s*(on|off)',run('iw','dev',interface,'get','power_save'))
 if not match:raise RuntimeError('The driver did not report its power-saving state.')
 return match[1]

def set_profile(uuid,value):run('nmcli','connection','modify','uuid',uuid,'802-11-wireless.powersave',str(value))
def set_radio(interface,value):run('iw','dev',interface,'set','power_save',value)

def guard_path(path):
 for p in [path,*path.parents]:
  if p.is_symlink():raise RuntimeError('Refusing symlink in Wi-Fi backup path')

def save(path,value):
 guard_path(path)
 fd,name=tempfile.mkstemp(prefix='.wifi-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(name,path)
 finally:
  if os.path.exists(name):os.unlink(name)

def read(path):
 guard_path(path)
 if not path.is_file():raise RuntimeError('No Wi-Fi trial backup exists.')
 value=json.loads(path.read_text())
 if not isinstance(value,dict):raise RuntimeError('Unknown Wi-Fi backup format; no changes were made.')
 if value.get('version')!=1 or value.get('phase') not in ['pending','applied'] or not UUID.fullmatch(value.get('uuid','')) or type(value.get('before')) is not int or value['before'] not in range(4) or value.get('radio_before') not in ['on','off']:
  raise RuntimeError('Unknown Wi-Fi backup format; no changes were made.')
 adapter=value.get('adapter',{})
 if not isinstance(adapter,dict):raise RuntimeError('Unknown saved Wi-Fi adapter')
 if adapter.get('vendor')!='0x14c3' or adapter.get('device') not in IDS or adapter.get('driver')!='mt7921e' or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,15}',adapter.get('interface','')):raise RuntimeError('Unknown saved Wi-Fi adapter')
 return value

def same_connection(adapter,uuid):
 return any(all(d[k]==adapter[k] for k in ['interface','vendor','device','driver']) for d in adapters()) and connection(adapter['interface'])==uuid

def restore(path):
 state=read(path);uuid=state['uuid'];adapter=state['adapter']
 current=profile_value(uuid)
 if current not in {2,state['before']}:raise RuntimeError('The saved connection was edited after this trial. Its newer setting was left unchanged; keep the backup for review.')
 set_profile(uuid,state['before'])
 if profile_value(uuid)!=state['before']:raise RuntimeError('Could not verify the restored connection setting; the backup was kept.')
 # Restore the live radio only if it still belongs to this adapter and connection.
 # A removed adapter or changed connection must not prevent restoring the saved profile.
 try:active=same_connection(adapter,uuid)
 except RuntimeError:active=False
 if active:
  set_radio(adapter['interface'],state['radio_before'])
  if radio_value(adapter['interface'])!=state['radio_before']:raise RuntimeError('Could not verify the restored radio setting; the backup was kept.')
 path.unlink()
 return 'Previous Wi-Fi power-saving setting restored. Reconnect Wi-Fi if the saved connection is not currently active.'

def trial(path):
 guard_path(path);matches=adapters()
 if len(matches)!=1:raise RuntimeError('This trial requires exactly one detected MediaTek RZ608/MT7921 or RZ616/MT7922 adapter using mt7921e. No Wi-Fi changes were made.')
 adapter=matches[0];interface=adapter['interface'];uuid=connection(interface)
 before=profile_value(uuid);radio=radio_value(interface)
 if path.exists():
  saved=read(path)
  if saved['uuid']==uuid and saved['adapter']==adapter and saved['phase']=='applied' and before==2 and radio=='off':return 'The Wi-Fi trial is already active. Its original backup has been kept. Use Restore Wi-Fi setting to undo.'
  raise RuntimeError('A Wi-Fi trial backup already exists. Restore that trial before starting another; its original setting was kept.')
 if radio=='off':return 'Wi-Fi power saving is already off. Nothing was changed; this trial is unlikely to improve the current slowdown.'
 if not same_connection(adapter,uuid):raise RuntimeError('The Wi-Fi connection changed. Try again once the connection is stable.')
 save(path,{'version':1,'phase':'pending','uuid':uuid,'adapter':adapter,'before':before,'radio_before':radio})
 try:
  set_profile(uuid,2)
  if profile_value(uuid)!=2 or not same_connection(adapter,uuid):raise RuntimeError('The connection changed during the trial.')
  set_radio(interface,'off')
  if radio_value(interface)!='off' or not same_connection(adapter,uuid):raise RuntimeError('Could not verify the live Wi-Fi power-saving change.')
  state=read(path);state['phase']='applied';save(path,state)
 except BaseException:
  try:restore(path)
  except (OSError,ValueError,RuntimeError):raise RuntimeError('Wi-Fi trial stopped and rollback could not finish. The original setting is saved; use Restore Wi-Fi setting in A1 Extras.') from None
  raise
 return 'Wi-Fi power saving is now off for this connection. Compare download speed and battery use. This is a troubleshooting trial, not a proven A1 speed fix. Use Restore Wi-Fi setting to undo.'
