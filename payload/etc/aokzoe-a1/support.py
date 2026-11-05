#!/usr/bin/python3
"""Original AOKZOE A1 support without replacing vendor system files."""
import hashlib,json,os,pathlib,re,subprocess,sys,tempfile
BASE=pathlib.Path('/etc/aokzoe-a1')
EDID_SHA256='85a76fda934a88aa08fe6c2575da82a834160071a8e76c20de16cb79d3003e70'
ARGS='drm.edid_firmware=eDP-1:edid/aokzoea1ar07_edid.bin firmware_class.path=/etc/aokzoe-a1/firmware video=eDP-1:panel_orientation=left_side_up'
def log(s): print('AOKZOE A1: '+s,file=sys.stderr)
def model_ok():
 try:return pathlib.Path('/sys/class/dmi/id/sys_vendor').read_text().strip()=='AOKZOE' and pathlib.Path('/sys/class/dmi/id/product_name').read_text().strip()=='AOKZOE A1 AR07'
 except OSError:return False
def enabled():return model_ok() and not (BASE/'disabled').exists()
def standby_guard():
 if not model_ok():raise RuntimeError('Standby fix requires the original AOKZOE A1 AR07')
 if pathlib.Path('/sys/class/dmi/id/bios_version').read_text().strip()!='1.30' or pathlib.Path('/sys/class/dmi/id/bios_date').read_text().strip()!='12/06/2022':raise RuntimeError('Unreviewed BIOS; standby wake policy unchanged')
 false_button=pathlib.Path('/sys/devices/platform/PNP0C0C:00/power/wakeup')
 fixed_button=pathlib.Path('/sys/devices/platform/LNXPWRBN:00/power/wakeup')
 if not false_button.is_file() or not fixed_button.is_file():raise RuntimeError('Power-button device layout changed; standby fix requires review')
 if fixed_button.read_text().strip()!='enabled':raise RuntimeError('Physical power-button wake must remain enabled')
 if pathlib.Path('/sys/bus/acpi/devices/PNP0C0C:00/path').read_text().strip()!=r'\_SB_.PWRB':raise RuntimeError('ACPI button namespace changed')
 if 'deep' not in pathlib.Path('/sys/power/mem_sleep').read_text().replace('[','').replace(']','').split():raise RuntimeError('Firmware does not expose deep sleep')
 # AML for Notify (\\_SB.PWRB, 0x80), inside this firmware's SPTS method.
 # Reject different firmware rather than applying a model-only workaround.
 aml=pathlib.Path('/sys/firmware/acpi/tables/DSDT').read_bytes()
 start=aml.find(b'SPTS\x01')
 signature=bytes.fromhex('86 5c 2e 5f 53 42 5f 50 57 52 42 0a 80')
 if start<0 or signature not in aml[start:start+256]:raise RuntimeError('Firmware sleep notification differs; standby fix requires review')
 return false_button
def standby():
 if not enabled():return
 p=standby_guard()
 previous=BASE/'state/wake-before'
 if not previous.exists():atomic_write(previous,p.read_bytes(),0o600)
 p.write_text('disabled\n')
 log('False firmware sleep-entry wake disabled; physical power-button wake retained')
def atomic_write(p,data,mode=0o644):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.a1-',dir=p.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);os.fchmod(f.fileno(),mode);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.lexists(tmp):os.unlink(tmp)
def firmware_ok():
 b=(BASE/'firmware/edid/aokzoea1ar07_edid.bin').read_bytes()
 if hashlib.sha256(b).hexdigest()!=EDID_SHA256:raise RuntimeError('EDID payload checksum mismatch')
def esp_mount_info(data):
 def mounts(rows):
  for row in rows:
   yield row
   yield from mounts(row.get('children',[]))
 candidates=[f for f in mounts(data.get('filesystems',[])) if f.get('target')=='/esp' and f.get('fstype')=='vfat']
 if not candidates:raise RuntimeError('The FAT boot partition is not mounted at /esp')
 return candidates[-1]
def stage_esp():
 firmware_ok()
 # Access a directory entry to trigger SteamOS's /esp automount before probing.
 with os.scandir('/esp') as entries:next(entries,None)
 raw=subprocess.check_output(['findmnt','--json','--types','vfat','--output','TARGET,SOURCE,FSTYPE,UUID','--target','/esp'],text=True)
 fs=esp_mount_info(json.loads(raw));uuid=fs.get('uuid')
 if not uuid:
  uuid=subprocess.check_output(['blkid','--probe','--match-tag','UUID','--output','value',fs['source']],text=True).strip()
 if not re.fullmatch(r'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}',uuid or ''):raise RuntimeError('Could not read the FAT boot partition UUID')
 payload=(BASE/'edid.cpio').read_bytes()
 p=pathlib.Path('/esp/aokzoe-a1/edid.cpio')
 if not p.is_file() or p.read_bytes()!=payload:atomic_write(p,payload)
 return uuid

