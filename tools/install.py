#!/usr/bin/env python3
"""Transactional /etc-only compatibility manager. Backup state persists with RAUC."""
import argparse,fcntl,hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile
BASE=pathlib.Path('/etc/aokzoe-a1')
REL='systemd/system/multi-user.target.wants/aokzoe-a1-persistence.service'
def command(*args):subprocess.run(args,check=True,timeout=120)
def preflight():
 if os.geteuid()!=0:raise RuntimeError('Run with sudo on the target original A1')
 d=pathlib.Path('/sys/class/dmi/id')
 if (d/'sys_vendor').read_text().strip()!='AOKZOE' or (d/'product_name').read_text().strip()!='AOKZOE A1 AR07':raise RuntimeError('Only original AOKZOE A1 AR07 is supported')
 values={}
 for line in pathlib.Path('/etc/os-release').read_text().splitlines():
  if '=' in line:
   k,v=line.split('=',1);values[k]=v.strip('"\'')
 if values.get('ID')!='steamos' or values.get('VARIANT_ID')=='steamdeck-oobe':raise RuntimeError('Requires installed Valve SteamOS; recovery image uses patch-image.py')
 if not pathlib.Path('/usr/lib/rauc/atomic-update-keep.conf').is_file() or not os.access('/etc/grub.d/10_linux',os.X_OK):raise RuntimeError('Unknown updater/boot layout; review required')
 for name in ['systemctl','update-grub','findmnt','blkid']:
  if not shutil.which(name):raise RuntimeError('Required command missing: '+name)
def safe(path):
 path=pathlib.Path(path)
 for p in [path,*path.parents]:
  if p.is_symlink():raise RuntimeError('Refusing symlink in managed path: '+str(p))
 return path
def capture(root,names,dest):
 dest.mkdir(parents=True,exist_ok=False);records={}
 for name in names:
  p=root/name
  safe(p.parent)
  if p.is_symlink():records[name]={'link':os.readlink(p)}
  elif p.is_file():
   records[name]={'mode':p.stat().st_mode&0o777};q=dest/'files'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
  elif p.exists():raise RuntimeError('Managed file is a directory: '+str(p))
  else:records[name]=None
 (dest/'index.json').write_text(json.dumps(records,indent=2)+'\n');return records
def restore(root,snapshot):
 records=json.loads((snapshot/'index.json').read_text())
 for name,item in records.items():
  if pathlib.PurePosixPath(name).is_absolute() or '..' in pathlib.PurePosixPath(name).parts:raise RuntimeError('Unsafe backup path')
  p=root/name;safe(p.parent)
  if p.exists() or p.is_symlink():p.unlink()
  if item is not None:
   p.parent.mkdir(parents=True,exist_ok=True)
   if 'link' in item:p.symlink_to(item['link'])
   else:shutil.copyfile(snapshot/'files'/name,p);p.chmod(item['mode'])
def copy_payload(payload,root):
 for p in sorted(payload.rglob('*')):
  if str(p.relative_to(payload))=='etc/'+REL:continue
  q=root/p.relative_to(payload)
  if p.is_dir():safe(q).mkdir(parents=True,exist_ok=True)
  else:
   safe(q);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);q.chmod(p.stat().st_mode&0o777)
 q=root/('etc/'+REL);safe(q.parent).mkdir(parents=True,exist_ok=True)
 if q.is_symlink():q.unlink()
 elif q.exists():raise RuntimeError('Unexpected service enablement file')
 q.symlink_to('../aokzoe-a1-persistence.service')
def activate():
 command('systemctl','daemon-reload')
 command('/usr/bin/python3',str(BASE/'support.py'),'bootstrap')
 command('update-grub')
def main():
 p=argparse.ArgumentParser();p.add_argument('action',nargs='?',default='install',choices=['install','undo','status']);p.add_argument('--edid',help='Use an offline upstream EDID with pinned checksum');a=p.parse_args()
 if a.action=='status':
  print((BASE/'manifest.json').read_text() if (BASE/'manifest.json').exists() else 'A1 tweaks are not installed')
  print('Undo backup: '+str((BASE/'state/original/index.json').is_file()))
  status=pathlib.Path('/var/lib/aokzoe-a1/status.json')
  if status.exists():print(status.read_text())
  return
 preflight();safe(BASE);BASE.mkdir(parents=True,exist_ok=True)
 with (BASE/'.lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  state=BASE/'state';safe(state);state.mkdir(mode=0o700,exist_ok=True);state.chmod(0o700)
  original=state/'original'
  if a.action=='undo':
   if not (original/'index.json').exists():raise RuntimeError('No undo backup; refusing to guess previous configuration')
   # Keep backup/manager available so undo can be retried after an interrupted update.
   restore(pathlib.Path('/'),original)
   command('systemctl','daemon-reload');command('update-grub')
   pathlib.Path('/run/wireplumber/wireplumber.conf.d/90-aokzoe-a1-analog.conf').unlink(missing_ok=True)
   try:
    # Re-enable only the endpoint changed by this bundle and only on reviewed firmware.
    import importlib.util
    spec=importlib.util.spec_from_file_location('a1support',state/'undo-support.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);wake=m.standby_guard();previous=(state/'wake-before').read_text().strip()
    if previous not in ('enabled','disabled'):raise RuntimeError('Invalid recorded wake policy')
    wake.write_text(previous+'\n')
   except (OSError,RuntimeError) as e:print('Wake policy left unchanged: '+str(e))
   print('Undo complete. Reboot to return to the previous display/audio configuration.');return
  repo=pathlib.Path(__file__).resolve().parent.parent
  from assets import prepare
  with tempfile.TemporaryDirectory(prefix='a1-install-') as tmp:
   staging=pathlib.Path(tmp)/'payload';shutil.copytree(repo/'payload',staging,symlinks=True)
   prepare(staging/'etc/aokzoe-a1',a.edid)
   shutil.copyfile(__file__,staging/'etc/aokzoe-a1/manage.py')
   names=['/'+str(x.relative_to(staging)) for x in staging.rglob('*') if x.is_file()]+['/etc/'+REL,'/esp/aokzoe-a1/edid.cpio']
   # Root-relative names cannot escape a fixture root or the installed root.
   names=[x.lstrip('/') for x in names]
   before=pathlib.Path(tmp)/'before';capture(pathlib.Path('/'),names,before)
   if not original.exists():shutil.copytree(before,original)
   shutil.copyfile(staging/'etc/aokzoe-a1/support.py',state/'undo-support.py')
   # Capture policy for failed-install rollback without storing DSDT or machine identifiers.
   wake=pathlib.Path('/sys/devices/platform/PNP0C0C:00/power/wakeup');oldwake=wake.read_text() if wake.exists() else None
   try:
    copy_payload(staging,pathlib.Path('/'));activate()
   except BaseException:
    restore(pathlib.Path('/'),before)
    if oldwake is not None:wake.write_text(oldwake)
    try:command('systemctl','daemon-reload');command('update-grub')
    except Exception as e:print('Rollback boot regeneration needs attention: '+str(e),file=sys.stderr)
    raise
  print('Installed revision 4. Reboot when ready. Undo: sudo python3 /etc/aokzoe-a1/manage.py undo')
if __name__=='__main__':
 try:main()
 except (OSError,RuntimeError,subprocess.SubprocessError) as e:print('A1 tweaks: '+str(e),file=sys.stderr);sys.exit(1)
