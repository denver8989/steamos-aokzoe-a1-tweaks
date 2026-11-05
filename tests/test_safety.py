"""No hardware, privileged operations, network or account files used by this suite."""
import fnmatch,hashlib,importlib.util,json,os,pathlib,subprocess,tempfile,unittest
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,R/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
s=load('support','payload/etc/aokzoe-a1/support.py');i=load('install','tools/install.py');g=load('guard','recovery/a1-disk-guard.py');im=load('image','tools/patch-image.py');assets=load('assets','tools/assets.py')
TEMPLATE="""set linux_gfx_mode=x
menuentry 'SteamOS' --id 'gnulinux-simple-test' {
 insmod btrfs
 steamenv_boot linux /boot/vmlinuz-linux-valve-test root=UUID=public-fixture aokzoe_a1.stock=1
 initrd /boot/amd-ucode.img /boot/initramfs-linux-valve-test.img
}
"""
class Boot(unittest.TestCase):
 def test_current_and_changed_kernel(self):
  for t in [TEMPLATE,TEMPLATE.replace('valve-test','future-123')]:
   entry=s.make_entry(t,'ABCD-1234');self.assertIn('aokzoe_a1.compat=1',entry);self.assertNotIn('stock=1',entry);self.assertIn('($a1esp)/aokzoe-a1/edid.cpio',entry)
 def test_unknown_generator_fails(self):
  for t in ['',TEMPLATE.replace(' linux ',' chainloader '),TEMPLATE.replace('/boot/vmlinuz-linux-valve-test','($root)/kernel'),TEMPLATE.replace(' initrd ',' badinitrd ')]:
   with self.assertRaises(RuntimeError):s.make_entry(t,'ABCD-1234')
 def test_bad_uuid(self):
  with self.assertRaises(RuntimeError):s.make_entry(TEMPLATE,'bad; reboot')
 def test_generator_falls_back(self):
  with patch.object(s,'enabled',return_value=True),patch.object(s.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'unknown boot syntax','')),patch.object(s,'stage_esp') as stage,patch('builtins.print'):
   s.grub();stage.assert_not_called()
 def test_automount(self):
  fs={'filesystems':[{'target':'/esp','fstype':'autofs','children':[{'target':'/esp','fstype':'vfat','uuid':'ABCD-1234'}]}]}
  self.assertEqual(s.esp_mount_info(fs)['uuid'],'ABCD-1234')
class Firmware(unittest.TestCase):
 def fixture(self,p):
  values={'/sys/class/dmi/id/bios_version':'1.30','/sys/class/dmi/id/bios_date':'12/06/2022','/sys/devices/platform/LNXPWRBN:00/power/wakeup':'enabled','/sys/bus/acpi/devices/PNP0C0C:00/path':r'\_SB_.PWRB','/sys/power/mem_sleep':'s2idle [deep]'}
  return values[str(p)]
 def test_reviewed(self):
  aml=b'headerSPTS\x01'+bytes.fromhex('86 5c 2e 5f 53 42 5f 50 57 52 42 0a 80')
  with patch.object(s,'model_ok',return_value=True),patch.object(pathlib.Path,'is_file',return_value=True),patch.object(pathlib.Path,'read_text',autospec=True,side_effect=self.fixture),patch.object(pathlib.Path,'read_bytes',return_value=aml):
   self.assertEqual(str(s.standby_guard()),'/sys/devices/platform/PNP0C0C:00/power/wakeup')
 def test_refuses_model(self):
  with patch.object(s,'model_ok',return_value=False),self.assertRaises(RuntimeError):s.standby_guard()
 def test_firmware_and_sole_button(self):
  changes=[('/sys/class/dmi/id/bios_version','2.0'),('/sys/class/dmi/id/bios_date','01/01/2026'),('/sys/devices/platform/LNXPWRBN:00/power/wakeup','disabled'),('/sys/bus/acpi/devices/PNP0C0C:00/path',r'\_SB_.OTHER'),('/sys/power/mem_sleep','[s2idle]')]
  for key,value in changes:
   def altered(p):return value if str(p)==key else self.fixture(p)
   with patch.object(s,'model_ok',return_value=True),patch.object(pathlib.Path,'is_file',return_value=True),patch.object(pathlib.Path,'read_text',autospec=True,side_effect=altered),self.assertRaises(RuntimeError):s.standby_guard()
  for aml in [b'no method',b'SPTS\x01'+bytes(256)+bytes.fromhex('86 5c 2e 5f 53 42 5f 50 57 52 42 0a 80')]:
   with patch.object(s,'model_ok',return_value=True),patch.object(pathlib.Path,'is_file',return_value=True),patch.object(pathlib.Path,'read_text',autospec=True,side_effect=self.fixture),patch.object(pathlib.Path,'read_bytes',return_value=aml),self.assertRaises(RuntimeError):s.standby_guard()
 def test_missing_endpoint(self):
  with patch.object(s,'model_ok',return_value=True),patch.object(pathlib.Path,'read_text',autospec=True,side_effect=self.fixture),patch.object(pathlib.Path,'is_file',return_value=False),self.assertRaises(RuntimeError):s.standby_guard()
 def test_nonblocking_suspend(self):
  drop=(R/'payload/etc/systemd/system/systemd-suspend.service.d/aokzoe-a1.conf').read_text();self.assertIn('ExecStartPre=-/',drop)
