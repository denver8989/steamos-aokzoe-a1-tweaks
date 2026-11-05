#!/usr/bin/env python3
"""Optional post-install setup. Never run this on recovery media or another handheld."""
import argparse,copy,fcntl,hashlib,json,os,pathlib,pwd,re,shutil,stat,subprocess,sys,tarfile,tempfile,urllib.request,zipfile
import wifi
REPO=pathlib.Path(__file__).resolve().parent.parent
UNIT=pathlib.Path('/etc/systemd/system/plugin_loader.service')
KEEP=pathlib.Path('/etc/atomic-update.conf.d/91-aokzoe-a1-extras.conf')
LINK=pathlib.Path('/etc/systemd/system/multi-user.target.wants/plugin_loader.service')
def command(*args):return subprocess.run(args,check=True,timeout=120)
def safe(p,leaf=True):
 p=pathlib.Path(p)
 for q in ([p] if leaf else [])+list(p.parents):
  if q.is_symlink():raise RuntimeError('Refusing symlink in destination: '+str(q))
 return p
def preflight(user):
 if os.geteuid()!=0:raise RuntimeError('Use the desktop launcher or sudo')
 d=pathlib.Path('/sys/class/dmi/id')
 if (d/'sys_vendor').read_text().strip()!='AOKZOE' or (d/'product_name').read_text().strip()!='AOKZOE A1 AR07':raise RuntimeError('Only the original AOKZOE A1 AR07 is supported')
 values={k:v.strip('"\'') for line in pathlib.Path('/etc/os-release').read_text().splitlines() if '=' in line for k,v in [line.split('=',1)]}
 if values.get('ID')!='steamos' or values.get('VARIANT_ID')=='steamdeck-oobe':raise RuntimeError('Install SteamOS completely first, then run extras from its desktop. Do not install extras on the recovery USB.')
 account=pwd.getpwnam(user)
 if account.pw_uid==0 or not pathlib.Path(account.pw_dir).is_dir():raise RuntimeError('Choose the installed desktop user, not root')
 if os.uname().machine!='x86_64':raise RuntimeError('Only Linux x86_64 is supported')
 return account
def download(spec,dest):
 h=hashlib.sha256();size=0
 request=urllib.request.Request(spec['url'],headers={'User-Agent':'aokzoe-a1-tweaks'})
 print('Downloading '+spec['url'],flush=True)
 with urllib.request.urlopen(request,timeout=60) as response,dest.open('xb') as f:
  for chunk in iter(lambda:response.read(1024**2),b''):
   size+=len(chunk)
   if size>512*1024**2:raise RuntimeError('Unexpected package size')
   h.update(chunk);f.write(chunk)
 if h.hexdigest()!=spec['sha256']:raise RuntimeError('Package checksum differs; refusing installation')
def member_path(folder,name):
 p=pathlib.PurePosixPath(name)
 if p.is_absolute() or '..' in p.parts or not p.parts:raise RuntimeError('Unsafe archive member')
 return folder.joinpath(*p.parts)
def unpack(archive,folder,kind):
 folder.mkdir();total=0
 if kind=='zip':
  with zipfile.ZipFile(archive) as z:
   for item in z.infolist():
    total+=item.file_size
    if total>1024**3 or stat.S_ISLNK(item.external_attr>>16):raise RuntimeError('Unsafe ZIP entry or expanded size')
    p=member_path(folder,item.filename)
    if item.is_dir():p.mkdir(parents=True,exist_ok=True)
    else:
     p.parent.mkdir(parents=True,exist_ok=True)
     with z.open(item) as src,p.open('xb') as out:shutil.copyfileobj(src,out)
     p.chmod(0o755 if (item.external_attr>>16)&0o111 else 0o644)
 else:
  with tarfile.open(archive,'r:gz') as tar:
   for item in tar:
    total+=item.size
    if total>1024**3 or not (item.isfile() or item.isdir()):raise RuntimeError('Unsafe TAR entry or expanded size')
    p=member_path(folder,item.name)
    if item.isdir():p.mkdir(parents=True,exist_ok=True)
    else:
     p.parent.mkdir(parents=True,exist_ok=True)
     with tar.extractfile(item) as src,p.open('xb') as out:shutil.copyfileobj(src,out)
     p.chmod(0o755 if item.mode&0o111 else 0o644)
 roots=list(folder.iterdir())
 if len(roots)!=1 or not roots[0].is_dir():raise RuntimeError('Unknown package root layout')
 return roots[0]
def tdp_preset(settings):
 result=copy.deepcopy(settings)
 profiles=result.setdefault('tdpProfiles',{});profiles.setdefault('default',{})['tdp']=30
 result['maxTdp']=max(30,int(result.get('maxTdp',30)))
 result.setdefault('advanced',{})['enableTdpControl']=True
 return result
