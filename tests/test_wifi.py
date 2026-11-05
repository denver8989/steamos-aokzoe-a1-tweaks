"""Wi-Fi trial tests use synthetic sysfs and command mocks only."""
import pathlib,sys,tempfile,unittest
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
import wifi
UUID='11111111-2222-3333-4444-555555555555'
OTHER='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
ADAPTER={'interface':'wlan0','vendor':'0x14c3','device':'0x0608','driver':'mt7921e','label':'RZ608 / MT7921K'}
class Wifi(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.state=self.root/'wifi.json'
  self.profile=3;self.radio='on';self.uuid=UUID;self.calls=[];self.fail_radio=False
  self.patch=patch.object(wifi,'adapters',return_value=[dict(ADAPTER)]);self.patch.start()
  self.runner=patch.object(wifi,'run',side_effect=self.run_command);self.runner.start()
 def tearDown(self):self.runner.stop();self.patch.stop();self.temp.cleanup()
 def run_command(self,*args):
  self.calls.append(args)
  if args[:3]==('nmcli','--get-values','GENERAL.CON-UUID'):return self.uuid
  if args[:3]==('nmcli','--get-values','802-11-wireless.powersave'):return str(self.profile)+' (fixture)'
  if args[:3]==('nmcli','connection','modify'):self.profile=int(args[-1]);return ''
  if args==('iw','dev','wlan0','get','power_save'):return 'Power save: '+self.radio
  if args[:5]==('iw','dev','wlan0','set','power_save'):
   if self.fail_radio and args[-1]=='off':raise RuntimeError('synthetic driver refusal')
   self.radio=args[-1];return ''
  raise AssertionError('Unexpected command '+repr(args))
 def mutations(self):return [x for x in self.calls if x[:3]==('nmcli','connection','modify') or 'set' in x]
 def test_sysfs_requires_exact_pci_and_bound_driver(self):
  self.patch.stop()
  interface=self.root/'net/wlan0';device=interface/'device';device.mkdir(parents=True);(interface/'phy80211').mkdir()
  (device/'vendor').write_text('0x14c3');(device/'device').write_text('0x0608');(device/'driver').symlink_to('/synthetic/drivers/mt7921e')
  self.assertEqual(wifi.adapters(self.root/'net'),[ADAPTER])
  for vendor,card,driver in [('0x8086','0x0608','mt7921e'),('0x14c3','0x7902','mt7921e'),('0x14c3','0x0608','iwlwifi')]:
   (device/'vendor').write_text(vendor);(device/'device').write_text(card);(device/'driver').unlink();(device/'driver').symlink_to('/synthetic/drivers/'+driver)
   self.assertEqual(wifi.adapters(self.root/'net'),[])
 def test_trial_and_exact_undo(self):
  wifi.trial(self.state)
  self.assertEqual((self.profile,self.radio),(2,'off'));self.assertEqual(wifi.read(self.state)['before'],3)
  self.assertEqual(self.state.stat().st_mode&0o777,0o600)
  wifi.restore(self.state);self.assertEqual((self.profile,self.radio),(3,'on'));self.assertFalse(self.state.exists())
 def test_backup_written_before_first_mutation(self):
  original=self.run_command
  def guarded(*args):
   if args[:3]==('nmcli','connection','modify'):self.assertTrue(self.state.is_file())
   return original(*args)
  with patch.object(wifi,'run',side_effect=guarded):wifi.trial(self.state)
 def test_reapply_preserves_original(self):
  wifi.trial(self.state);original=self.state.read_bytes();self.calls=[]
  wifi.trial(self.state);self.assertEqual(self.state.read_bytes(),original);self.assertEqual(self.mutations(),[])
 def test_already_off_no_changes_or_backup(self):
  self.radio='off';wifi.trial(self.state);self.assertEqual(self.mutations(),[]);self.assertFalse(self.state.exists());self.assertEqual(self.profile,3)
 def test_unsupported_or_ambiguous_adapter_no_commands(self):
  for values in [[],[dict(ADAPTER),dict(ADAPTER)]]:
   with patch.object(wifi,'adapters',return_value=values),self.assertRaises(RuntimeError):wifi.trial(self.state)
  self.assertEqual(self.calls,[]);self.assertFalse(self.state.exists())
 def test_disconnected_no_mutation(self):
  self.uuid='--'
  with self.assertRaisesRegex(RuntimeError,'Connect'):wifi.trial(self.state)
  self.assertEqual(self.mutations(),[]);self.assertFalse(self.state.exists())
 def test_failed_live_change_rolls_back(self):
  self.fail_radio=True
  with self.assertRaisesRegex(RuntimeError,'synthetic'):wifi.trial(self.state)
  self.assertEqual((self.profile,self.radio),(3,'on'));self.assertFalse(self.state.exists())
 def test_failed_rollback_keeps_backup(self):
  original=self.run_command
  def fail(*args):
   if args[:5]==('iw','dev','wlan0','set','power_save'):raise RuntimeError('driver failed')
   return original(*args)
  with patch.object(wifi,'run',side_effect=fail),self.assertRaisesRegex(RuntimeError,'rollback'):wifi.trial(self.state)
  self.assertEqual(wifi.read(self.state)['before'],3)
 def test_undo_does_not_overwrite_later_edit(self):
  wifi.trial(self.state);self.profile=1;self.calls=[]
  with self.assertRaisesRegex(RuntimeError,'edited'):wifi.restore(self.state)
  self.assertEqual(self.mutations(),[]);self.assertTrue(self.state.exists())
 def test_undo_profile_even_if_adapter_removed(self):
  wifi.trial(self.state);self.calls=[]
  with patch.object(wifi,'adapters',return_value=[]):wifi.restore(self.state)
  self.assertEqual(self.profile,3);self.assertFalse(any(x[0]=='iw' for x in self.calls));self.assertFalse(self.state.exists())
 def test_undo_does_not_touch_new_connection_radio(self):
  wifi.trial(self.state);self.uuid=OTHER;self.calls=[];wifi.restore(self.state)
  self.assertEqual(self.profile,3);self.assertFalse(any(x[0]=='iw' for x in self.calls))
 def test_changed_connection_before_mutation_refused(self):
  with patch.object(wifi,'same_connection',return_value=False),self.assertRaisesRegex(RuntimeError,'changed'):wifi.trial(self.state)
  self.assertEqual(self.mutations(),[])
 def test_new_trial_on_different_network_keeps_backup(self):
  wifi.trial(self.state);original=self.state.read_bytes();self.uuid=OTHER;self.calls=[]
  with self.assertRaisesRegex(RuntimeError,'backup already'):wifi.trial(self.state)
  self.assertEqual(self.state.read_bytes(),original);self.assertEqual(self.mutations(),[])
 def test_symlink_backup_refused(self):
  target=self.root/'original';target.write_text('keep');self.state.symlink_to(target)
  with self.assertRaisesRegex(RuntimeError,'symlink'):wifi.trial(self.state)
  self.assertEqual(target.read_text(),'keep');self.assertEqual(self.calls,[])
if __name__=='__main__':unittest.main()
