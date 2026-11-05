#!/usr/bin/env python3
"""Patch a new regular-file copy of one reviewed Valve recovery image. Never flash."""
import argparse,bz2,hashlib,importlib.util,json,os,pathlib,re,shutil,signal,struct,subprocess,sys,tempfile,zlib
HERE=pathlib.Path(__file__).resolve().parent;REPO=HERE.parent
COMPRESSED='4254ee02ec34ae8add9aceef1881a2ce675a9d0176171df92e0eaa1bf014c594'
RAW='f9aa0fa2dd618febf28a5e2a583d1e2b5a8ca3f1205be965da584602ac962f40';SIZE=8120172544
URL='https://steamdeck-images.steamos.cloud/recovery/steamdeck-oobe-repair-20260707.10-3.8.14.img.bz2'
def run(*args,**kw):return subprocess.run(args,check=True,**kw)
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
def output_path(p):
 p=pathlib.Path(p).absolute()
 if p.exists() or p.is_symlink():raise RuntimeError('Output already exists; choose a new .img filename')
 if p.suffix!='.img' or str(p.resolve()).startswith('/dev/'):raise RuntimeError('Output must be a new regular .img file outside /dev')
 if not p.parent.is_dir() or p.parent.resolve()!=p.parent:raise RuntimeError('Output parent must exist and must not contain symlinks')
 return p
def partitions(f):
 f.seek(512);h=f.read(512)
 if h[:8]!=b'EFI PART':raise RuntimeError('Missing GPT')
 size=struct.unpack_from('<I',h,12)[0];saved=struct.unpack_from('<I',h,16)[0];header=bytearray(h[:size]);header[16:20]=b'\0'*4
 if not 92<=size<=512 or zlib.crc32(header)!=saved:raise RuntimeError('Invalid GPT header')
 lba,count,width,crc=struct.unpack_from('<QIII',h,72)
 if width!=128 or count>256:raise RuntimeError('Unknown GPT entry layout')
 f.seek(lba*512);table=f.read(count*width)
 if zlib.crc32(table)!=crc:raise RuntimeError('Invalid GPT entries')
 result={}
 for i in range(count):
  row=table[i*width:(i+1)*width]
  if row[:16]==bytes(16):continue
  start,end=struct.unpack_from('<QQ',row,32);name=row[56:128].decode('utf-16-le').rstrip('\0')
  if end<start or (end+1)*512>SIZE or name in result:raise RuntimeError('Unsafe partition bounds/names')
  result[name]={'offset':start*512,'size':(end-start+1)*512}
 expected={'esp':(17408,67091456),'efi-A':(67108864,134217728),'rootfs-A':(335544320,5368709120),'var-A':(5704253440,268435456),'home':(5972688896,2147466752)}
 for name,(offset,length) in expected.items():
  if result.get(name)!={'offset':offset,'size':length}:raise RuntimeError('Unknown recovery partition layout: '+name)
 return result