def glyph_preset(settings):
 result=copy.deepcopy(settings);result.update(active=True,Handheld='AOKZOE A1');return result
def write_json(path,value):
 safe(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name('.a1-'+path.name)
 safe(tmp)
 with tmp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
def read_json(p):return json.loads(p.read_text()) if p.exists() else {}
def remove(p):
 safe(p,leaf=False)
 if p.is_symlink() or p.is_file():p.unlink()
 elif p.exists():shutil.rmtree(p)
def save(paths,dest,extend=False):
 dest.mkdir(parents=True,exist_ok=extend);index=read_json(dest/'index.json')
 for p in paths:
  p=pathlib.Path(p);key=str(p)
  if key in index:continue
  safe(p,leaf=False);item={'exists':p.exists() or p.is_symlink()}
  if item['exists']:
   slot=str(len(index));item['slot']=slot;q=dest/slot
   if p.is_symlink():item['link']=os.readlink(p)
   elif p.is_dir():shutil.copytree(p,q,symlinks=True)
   else:shutil.copy2(p,q)
   item['owners']={str(x.relative_to(p)) if x!=p else '.':[x.lstat().st_uid,x.lstat().st_gid] for x in [p,*(p.rglob('*') if p.is_dir() and not p.is_symlink() else [])]}
  index[key]=item
 write_json(dest/'index.json',index)
def restore(snapshot):
 for key,item in read_json(snapshot/'index.json').items():
  p=pathlib.Path(key);remove(p)
  if not item['exists']:continue
  p.parent.mkdir(parents=True,exist_ok=True)
  if 'link' in item:p.symlink_to(item['link'])
  else:
   source=snapshot/item['slot']
   if source.is_dir():shutil.copytree(source,p,symlinks=True)
   else:shutil.copy2(source,p)
  for rel,(uid,gid) in item.get('owners',{}).items():os.chown(p if rel=='.' else p/rel,uid,gid,follow_symlinks=False)
def user_directory(path,account):
 missing=[];q=path
 while not q.exists():missing.append(q);q=q.parent
 safe(path)
 for q in reversed(missing):q.mkdir();os.chown(q,account.pw_uid,account.pw_gid)
def own(path,account):
 for p in [path,*path.rglob('*')]:os.chown(p,account.pw_uid,account.pw_gid,follow_symlinks=False)
def loader_state():
 def query(action):return subprocess.run(['systemctl',action,'--quiet','plugin_loader.service'],capture_output=True).returncode==0
 return {'active':query('is-active'),'enabled':query('is-enabled')}
def finish_loader(before):
 command('systemctl','daemon-reload')
 if before['enabled']:command('systemctl','enable','plugin_loader.service')
 else:subprocess.run(['systemctl','disable','plugin_loader.service'],capture_output=True)
 if before['active']:command('systemctl','start','plugin_loader.service')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['install','undo','wifi','wifi-undo']);p.add_argument('--user',required=True)
 for option in ['decky','tdp','glyphs']:p.add_argument('--'+option,action='store_true')
 p.add_argument('--30w',dest='preset30',action='store_true');a=p.parse_args();account=preflight(a.user)
 home=pathlib.Path(account.pw_dir);brew=home/'homebrew'
 state=home/'.local/state/aokzoe-a1-extras';safe(state);state.mkdir(parents=True,exist_ok=True,mode=0o700);state.chmod(0o700)
 with (state/'lock').open('w') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if a.action in ['wifi','wifi-undo']:
   print(wifi.trial(state/'wifi.json') if a.action=='wifi' else wifi.restore(state/'wifi.json'));return
  safe(brew);before=loader_state()
  if a.action=='undo':
   if not (state/'original/index.json').is_file():raise RuntimeError('No extras backup exists')
   subprocess.run(['systemctl','stop','plugin_loader.service'],capture_output=True)
   restore(state/'original');finish_loader(read_json(state/'loader-before.json'))
   print('Extras restored. Reboot to end any running plugin effects. Hardware tweaks have their own undo.');return
  if a.preset30:a.tdp=True
  if a.tdp or a.glyphs:a.decky=True
  if not a.decky:raise RuntimeError('Choose at least one optional extra')
  existing=(brew/'services/PluginLoader').is_file()
  if before['active'] and not existing:raise RuntimeError('Existing Decky uses an unfamiliar layout; review required')
  if a.tdp and (brew/'plugins/PowerControl').exists():raise RuntimeError('PowerControl is installed. Remove the competing TDP controller in Decky before installing SimpleDeckyTDP.')
  pins=read_json(REPO/'extras/packages.json')
  with tempfile.TemporaryDirectory(prefix='a1-extras-') as t:
   temp=pathlib.Path(t);packages={};keys=([] if existing else ['decky','service'])+(['tdp'] if a.tdp else [])+(['css','glyphs'] if a.glyphs else [])
   for key in keys:
    archive=temp/(key+'.download');download(pins[key],archive)
    packages[key]=unpack(archive,temp/key,'tar' if key=='glyphs' else 'zip') if key in ['tdp','css','glyphs'] else archive
   if a.tdp:
    if read_json(packages['tdp']/'plugin.json').get('name')!='SimpleDeckyTDP' or read_json(packages['tdp']/'package.json').get('version')!=pins['tdp']['version']:raise RuntimeError('Unknown TDP plugin schema')
   if a.glyphs:
    css=packages['css'];theme=packages['glyphs'];manifest=read_json(theme/'theme.json')
    supported=re.search(r'CSS_LOADER_VER\s*=\s*(\d+)',(css/'css_theme.py').read_text())
    if not supported or manifest.get('manifest_version',99)>int(supported[1]) or 'AOKZOE A1' not in manifest.get('patches',{}).get('Handheld',{}).get('values',{}):raise RuntimeError('Incompatible CSS Loader or glyph theme')
   settings=brew/'settings/SimpleDeckyTDP/settings.json';theme_path=brew/'themes/handheld-controller-glyphs'
   paths=[KEEP]+([brew/'services',UNIT,LINK] if not existing else [])+([brew/'plugins/SimpleDeckyTDP',settings] if a.tdp else [])+([brew/'plugins/SDH-CssLoader',theme_path] if a.glyphs else [])
   steam=next((x.resolve() for x in [home/'.local/share/Steam',home/'.steam/steam'] if x.is_dir()),None)
   if not existing:
    if steam is None or not steam.is_relative_to(home):raise RuntimeError('Start Steam once before installing Decky')
    paths.append(steam/'.cef-enable-remote-debugging')
   for path in paths:safe(path,leaf=(path!=LINK))
   save(paths,temp/'before');save(paths,state/'original',extend=True)
   if not (state/'loader-before.json').exists():write_json(state/'loader-before.json',before)
   if existing:command('systemctl','stop','plugin_loader.service')
   try:
    KEEP.parent.mkdir(parents=True,exist_ok=True)
    KEEP.write_text('/etc/systemd/system/plugin_loader.service\n/etc/systemd/system/multi-user.target.wants/plugin_loader.service\n/etc/atomic-update.conf.d/91-aokzoe-a1-extras.conf\n')
    if not existing:
     services=brew/'services';user_directory(services,account)
     shutil.copyfile(packages['decky'],services/'PluginLoader');(services/'PluginLoader').chmod(0o755)
     (services/'.loader.version').write_text('v'+pins['decky']['version']+'\n')
     service=packages['service'].read_text().replace('${HOMEBREW_FOLDER}',str(brew))
     if '${HOMEBREW_FOLDER}' in service:raise RuntimeError('Unknown Decky service template')
     UNIT.parent.mkdir(parents=True,exist_ok=True);UNIT.write_text(service);UNIT.chmod(0o644)
     (services/'.systemd').mkdir(exist_ok=True);(services/'.systemd/plugin_loader-release.service').write_text(service);(services/'.systemd/plugin_loader-backup.service').write_text(service)
     marker=steam/'.cef-enable-remote-debugging';marker.touch();os.chown(marker,account.pw_uid,account.pw_gid);own(services,account)
    for key,target in [('tdp',brew/'plugins/SimpleDeckyTDP'),('css',brew/'plugins/SDH-CssLoader'),('glyphs',theme_path)]:
     if key not in packages:continue
     previous={name:read_json(target/name) for name in ['config_USER.json','config_ROOT.json'] if (target/name).exists()} if key=='glyphs' else {}
     remove(target);user_directory(target.parent,account);shutil.copytree(packages[key],target)
     if key=='glyphs':
      for name in ['config_USER.json','config_ROOT.json']:write_json(target/name,glyph_preset(previous.get(name,{})))
     own(target,account)
    if a.preset30:
     user_directory(settings.parent,account)
     write_json(settings,tdp_preset(read_json(settings)));os.chown(settings,account.pw_uid,account.pw_gid)
    command('systemctl','daemon-reload');command('systemctl','enable','plugin_loader.service')
    if existing and before['active']:command('systemctl','start','plugin_loader.service')
   except BaseException:
    subprocess.run(['systemctl','stop','plugin_loader.service'],capture_output=True);restore(temp/'before');finish_loader(before);raise
   print('Optional extras installed. Reboot, then open Decky in Gaming Mode. The selected 30 W preset applies when SimpleDeckyTDP loads; firmware may clamp actual power. Undo is available in Set Up A1 Extras.')
if __name__=='__main__':
 try:main()
 except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,zipfile.BadZipFile,tarfile.TarError) as e:print('Extras setup stopped: '+str(e),file=sys.stderr);sys.exit(1)
