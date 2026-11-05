"""Fetch and transform upstream only while preparing the user's local image."""
import importlib.util,json,pathlib,shutil,tempfile,urllib.request
HERE=pathlib.Path(__file__).resolve().parent
def stage(destination):
 spec=importlib.util.spec_from_file_location('dual_transform',HERE/'transform.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 known=json.loads((HERE/'upstream.json').read_text());url='https://raw.githubusercontent.com/'+known['repo']+'/'+known['commit']+'/steam-os-custom-install.sh'
 with tempfile.TemporaryDirectory(prefix='a1-dual-upstream-') as t:
  p=pathlib.Path(t)/'upstream';p.write_bytes(urllib.request.urlopen(url,timeout=30).read(1024**2));m.transform(p,destination/'a1-dualboot-install.sh')
 shutil.copyfile(HERE/'a1-dualboot.py',destination/'a1-dualboot.py');(destination/'a1-dualboot.py').chmod(0o755)
