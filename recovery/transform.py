#!/usr/bin/env python3
"""Apply only to the reviewed Valve recovery script, retaining its native install flow."""
import hashlib,json,pathlib,subprocess,tempfile
HERE=pathlib.Path(__file__).resolve().parent
def transform(source,destination):
 source=pathlib.Path(source);destination=pathlib.Path(destination)
 known=json.loads((HERE/'vendor.json').read_text())
 if hashlib.sha256(source.read_bytes()).hexdigest()!=known['stock_sha256']:raise RuntimeError('Unknown Valve repair script; refusing transform. Review a newer image first.')
 with tempfile.TemporaryDirectory(prefix='a1-vendor-') as t:
  p=pathlib.Path(t)/'repair_device.sh';p.write_bytes(source.read_bytes())
  subprocess.run(['patch','--batch','--fuzz=0',str(p),str(HERE/'repair-device.patch')],check=True,capture_output=True)
  if hashlib.sha256(p.read_bytes()).hexdigest()!=known['patched_sha256']:raise RuntimeError('Patched Valve script checksum mismatch')
  subprocess.run(['bash','-n',str(p)],check=True)
  destination.write_bytes(p.read_bytes());destination.chmod(0o755)
