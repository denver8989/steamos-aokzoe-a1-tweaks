#!/usr/bin/env python3
"""Optional official binary download. No npm, root access, credentials or sandbox changes."""
import hashlib,io,os,pathlib,shutil,sys,tarfile,tempfile,urllib.request
VERSION='0.166.0'
PACKAGES={
 'codex':'a0bf572d2f93f056c6712a6da348e96078dc84f3885fd7be67807ef389cb3978',
 'codex-code-mode-host':'7588334fd47bc4003d970b70dfd4d1e4578491b1e9baa72976a4c2d7e97590da',
 'codex-exec-server':'16f698d576fcd1d94e5e38b5c6ce48168afad1d95737b1eb2d84b3f0219ea6e3'}
def install():
 if os.geteuid()==0:raise RuntimeError('Run as the desktop user, without sudo')
 if os.uname().machine!='x86_64':raise RuntimeError('This optional recovery download is for Linux x86_64 only')
 base=pathlib.Path.home()/'.local/share/a1-codex'/VERSION
 for p in [base,*base.parents]:
  if p.is_symlink():raise RuntimeError('Refusing symlink in optional package destination')
 base.mkdir(parents=True,exist_ok=True)
 dest=base/'bin'
 if dest.exists():raise RuntimeError('Package destination already exists; inspect it before reinstalling')
 with tempfile.TemporaryDirectory(prefix='.download-',dir=base) as tmp:
  folder=pathlib.Path(tmp)
  for name,expected in PACKAGES.items():
   archive_name=name+'-x86_64-unknown-linux-musl.tar.gz'
   url='https://github.com/openai/codex/releases/download/rust-v'+VERSION+'/'+archive_name
   print('Downloading official '+archive_name,flush=True)
   archive=folder/archive_name;h=hashlib.sha256();size=0
   with urllib.request.urlopen(url,timeout=60) as response,archive.open('xb') as f:
    while True:
     b=response.read(1024**2)
     if not b:break
     size+=len(b)
     if size>512*1024**2:raise RuntimeError('Unexpectedly large package')
     h.update(b);f.write(b)
   if h.hexdigest()!=expected:raise RuntimeError('Official package checksum mismatch: '+name)
   with tarfile.open(archive,'r:gz') as tar:
    members=[m for m in tar if m.isfile() and pathlib.PurePosixPath(m.name).name in {name,name+'-x86_64-unknown-linux-musl'}]
    if len(members)!=1 or members[0].size>1024**3:raise RuntimeError('Unrecognized official package layout')
    target=folder/name
    with tar.extractfile(members[0]) as src,target.open('xb') as f:shutil.copyfileobj(src,f)
    target.chmod(0o755)
   archive.unlink()
  folder.rename(dest)
 print('Installed optional official Codex '+VERSION+' with both companion programs. Sign in separately when launched.')
if __name__=='__main__':
 try:install()
 except (OSError,RuntimeError,tarfile.TarError) as e:print('Codex download stopped: '+str(e),file=sys.stderr);sys.exit(1)
