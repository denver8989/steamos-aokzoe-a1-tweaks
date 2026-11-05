import sys,importlib.util,io,json,os,pathlib,subprocess,tarfile,tempfile,unittest,zipfile
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'tools'))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,R/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
e=load('extras','tools/extras.py');d=load('desktop','tools/desktop.py');b=load('extras_bundle','tools/extras_bundle.py');s=load('support2','payload/etc/aokzoe-a1/support.py')
class Extras(unittest.TestCase):
 def test_30w_preserves_other_settings(self):
  original={'tdpProfiles':{'default':{'tdp':15,'cpuBoost':True},'42':{'tdp':12}},'maxTdp':25,'advanced':{'other':False},'enableTdpProfiles':True}
  updated=e.tdp_preset(original)
  self.assertEqual(updated['tdpProfiles']['default']['tdp'],30);self.assertEqual(updated['maxTdp'],30)
  self.assertTrue(updated['tdpProfiles']['default']['cpuBoost']);self.assertEqual(updated['tdpProfiles']['42']['tdp'],12)
  self.assertTrue(updated['enableTdpProfiles']);self.assertEqual(original['tdpProfiles']['default']['tdp'],15)
  self.assertTrue(updated['advanced']['enableTdpControl']);self.assertFalse(updated['advanced']['other'])
 def test_theme_a1(self):
  original={'Handheld':'Anbernic Win600','Other':'Yes'};preset=e.glyph_preset(original)
  self.assertTrue(preset['active']);self.assertEqual(preset['Handheld'],'AOKZOE A1');self.assertEqual(preset['Other'],'Yes');self.assertNotEqual(original['Handheld'],'AOKZOE A1')
 def test_archives_refuse_traversal_and_links(self):
  with tempfile.TemporaryDirectory() as t:
   folder=pathlib.Path(t);archive=folder/'bad.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape','unsafe')
   with self.assertRaises(RuntimeError):e.unpack(archive,folder/'zipout','zip')
   archive=folder/'bad.tar.gz'
   with tarfile.open(archive,'w:gz') as z:
    item=tarfile.TarInfo('theme/link');item.type=tarfile.SYMTYPE;item.linkname='/etc';z.addfile(item)
   with self.assertRaises(RuntimeError):e.unpack(archive,folder/'tarout','tar')
   self.assertFalse((folder/'escape').exists())
 def test_executable_zip(self):
  with tempfile.TemporaryDirectory() as t:
   folder=pathlib.Path(t);archive=folder/'valid.zip'
   with zipfile.ZipFile(archive,'w') as z:
    item=zipfile.ZipInfo('plugin/bin/tool');item.external_attr=(0o100755<<16);z.writestr(item,b'synthetic')
   root=e.unpack(archive,folder/'out','zip');self.assertTrue(os.access(root/'bin/tool',os.X_OK))
 def test_snapshot_restores_directory_and_link(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);plugin=root/'plugin';plugin.mkdir();(plugin/'settings').write_text('original');link=root/'link';link.symlink_to('plugin')
   snapshot=root/'snapshot';e.save([plugin,link,root/'absent'],snapshot)
   (plugin/'settings').write_text('changed');link.unlink();(root/'absent').mkdir();(root/'absent/file').write_text('new')
   e.restore(snapshot);self.assertEqual((plugin/'settings').read_text(),'original');self.assertTrue(link.is_symlink());self.assertFalse((root/'absent').exists())
 def test_refuse_recovery_before_any_install(self):
  values={'/sys/class/dmi/id/sys_vendor':'AOKZOE','/sys/class/dmi/id/product_name':'AOKZOE A1 AR07','/etc/os-release':'ID=steamos\nVARIANT_ID=steamdeck-oobe\n'}
  with patch.object(e.os,'geteuid',return_value=0),patch.object(pathlib.Path,'read_text',autospec=True,side_effect=lambda p:values[str(p)]),self.assertRaisesRegex(RuntimeError,'Install SteamOS completely'):e.preflight('deck')
 def test_self_contained_bundle(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);b.stage_extras(R,root)
   installed=root/'etc/aokzoe-a1/extras'
   self.assertTrue((installed/'extras/packages.json').is_file());self.assertTrue((installed/'tools/desktop.py').is_file());self.assertTrue((installed/'tools/extras.py').is_file());self.assertTrue((installed/'tools/wifi.py').is_file())
 def test_launcher_does_not_overwrite_user_file(self):
  with tempfile.TemporaryDirectory() as t:
   file=pathlib.Path(t)/'desktop';file.write_text('user content')
   with patch.object(s,'extras_desktop',return_value=(file,None)):s.seed_extras_launcher();s.remove_extras_launcher()
   self.assertEqual(file.read_text(),'user content')
 def test_image_gui_argv_keeps_special_filenames_literal(self):
  with tempfile.TemporaryDirectory() as t:
   output=str(pathlib.Path(t)/'output $ literal.img');source='/tmp/source $(literal).img.bz2'
   with patch.object(d,'dialog',side_effect=[source,output,'clean','']),patch.object(d,'terminal') as terminal:d.image()
   args=terminal.call_args[0][0];self.assertEqual(args[-2:],[source,output]);self.assertIn('patch-image.py',args[2])
 def test_extras_gui_dependency_choices(self):
  with patch.object(d.wifi,'adapters',return_value=[]),patch.object(d,'dialog',side_effect=['install','"30w" "glyphs"','']),patch.object(d,'terminal') as terminal:d.extras()
  args=terminal.call_args[0][0]
  for flag in ['--decky','--tdp','--30w','--glyphs']:self.assertIn(flag,args)
 def test_wifi_backend_does_not_query_or_install_decky(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as t:
   account=SimpleNamespace(pw_dir=t,pw_uid=os.getuid(),pw_gid=os.getgid())
   with patch.object(e.sys,'argv',['extras.py','wifi','--user','fixture']),patch.object(e,'preflight',return_value=account),patch.object(e.wifi,'trial',return_value='fixture trial') as trial,patch.object(e,'loader_state',side_effect=AssertionError('Decky queried')),patch.object(e,'download',side_effect=AssertionError('Download attempted')):e.main()
   self.assertEqual(trial.call_args[0][0],pathlib.Path(t)/'.local/state/aokzoe-a1-extras/wifi.json')
 def test_wifi_gui_gate_and_independent_action(self):
  adapter={'label':'RZ608 / MT7921K'}
  with patch.object(d.wifi,'adapters',return_value=[adapter]),patch.object(d,'dialog',side_effect=['wifi','']) as dialog,patch.object(d,'terminal') as terminal:d.extras()
  self.assertIn('wifi',dialog.call_args_list[0][0]);self.assertIn('wifi',terminal.call_args[0][0]);self.assertNotIn('--decky',terminal.call_args[0][0])
  with patch.object(d.wifi,'adapters',return_value=[]),patch.object(d,'dialog',side_effect=['wifi-undo','']) as dialog,patch.object(d,'terminal'):d.extras()
  self.assertNotIn('wifi',dialog.call_args_list[0][0]);self.assertIn('wifi-undo',dialog.call_args_list[0][0])
if __name__=='__main__':unittest.main()
