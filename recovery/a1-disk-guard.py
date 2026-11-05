#!/usr/bin/python3
"""Select and validate the original A1's internal install disk, never recovery media."""
import argparse,json,os,pathlib,re,subprocess,sys
MIN_SIZE=32*1024**3
def command(args):return subprocess.check_output(args,text=True).strip()
def flatten(rows):
 for row in rows:
  yield row
  yield from flatten(row.get('children',[]))
def eligible(rows,protected):
 return [r for r in rows if r.get('type')=='disk' and re.fullmatch(r'/dev/nvme\d+n\d+',r['path']) and r.get('tran')=='nvme' and not r.get('ro') and int(r['size'])>=MIN_SIZE and r['path'] not in protected]
def environment():
 if pathlib.Path('/sys/class/dmi/id/sys_vendor').read_text().strip()!='AOKZOE' or pathlib.Path('/sys/class/dmi/id/product_name').read_text().strip()!='AOKZOE A1 AR07':raise RuntimeError('This installer is only for the original AOKZOE A1 AR07.')
 os_release=pathlib.Path('/etc/os-release').read_text()
 if not re.search(r'^ID=["\']?steamos["\']?$',os_release,re.M) or not re.search(r'^VARIANT_ID=["\']?steamdeck-oobe["\']?$',os_release,re.M):raise RuntimeError('Boot this USB into its SteamOS recovery desktop before installing.')
def snapshot():
 return json.loads(command(['lsblk','--json','--tree','--bytes','--output','PATH,TYPE,TRAN,RO,SIZE,MODEL,SERIAL,MOUNTPOINTS,LOG-SEC']))['blockdevices']
def ancestors(source):
 source=source.split('[',1)[0]
 if not source.startswith('/dev/'):raise RuntimeError('Cannot identify recovery-media storage safely.')
 return set(command(['lsblk','--inverse','--noheadings','--raw','--output','PATH',source]).splitlines())
def inspect():
 environment();rows=snapshot();protected=set()
 for target in ['/','/home','/var','/efi','/esp']:
  src=command(['findmnt','--noheadings','--raw','--output','SOURCE','--target',target])
  protected.update(ancestors(src))
 root_source=command(['findmnt','--noheadings','--raw','--output','SOURCE','--target','/'])
 root_ancestors=ancestors(root_source)
 all_rows=list(flatten(rows))
 if not any(r['path'] in root_ancestors and r.get('tran')=='usb' for r in all_rows):raise RuntimeError('The running recovery system is not on USB; refusing to erase any disk.')
 return rows,protected

def select():
 rows,protected=inspect();candidates=eligible(rows,protected)
 requested=os.environ.get('STEAMOS_TARGET_DISK')
 if requested:candidates=[r for r in candidates if r['path']==requested]
 if len(candidates)!=1:raise RuntimeError('Expected one writable internal NVMe disk separate from the recovery USB; found '+str(len(candidates))+'. No disk has been changed.')
 disk=candidates[0]
 if int(disk.get('log-sec') or 0)!=512:raise RuntimeError('This Valve image requires a disk with 512-byte logical sectors. No disk has been changed.')
 print('Install target: '+disk['path']+' | '+(disk.get('model') or 'NVMe')+' | '+str(round(int(disk['size'])/1024**3,1))+' GiB',file=sys.stderr)
 print(disk['path'])
def prepare(path,serial):
 rows,protected=inspect();matches=[r for r in eligible(rows,protected) if r['path']==path]
 if len(matches)!=1:raise RuntimeError('The selected target is no longer a safe internal installation disk.')
 disk=matches[0]
 if int(disk.get('log-sec') or 0)!=512:raise RuntimeError('Logical sector size changed')
 if not serial or disk.get('serial')!=serial:raise RuntimeError('Target disk identity changed; refusing to continue.')
 nodes=list(flatten([disk]));paths={r['path'] for r in nodes}
 swap=command(['swapon','--show','--noheadings','--raw','--output','NAME'])
 for name in swap.splitlines():
  if name.startswith('/dev/') and path in ancestors(name):raise RuntimeError('The target contains active swap; stop that swap before retrying.')
  if name.startswith('/') and not name.startswith('/dev/'):
   try:
    if path in ancestors(command(['findmnt','-nro','SOURCE','--target',name])):raise RuntimeError('The target contains an active swap file; stop it before retrying.')
   except subprocess.CalledProcessError:raise RuntimeError('Could not verify an active swap file safely.')
 mounts=sorted({p for r in nodes for p in (r.get('mountpoints') or []) if p},key=lambda p:p.count('/'),reverse=True)
 for p in mounts:subprocess.run(['umount','--',p],check=True)
 fresh,protected=inspect();matches=[r for r in eligible(fresh,protected) if r['path']==path and r.get('serial')==serial and int(r.get('log-sec') or 0)==512]
 if len(matches)!=1:raise RuntimeError('Target identity or eligibility changed after unmount')
 disk=matches[0]
 if any(any(r.get('mountpoints') or []) for r in flatten([disk])):raise RuntimeError('A target partition is still mounted; refusing to partition it.')
 # Normal installation removes disk signatures; it does not require NVMe sanitize.
 subprocess.run(['wipefs','--all','--force',path],check=True)
 print('Target signatures cleared. Continuing with normal partitioning and formatting.',file=sys.stderr)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['select','prepare']);p.add_argument('--disk');p.add_argument('--serial');a=p.parse_args()
 try:
  if a.action=='select':select()
  else:prepare(a.disk,a.serial)
 except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as e:
  print('Installation stopped: '+str(e),file=sys.stderr);sys.exit(1)