def first_entry(template):
 m=re.search(r"(?ms)^menuentry [^\n]*\{\n.*?^\}",template)
 if not m:raise RuntimeError('Vendor GRUB template has no recognized simple entry')
 return m.group()
def make_entry(template,esp_uuid):
 if not re.fullmatch(r'[0-9a-fA-F]{4}-[0-9a-fA-F]{4}',esp_uuid):raise RuntimeError('Invalid shared EFI UUID')
 s=first_entry(template)
 linux=re.compile(r'(?m)^(\s*(?:steamenv_boot\s+)?linux(?:efi)?\s+)(\S+)([^\n]*)$')
 initrd=re.compile(r'(?m)^(\s*initrd(?:efi)?\s+)([^\n]+)$')
 if len(linux.findall(s))!=1 or len(initrd.findall(s))!=1:raise RuntimeError('Unrecognized vendor kernel/initramfs commands; keeping stock boot entries')
 kernel=linux.search(s).group(2)
 if not re.fullmatch(r'/boot/vmlinuz-[a-zA-Z0-9._+\-]+',kernel):raise RuntimeError('Unrecognized kernel path; keeping stock boot entries')
 s=re.sub(r"^menuentry '[^']*'","menuentry 'SteamOS - AOKZOE A1'",s,count=1)
 s=s.replace('gnulinux-simple-','aokzoe-a1-')
 def patch_linux(m):
  tail=re.sub(r'(?<!\S)aokzoe_a1.stock=1(?!\S)','',m.group(3))
  return m.group(1)+m.group(2)+tail+' '+ARGS+' aokzoe_a1.compat=1'
 s=linux.sub(patch_linux,s)
 s=initrd.sub(lambda m:m.group(1)+m.group(2)+' ($a1esp)/aokzoe-a1/edid.cpio',s)
 s=s.replace('\n','\n\tinsmod part_gpt\n\tinsmod fat\n\tsearch --no-floppy --fs-uuid --set=a1esp '+esp_uuid+'\n',1)
 return s+'\n'
def grub():
 if not enabled():return
 try:
  # Read the current release's vendor generator, never a cached older copy.
  p=subprocess.run(['/etc/grub.d/10_linux'],capture_output=True,text=True,timeout=45)
  if p.returncode:raise RuntimeError('Vendor GRUB generator failed; keeping stock entries')
  first_entry(p.stdout)
  uuid=stage_esp()
  entry=make_entry(p.stdout,uuid)
  print(entry)
 except (OSError,RuntimeError,subprocess.SubprocessError) as e:log(str(e))
def persistent_files(manifest):
 # Image-seeded undo files must also be copied up before the first A/B update.
 names=list(manifest['files'])
 state=BASE/'state'
 if state.is_dir():names.extend(str(p) for p in state.rglob('*') if p.is_file() or p.is_symlink())
 return list(dict.fromkeys(names))
def bootstrap():
 if not enabled():return
 manifest=json.loads((BASE/'manifest.json').read_text())
 # Atomic self-copy forces these base-image files into writable /etc's overlay.
 # RAUC copies the explicitly allowlisted overlay files to the updated slot.
 for name in persistent_files(manifest):
  p=pathlib.Path(name)
  if p.is_symlink():
   target=os.readlink(p);tmp=p.with_name('.a1-link-'+p.name)
   if os.path.lexists(tmp):tmp.unlink()
   tmp.symlink_to(target);os.replace(tmp,p)
  else:atomic_write(p,p.read_bytes(),p.stat().st_mode&0o777)
 uuid=stage_esp()
 standby_status="unsupported firmware; unchanged"
 try:
  standby();standby_status="firmware PWRB wake disabled; fixed physical button wake enabled"
 except (OSError,RuntimeError) as e:log(str(e))
 status={'persistent_configuration':'seeded into etc overlay','shared_efi_uuid':uuid,'model':'AOKZOE A1 AR07','root_files_modified':False,'standby_fix':standby_status}
 atomic_write('/var/lib/aokzoe-a1/status.json',(json.dumps(status,indent=2)+'\n').encode())
 log('Configuration preserved in /etc overlay; boot firmware checked')
def audio():
 if not enabled():return
 try:
  version=subprocess.check_output(['/usr/bin/wireplumber','--version'],text=True,stderr=subprocess.STDOUT)
  if not re.search(r'\b0\.5\.\d+',version):raise RuntimeError('WirePlumber version needs review; using vendor audio configuration')
  folder=pathlib.Path('/run/wireplumber/wireplumber.conf.d')
  if not folder.is_dir():raise RuntimeError('Vendor audio configuration path changed; using stock audio')
  atomic_write(folder/'90-aokzoe-a1-analog.conf',(BASE/'audio.conf').read_bytes())
 except (OSError,RuntimeError,subprocess.SubprocessError) as e:log(str(e))
if __name__=='__main__':
 try:
  {'grub':grub,'bootstrap':bootstrap,'audio':audio,'standby':standby}[sys.argv[1]]()
 except (OSError,RuntimeError,ValueError,KeyError,IndexError,subprocess.SubprocessError) as e:
  log(str(e));sys.exit(1)
