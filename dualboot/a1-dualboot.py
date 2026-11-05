#!/usr/bin/env python3
"""Fresh A1 dual-boot installation into a verified trailing free extent only."""
import argparse,hashlib,importlib.util,json,os,pathlib,re,shlex,subprocess,sys,tempfile,time
HERE=pathlib.Path(__file__).resolve().parent
SECTOR=512;MIB=2048;ROOT_BYTES=5368709120;MIN_FREE=32*1024**3
GUIDS=['C12A7328-F81F-11D2-BA4B-00A0C93EC93B','EBD0A0A2-B9E5-4433-87C0-68B6B72699C7','EBD0A0A2-B9E5-4433-87C0-68B6B72699C7','4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709','4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709','4D21B016-B534-45C2-A9FB-5C16E091FD2D','4D21B016-B534-45C2-A9FB-5C16E091FD2D','933AC7E1-2EB4-4F13-B844-0E14E2AEF915']
NAMES=['esp','efi-A','efi-B','rootfs-A','rootfs-B','var-A','var-B','home']
VARS=['FS_ESP','FS_EFI_A','FS_EFI_B','FS_ROOT_A','FS_ROOT_B','FS_VAR_A','FS_VAR_B','FS_HOME']
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def command(*args):return subprocess.check_output(args,text=True).strip()
def fingerprint(table):return hashlib.sha256(json.dumps(table,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def canonical(part):return {k:part.get(k) for k in ['node','start','size','type','uuid','name','attrs']}
def layout(table):
 if table.get('label')!='gpt' or int(table.get('sectorsize',0))!=SECTOR:raise RuntimeError('Only reviewed 512-byte-sector GPT layouts are supported')
 device=table.get('device','')
 if not re.fullmatch(r'/dev/nvme\d+n\d+',device):raise RuntimeError('Unknown internal disk name')
 rows=table.get('partitions',[])
 if not rows:raise RuntimeError('Expected an existing Windows partition table')
 for p in rows:
  if p.get('name') in NAMES:raise RuntimeError('SteamOS partitions already exist. This workflow is for a fresh dual-boot installation only.')
  if int(p['start'])<=0 or int(p['size'])<=0:raise RuntimeError('Invalid partition bounds')
 ordered=sorted(rows,key=lambda p:int(p['start']))
 if any(int(a['start'])+int(a['size'])>int(b['start']) for a,b in zip(ordered,ordered[1:])):raise RuntimeError('Overlapping partitions')
 if not any(p['type'].upper()==GUIDS[0] for p in rows) or not any(p['type'].upper()==GUIDS[1] for p in rows):raise RuntimeError('Expected Windows EFI and data partitions')
 start=((max(int(p['start'])+int(p['size']) for p in rows)+MIB-1)//MIB)*MIB;end=int(table.get('lastlba',0))
 if (end-start+1)*SECTOR<MIN_FREE:raise RuntimeError('Leave at least 32 GiB of unallocated space at the END of the disk using Windows Disk Management first. No Windows volume will be resized here.')
 indices=[]
 for p in rows:
  m=re.fullmatch(r'/dev/nvme\d+n\d+p(\d+)',p['node'])
  if not m or p['node']!=device+'p'+m[1]:raise RuntimeError('Unknown or mixed internal NVMe partition naming')
  indices.append(int(m[1]))
 if len(indices)!=len(set(indices)):raise RuntimeError('Duplicate GPT partition indices')
 first=max(indices)+1
 if first+7>128:raise RuntimeError('Not enough unused GPT indices')
 sizes=[256,64,64,5120,5120,256,256,None];result=[];cursor=start
 for n,(name,size,guid) in enumerate(zip(NAMES,sizes,GUIDS),first):
  length=size*MIB if size is not None else end-cursor+1
  if length<=0:raise RuntimeError('Insufficient free space')
  result.append({'index':n,'name':name,'start':cursor,'size':length,'type':guid});cursor+=length
 return result
def context():
 if os.geteuid()!=0:raise RuntimeError('Use the desktop launcher with sudo')
 g=load('disk_guard',HERE/'a1-disk-guard.py');rows,protected=g.inspect();candidates=g.eligible(rows,protected)
 if len(candidates)!=1:raise RuntimeError('Expected one safe writable internal NVMe separate from the running recovery USB')
 disk=candidates[0]
 if int(disk.get('log-sec') or 0)!=512 or not disk.get('serial'):raise RuntimeError('Target needs 512-byte sectors and a stable serial identity')
 if any(any(x.get('mountpoints') or []) for x in g.flatten([disk])):raise RuntimeError('Unmount the internal disk volumes first; Windows volumes will not be unmounted automatically')
 swap=command('swapon','--show','--noheadings','--raw','--output','NAME')
 for name in swap.splitlines():
  source=name if name.startswith('/dev/') else command('findmnt','-nro','SOURCE','--target',name)
  if disk['path'] in g.ancestors(source):raise RuntimeError('Active swap uses the internal target')
 table=json.loads(command('sfdisk','--json',disk['path']))['partitiontable']
 if table.get('device')!=disk['path'] or int(table.get('lastlba',0))>int(disk['size'])//SECTOR-34:raise RuntimeError('Unexpected partition-table bounds or device')
 source=command('findmnt','-nro','SOURCE','--target','/').split('[',1)[0]
 if int(command('blockdev','--getsize64',source))!=ROOT_BYTES:raise RuntimeError('Unreviewed recovery root size; use the reviewed patched Valve image')
 return disk,table
def compare_identity(plan,disk):
 if disk['path']!=plan['disk'] or disk.get('serial')!=plan['serial'] or int(disk['size'])!=plan['disk_bytes']:raise RuntimeError('Internal target identity changed')
def verify_original(plan,table):
 for key in ['label','id','device','unit','firstlba','lastlba','sectorsize']:
  if table.get(key)!=plan['original'].get(key):raise RuntimeError('Original GPT metadata changed: '+key)
 current={p['node']:canonical(p) for p in table['partitions']}
 for p in plan['original']['partitions']:
  if current.get(p['node'])!=canonical(p):raise RuntimeError('An original Windows partition entry changed; stop and inspect the saved GPT backup')
def verify_created(plan,table):
 verify_original(plan,table);expected_count=len(plan['original']['partitions'])+8
 if len(table['partitions'])!=expected_count:raise RuntimeError('Unexpected partition count after creation')
 for entry in plan['new']:
  node=plan['disk']+'p'+str(entry['index']);matches=[p for p in table['partitions'] if p['node']==node]
  if len(matches)!=1:raise RuntimeError('Missing new partition: '+node)
  p=matches[0]
  if (int(p['start']),int(p['size']),p['type'].upper(),p.get('name'))!=(entry['start'],entry['size'],entry['type'],entry['name']):raise RuntimeError('New partition layout differs from plan')
def verify_boot_mapping(plan):
 for letter,root_entry,efi_entry in [('A',plan['new'][3],plan['new'][1]),('B',plan['new'][4],plan['new'][2])]:
  for target,entry,fs in [('/',root_entry,'btrfs'),('/esp',plan['new'][0],'vfat'),('/efi',efi_entry,'vfat')]:
   raw=command('steamos-chroot','--no-overlay','--disk',plan['disk'],'--partset',letter,'--','findmnt','--json','--output','TARGET,SOURCE,FSTYPE','--target',target)
   rows=json.loads(raw).get('filesystems',[])
   expected=plan['disk']+'p'+str(entry['index'])
   if len(rows)!=1 or rows[0].get('target')!=target or rows[0].get('fstype')!=fs or os.path.realpath(rows[0].get('source','').split('[',1)[0])!=expected:raise RuntimeError('Native boot helper did not map to the NEW SteamOS partitions; refusing bootloader writes')
def read_plan(path):
 p=pathlib.Path(path)
 if p.is_symlink() or p.stat().st_uid!=0 or p.stat().st_mode&0o022:raise RuntimeError('Plan must be a root-owned file, not group/world writable or a symlink')
 plan=json.loads(p.read_text())
 if layout(plan['original'])!=plan['new'] or fingerprint(plan['original'])!=plan['fingerprint']:raise RuntimeError('Invalid or altered plan')
 return plan
def create(plan):
 disk,table=context();compare_identity(plan,disk)
 if fingerprint(table)!=plan['fingerprint']:raise RuntimeError('Partition table changed after confirmation')
 backup=pathlib.Path(plan['backup']);backup.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(['sgdisk','--backup='+str(backup),plan['disk']],check=True)
 for entry in plan['new']:
  # A fresh identity and original-table check precedes every GPT mutation.
  disk,table=context();compare_identity(plan,disk);verify_original(plan,table)
  n=entry['index'];last=entry['start']+entry['size']-1
  subprocess.run(['sgdisk',f'--new={n}:{entry["start"]}:{last}',f'--change-name={n}:{entry["name"]}',f'--typecode={n}:{entry["type"]}',plan['disk']],check=True)
 subprocess.run(['partprobe',plan['disk']],check=True);subprocess.run(['udevadm','settle','--timeout=30'],check=True)
 disk,table=context();compare_identity(plan,disk);verify_created(plan,table)
 for entry in plan['new']:
  node=pathlib.Path(plan['disk']+'p'+str(entry['index']))
  if not node.is_block_device():raise RuntimeError('New partition node did not appear')
 print('New partitions verified; existing Windows partition entries retained.')
def run():
 for tool in ['sgdisk','sfdisk','partprobe','udevadm','zenity','blockdev']:
  import shutil
  if not shutil.which(tool):raise RuntimeError('Recovery tool missing: '+tool)
 disk,table=context();new=layout(table)
 if not pathlib.Path('/etc/aokzoe-a1/support.py').is_file():raise RuntimeError('Boot the A1-patched recovery image so the hardware fixes are included in the copied OS')
 logdir=pathlib.Path('/home/deck/SteamOS-Recovery/logs');logdir.mkdir(parents=True,exist_ok=True)
 stamp=time.strftime('%Y%m%d-%H%M%S');backup=logdir/('dualboot-gpt-'+stamp+'.bin')
 plan={'disk':disk['path'],'serial':disk['serial'],'disk_bytes':int(disk['size']),'original':table,'fingerprint':fingerprint(table),'new':new,'backup':str(backup)}
 summary='Install SteamOS alongside Windows on '+disk['path']+'?\n\nThis creates eight NEW partitions in the trailing unallocated space. Existing Windows partition entries are retained; no Windows filesystem is resized or formatted.\nNew SteamOS home: '+str(round(new[-1]['size']*SECTOR/1024**3,1))+' GiB.\n\nKeep a Windows backup and BitLocker recovery key available. This preview has not been physically validated.\n\nType INSTALL to continue.'
 p=subprocess.run(['zenity','--entry','--title=A1 dual-boot installation','--text='+summary],capture_output=True,text=True)
 if p.returncode or p.stdout.strip()!='INSTALL':return
 with tempfile.TemporaryDirectory(prefix='a1-dualboot-',dir='/run') as t:
  t=pathlib.Path(t);jsonpath=t/'plan.json';jsonpath.write_text(json.dumps(plan,indent=2)+'\n');jsonpath.chmod(0o600)
  envfile=t/'plan.sh';lines=['DISK='+shlex.quote(plan['disk']),'DISK_SUFFIX=p','A1_DUALBOOT_JSON='+shlex.quote(str(jsonpath))]
  lines.extend(name+'='+str(entry['index']) for name,entry in zip(VARS,new));envfile.write_text('\n'.join(lines)+'\n');envfile.chmod(0o600)
  logfile=logdir/('dualboot-install-'+stamp+'.log');environment=dict(os.environ,A1_DUALBOOT_PLAN=str(envfile));environment.pop('NOPROMPT',None)
  with logfile.open('x') as log:
   process=subprocess.Popen(['bash',str(HERE/'a1-dualboot-install.sh')],env=environment,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   for line in process.stdout:print(line,end='',flush=True);log.write(line);log.flush()
   rc=process.wait()
  if rc:raise RuntimeError('Installation stopped; private log: '+str(logfile)+'. New partitions may be partially installed. Do not rerun a wipe installer.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['run','create','verify','verify-boot-mapping']);p.add_argument('--plan');a=p.parse_args()
 try:
  if a.action=='run':run()
  else:
   plan=read_plan(a.plan)
   if a.action=='create':create(plan)
   else:
    disk,table=context();compare_identity(plan,disk);verify_created(plan,table)
    if a.action=='verify-boot-mapping':verify_boot_mapping(plan)
 except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as e:print('A1 dual boot stopped: '+str(e),file=sys.stderr);sys.exit(1)