def expand(source,dest):
 if not source.is_file() or source.is_symlink():raise RuntimeError('Source must be a regular pristine Valve .img.bz2 or .img')
 compressed=source.name.endswith('.img.bz2')
 if digest(source)!=(COMPRESSED if compressed else RAW):raise RuntimeError('Unknown source hash; only reviewed pristine Valve 3.8.14 is supported')
 h=hashlib.sha256();total=0
 opener=bz2.open if compressed else open
 with opener(source,'rb') as src,open(dest,'xb') as out:
  for b in iter(lambda:src.read(1024**2),b''):
   total+=len(b)
   if total>SIZE:raise RuntimeError('Expanded image exceeds expected size')
   h.update(b)
   if b==bytes(len(b)):out.seek(len(b),1)
   else:out.write(b)
  out.truncate(total)
 if total!=SIZE or h.hexdigest()!=RAW:raise RuntimeError('Expanded source hash/size mismatch')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def patch_mounted(root,esp,efi,home,edid,include_dualboot=False):
 from assets import prepare
 from extras_bundle import stage_extras
 install=load('a1install',HERE/'install.py');support=load('a1support',REPO/'payload/etc/aokzoe-a1/support.py');transform=load('a1transform',REPO/'recovery/transform.py')
 grub=efi/'EFI/steamos/grub.cfg';stock=grub.read_text()
 uuid=subprocess.check_output(['findmnt','-nro','UUID','--target',str(esp)],text=True).strip()
 entry=support.make_entry(stock,uuid) # Fail before modifications on unfamiliar boot syntax.
 if stock.count("menuentry 'SteamOS'")!=1 or 'timeout=0' not in stock:raise RuntimeError('Unknown recovery GRUB layout')
 tools=home/'deck/tools'
 if not (tools/'repair_device.sh').is_file():raise RuntimeError('Recovery helper layout changed')
 if not (root/'usr/lib/rauc/atomic-update-keep.conf').is_file():raise RuntimeError('Native RAUC preservation layout changed')
 # Transform in a temporary directory; never replace pristine source until verified.
 with tempfile.TemporaryDirectory(prefix='a1-stage-') as t:
  stage=pathlib.Path(t)/'payload';shutil.copytree(REPO/'payload',stage,symlinks=True);prepare(stage/'etc/aokzoe-a1',edid);stage_extras(REPO,stage)
  shutil.copyfile(HERE/'install.py',stage/'etc/aokzoe-a1/manage.py')
  transform.transform(tools/'repair_device.sh',pathlib.Path(t)/'repair_device.sh')
  names=[str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()]+['etc/'+install.REL,'esp/aokzoe-a1/edid.cpio']
  # Existing compatibility paths in a supposedly pristine image indicate a review error.
  if any((root/n).exists() or (root/n).is_symlink() for n in names):raise RuntimeError('Image already contains A1 configuration')
  state=root/'etc/aokzoe-a1/state';state.mkdir(parents=True,mode=0o700)
  install.capture(root,names,state/'original')
  shutil.copyfile(stage/'etc/aokzoe-a1/support.py',state/'undo-support.py')
  install.copy_payload(stage,root)
  (esp/'aokzoe-a1').mkdir();shutil.copyfile(stage/'etc/aokzoe-a1/edid.cpio',esp/'aokzoe-a1/edid.cpio')
  shutil.copyfile(pathlib.Path(t)/'repair_device.sh',tools/'repair_device.sh');(tools/'repair_device.sh').chmod(0o755)
 for name in ['a1-disk-guard.py','repair_reimage.sh','start-codex-recovery.sh','install-codex.py']:
  shutil.copyfile(REPO/'recovery'/name,tools/name);(tools/name).chmod(0o755)
 if include_dualboot:
  dualstage=load('a1_dualstage',REPO/'dualboot/stage.py');dualstage.stage(tools)
 desktop=home/'deck/Desktop'
 for p in (REPO/'recovery/Desktop').glob('*.desktop'):
  if p.name=='Install-A1-Alongside-Windows.desktop' and not include_dualboot:continue
  shutil.copyfile(p,desktop/p.name);(desktop/p.name).chmod(0o755)
 # Home belongs to image's deck user, without reading any preparer's account files.
 for p in [*tools.glob('a1-*'),tools/'repair_reimage.sh',tools/'start-codex-recovery.sh',tools/'install-codex.py',*desktop.glob('*.desktop')]:os.chown(p,1000,1000)
 pos=stock.index("menuentry 'SteamOS'");s=stock[:pos]+entry+stock[pos:];s=s.replace("menuentry 'SteamOS'","menuentry 'SteamOS (stock display fallback)'",1).replace('timeout=0','timeout=5',1)
 s='\n'.join(line+(' aokzoe_a1.stock=1' if re.search(r'\blinux(?:efi)?\s+/boot/vmlinuz-',line) and 'aokzoe_a1.compat=1' not in line else '') for line in s.splitlines())+'\n'
 grub.write_text(s)
 # Static verification in the patched image, without chroot execution on the host.
 if hashlib.sha256((tools/'repair_device.sh').read_bytes()).hexdigest()!=json.loads((REPO/'recovery/vendor.json').read_text())['patched_sha256']:raise RuntimeError('Recovery transform verification failed')
 for name in json.loads((root/'etc/aokzoe-a1/manifest.json').read_text())['files']:
  if not (root/name.lstrip('/')).exists():raise RuntimeError('Missing payload: '+name)
 if (esp/'aokzoe-a1/edid.cpio').read_bytes()!=(root/'etc/aokzoe-a1/edid.cpio').read_bytes():raise RuntimeError('EFI archive mismatch')
 run('bash','-n',str(tools/'repair_device.sh'))
 for p in (REPO/'recovery/Desktop').glob('*.desktop'):run('desktop-file-validate',str(p))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=pathlib.Path);p.add_argument('output');p.add_argument('--edid');p.add_argument('--include-dualboot',action='store_true',help='Stage the experimental preserve-only dual-boot installer from pinned upstream source');p.add_argument('--inspect-only',action='store_true',help='Hash, decompress and inspect GPT only; no root or mounts');a=p.parse_args()
 out=output_path(a.output);partial=out.with_name(out.name+'.partial')
 if partial.exists() or partial.is_symlink():raise RuntimeError('Partial output exists')
 if shutil.disk_usage(out.parent).free<SIZE+1024**3:raise RuntimeError('Need at least 9 GiB free for image copy')
 if not a.inspect_only:
  if os.geteuid()!=0:raise RuntimeError('Use sudo; this patches only a newly created image file')
  for name in ['losetup','mount','umount','btrfs','blkid','findmnt','patch','bash','desktop-file-validate']:
   if not shutil.which(name):raise RuntimeError('Missing tool: '+name)
 loops=[];mounts=[];root=None;was_ro=False;completed=False
 def interrupted(sig,frame):raise RuntimeError('Interrupted; cleaning up image mounts')
 signal.signal(signal.SIGTERM,interrupted)
 try:
  print('Verifying and expanding pristine Valve image...',flush=True);expand(a.source,partial)
  with partial.open('rb') as f:parts=partitions(f)
  if a.inspect_only:
   print(json.dumps({'raw_sha256':RAW,'bytes':SIZE,'partitions':parts},indent=2));return
  tmp=pathlib.Path(tempfile.mkdtemp(prefix='a1-image-',dir=out.parent))
  try:
   try:
    for name,fstype in [('rootfs-A','btrfs'),('esp','vfat'),('efi-A','vfat'),('home','ext4')]:
     part=parts[name]
     loop=subprocess.check_output(['losetup','--find','--show','--offset',str(part['offset']),'--sizelimit',str(part['size']),'--',str(partial)],text=True).strip()
     if not re.fullmatch(r'/dev/loop\d+',loop):raise RuntimeError('Unexpected loop device')
     loops.append(loop);folder=tmp/name;folder.mkdir()
     if fstype=='btrfs':
      uuid=subprocess.check_output(['blkid','--probe','--match-tag','UUID','--output','value',loop],text=True).strip()
      mounted=subprocess.run(['findmnt','--noheadings','--raw','--types','btrfs','--output','UUID'],capture_output=True,text=True)
      if mounted.returncode not in (0,1):raise RuntimeError('Cannot check mounted Btrfs identities')
      if uuid in mounted.stdout.split():raise RuntimeError('Same Btrfs UUID is already mounted; disconnect the original recovery media before patching its image')
     run('mount','-t',fstype,'-o','rw,nosuid,nodev,noexec',loop,str(folder));mounts.append(folder)
     if name=='rootfs-A':
      root=folder;was_ro='ro=true' in subprocess.check_output(['btrfs','property','get','-ts',str(root),'ro'],text=True)
      if was_ro:run('btrfs','property','set','-ts',str(root),'ro','false')
    patch_mounted(root,tmp/'esp',tmp/'efi-A',tmp/'home',a.edid,a.include_dualboot)
   finally:
    errors=[]
    if root is not None and was_ro:
     try:run('btrfs','property','set','-ts',str(root),'ro','true')
     except Exception as e:errors.append(str(e))
    for folder in list(reversed(mounts)):
     try:run('umount',str(folder));mounts.remove(folder)
     except Exception as e:errors.append(str(e))
    if not mounts:
     for loop in list(reversed(loops)):
      try:run('losetup','--detach',loop);loops.remove(loop)
      except Exception as e:errors.append(str(e))
    if errors:raise RuntimeError('Image cleanup failed: '+'; '.join(errors))
  finally:
   # Never recursively remove a directory while an image filesystem remains mounted.
   if not mounts:shutil.rmtree(tmp)
  partial.rename(out);completed=True
  report={'source_url':URL,'source_sha256':COMPRESSED if a.source.name.endswith('.bz2') else RAW,'output_sha256':digest(out),'bytes':out.stat().st_size,'revision':4,'include_dualboot':a.include_dualboot,'physical_install_tested':False}
  out.with_suffix('.img.json').write_text(json.dumps(report,indent=2)+'\n');print('Patched image: '+str(out))
 finally:
  if mounts or loops:print('Cleanup incomplete: inspect mounts '+str(mounts)+' loops '+str(loops),file=sys.stderr)
  elif not completed:partial.unlink(missing_ok=True)
if __name__=='__main__':
 try:main()
 except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,KeyboardInterrupt) as e:print('Image patch stopped: '+str(e),file=sys.stderr);sys.exit(1)