class Transaction(unittest.TestCase):
 def test_restore_reinstall_and_undo(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t)/'root';root.mkdir();(root/'etc').mkdir();(root/'etc/existing').write_text('baseline');(root/'etc/existing').chmod(0o640)
   names=['etc/existing','etc/new','etc/link'];original=pathlib.Path(t)/'original';i.capture(root,names,original)
   for _ in range(2):
    (root/'etc/existing').write_text('installed');(root/'etc/new').write_text('installed');(root/'etc/link').symlink_to('../original')
    before=pathlib.Path(t)/('before'+str(_));i.capture(root,names,before);(root/'etc/existing').write_text('failed install');i.restore(root,before)
    self.assertEqual((root/'etc/existing').read_text(),'installed');i.restore(root,original)
    self.assertEqual((root/'etc/existing').read_text(),'baseline');self.assertFalse((root/'etc/new').exists());self.assertFalse((root/'etc/link').is_symlink());self.assertEqual((root/'etc/existing').stat().st_mode&0o777,0o640)
 def test_payload_service_link_reinstall(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t)/'root';root.mkdir()
   i.copy_payload(R/'payload',root)
   link=root/('etc/'+i.REL)
   self.assertTrue(link.is_symlink());self.assertTrue(link.resolve().is_file())
   i.copy_payload(R/'payload',root)
   self.assertTrue(link.is_symlink());self.assertTrue(link.resolve().is_file())
 def test_refuse_symlink_parent(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);(root/'etc').symlink_to(root)
   with self.assertRaises(RuntimeError):i.capture(root,['etc/new'],root/'backup')
 def test_image_seeded_undo_is_copied_up(self):
  with tempfile.TemporaryDirectory() as t:
   base=pathlib.Path(t);(base/'state/original').mkdir(parents=True)
   index=base/'state/original/index.json';index.write_text('{}')
   helper=base/'state/undo-support.py';helper.write_text('# fixture')
   with patch.object(s,'BASE',base):
    names=s.persistent_files({'files':['/etc/aokzoe-a1/support.py']})
   self.assertIn(str(index),names);self.assertIn(str(helper),names)
 def test_allowlist(self):
  manifest=json.loads((R/'payload/etc/aokzoe-a1/manifest.json').read_text());patterns=(R/'payload/etc/atomic-update.conf.d/90-aokzoe-a1.conf').read_text().splitlines()
  for name in manifest['files']+['/etc/aokzoe-a1/state/original/index.json','/etc/aokzoe-a1/state/original/files/etc/grub.d/09_aokzoe_a1','/etc/aokzoe-a1/state/wake-before']:
   self.assertTrue(any(fnmatch.fnmatch(name,p) for p in patterns if p.startswith('/')),name)
  self.assertEqual(manifest['version'],4)
class Disk(unittest.TestCase):
 def rows(self):return [{'path':'/dev/nvme0n1','type':'disk','tran':'nvme','ro':False,'size':128*1024**3,'serial':'SYNTHETIC','log-sec':512}]
 def test_selection(self):
  rows=self.rows();self.assertEqual(len(g.eligible(rows,set())),1);self.assertEqual(g.eligible(rows,{'/dev/nvme0n1'}),[])
  for key,val in [('ro',True),('tran','usb'),('size',1024),('type','part')]:
   row=dict(rows[0]);row[key]=val;self.assertEqual(g.eligible([row],set()),[])
 def test_identity_and_sector(self):
  rows=self.rows()
  with patch.object(g,'inspect',return_value=(rows,set())),patch.object(g.subprocess,'run') as run:
   with self.assertRaises(RuntimeError):g.prepare('/dev/nvme0n1','OTHER')
   rows[0]['log-sec']=4096
   with self.assertRaises(RuntimeError):g.prepare('/dev/nvme0n1','SYNTHETIC')
   run.assert_not_called()
 def test_swap(self):
  with patch.object(g,'inspect',return_value=(self.rows(),set())),patch.object(g,'command',return_value='/dev/mapper/test'),patch.object(g,'ancestors',return_value={'/dev/nvme0n1'}),patch.object(g.subprocess,'run') as run:
   with self.assertRaises(RuntimeError):g.prepare('/dev/nvme0n1','SYNTHETIC')
   run.assert_not_called()
class Image(unittest.TestCase):
 def test_bad_source_output(self):
  with tempfile.TemporaryDirectory() as t:
   folder=pathlib.Path(t);p=folder/'bad.img';p.write_bytes(b'unknown')
   with self.assertRaises(RuntimeError):im.expand(p,folder/'out.img')
   self.assertFalse((folder/'out.img').exists())
   for out in [p,folder/'out.iso',pathlib.Path('/dev/a1-test.img')]:
    with self.assertRaises(RuntimeError):im.output_path(out)
 def test_unknown_vendor_script(self):
  tr=load('transform','recovery/transform.py')
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'vendor';p.write_text('unknown')
   with self.assertRaises(RuntimeError):tr.transform(p,pathlib.Path(t)/'patched')
 def test_cpio(self):
  c=assets.cpio(b'public synthetic fixture');self.assertTrue(c.startswith(b'070701'));self.assertIn(b'lib/firmware/edid/aokzoea1ar07_edid.bin',c);self.assertEqual(len(c)%512,0)
 def test_asset_refusal(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'bad';p.write_bytes(b'unknown')
   with self.assertRaises(RuntimeError):assets.prepare(pathlib.Path(t)/'out',p)
if __name__=='__main__':unittest.main()
