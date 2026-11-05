#!/usr/bin/env python3
"""Fetch a checksum-pinned upstream EDID; do not redistribute unlicensed firmware."""
import argparse,hashlib,pathlib,urllib.request
SHA='85a76fda934a88aa08fe6c2575da82a834160071a8e76c20de16cb79d3003e70'
URL='https://raw.githubusercontent.com/ublue-os/bazzite-firmware-nonfree/main/usr/lib/firmware/edid/aokzoea1ar07_edid.bin'
def cpio(data):
 out=bytearray()
 def entry(name,blob,mode,ino):
  name=name.encode()+b'\0'
  values=[ino,mode,0,0,1,0,len(blob),0,0,0,0,len(name),0]
  out.extend(b'070701'+''.join(f'{v:08x}' for v in values).encode()+name)
  out.extend(b'\0'*((-len(out))%4));out.extend(blob);out.extend(b'\0'*((-len(out))%4))
 for i,name in enumerate(['lib','lib/firmware','lib/firmware/edid'],1):entry(name,b'',0o40755,i)
 entry('lib/firmware/edid/aokzoea1ar07_edid.bin',data,0o100644,4)
 entry('TRAILER!!!',b'',0,5);out.extend(b'\0'*((-len(out))%512))
 return bytes(out)
def prepare(folder,source=None):
 data=pathlib.Path(source).read_bytes() if source else urllib.request.urlopen(URL,timeout=30).read(65537)
 if hashlib.sha256(data).hexdigest()!=SHA:raise RuntimeError('Upstream EDID checksum differs; manual review required')
 if len(data)%128 or data[:8]!=bytes.fromhex('00ffffffffffff00') or any(sum(data[i:i+128])%256 for i in range(0,len(data),128)):raise RuntimeError('Invalid EDID')
 folder=pathlib.Path(folder);p=folder/'firmware/edid/aokzoea1ar07_edid.bin';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 (folder/'edid.cpio').write_bytes(cpio(data))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output');p.add_argument('--edid');a=p.parse_args();prepare(a.output,a.edid)
