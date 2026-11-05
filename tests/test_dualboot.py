import copy,importlib.util,json,pathlib,tempfile,unittest
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dual',R/'dualboot/a1-dualboot.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
def table():
 types=[d.GUIDS[0],'E3C9E316-0B5C-4DB8-817D-F92DF00215AE',d.GUIDS[1],'DE94BBA4-06D1-4D40-A16A-BFD50179D6AC']
 return {'label':'gpt','device':'/dev/nvme0n1','sectorsize':512,'lastlba':134217694,'partitions':[{'node':'/dev/nvme0n1p'+str(n),'start':2048+(n-1)*2097152,'size':1048576,'type':t,'uuid':'synthetic-'+str(n),'name':'Windows '+str(n)} for n,t in enumerate(types,1)]}
class DualBoot(unittest.TestCase):
 def test_trailing_layout_preserves_every_old_extent(self):
  original=table();before=copy.deepcopy(original);new=d.layout(original)
  self.assertEqual(original,before);self.assertEqual([p['index'] for p in new],list(range(5,13)));self.assertEqual([p['name'] for p in new],d.NAMES)
  self.assertGreaterEqual(new[0]['start'],max(p['start']+p['size'] for p in original['partitions']))
  self.assertEqual(new[-1]['start']+new[-1]['size']-1,original['lastlba'])
 def test_refuse_small_gap_or_existing_steamos(self):
  for change in ['space','label','sector','gpt','overlap','mixed']:
   data=table()
   if change=='space':data['lastlba']=10000000
   elif change=='label':data['partitions'][0]['name']='esp'
   elif change=='sector':data['sectorsize']=4096
   elif change=='gpt':data['label']='dos'
   elif change=='overlap':data['partitions'][1]['start']=data['partitions'][0]['start']
   else:data['partitions'][1]['node']='/dev/nvme1n1p2'
   with self.assertRaises(RuntimeError):d.layout(data)
 def test_existing_partition_changes_refused(self):
  original=table();plan={'original':original};changed=copy.deepcopy(original);changed['partitions'][2]['size']+=1
  with self.assertRaises(RuntimeError):d.verify_original(plan,changed)
 def test_created_exact_match(self):
  original=table();plan={'disk':'/dev/nvme0n1','original':original,'new':d.layout(original)};created=copy.deepcopy(original)
  for p in plan['new']:created['partitions'].append(dict(p,node=plan['disk']+'p'+str(p['index']),uuid='synthetic-new'))
  d.verify_created(plan,created);created['partitions'][-1]['start']-=1
  with self.assertRaises(RuntimeError):d.verify_created(plan,created)
 def test_identity_refusal_before_gpt_write(self):
  original=table();plan={'disk':'/dev/nvme0n1','serial':'EXPECTED','disk_bytes':64*1024**3,'original':original,'fingerprint':d.fingerprint(original),'new':d.layout(original)}
  with patch.object(d,'context',return_value=({'path':plan['disk'],'serial':'OTHER','size':plan['disk_bytes']},original)),patch.object(d.subprocess,'run') as run:
   with self.assertRaises(RuntimeError):d.create(plan)
   run.assert_not_called()
 def test_table_race_refused_before_gpt_write(self):
  original=table();plan={'disk':'/dev/nvme0n1','serial':'EXPECTED','disk_bytes':64*1024**3,'original':original,'fingerprint':d.fingerprint(original),'new':d.layout(original)};changed=copy.deepcopy(original);changed['partitions'][1]['uuid']='changed'
  with patch.object(d,'context',return_value=({'path':plan['disk'],'serial':plan['serial'],'size':plan['disk_bytes']},changed)),patch.object(d.subprocess,'run') as run:
   with self.assertRaises(RuntimeError):d.create(plan)
   run.assert_not_called()
 def test_boot_mapping_verifies_new_partitions(self):
  original=table();plan={'disk':'/dev/nvme0n1','original':original,'new':d.layout(original)}
  def response(*args):
   letter=args[args.index('--partset')+1];target=args[-1]
   entry=plan['new'][0] if target=='/esp' else plan['new'][1 if letter=='A' else 2] if target=='/efi' else plan['new'][3 if letter=='A' else 4]
   return json.dumps({'filesystems':[{'target':target,'source':plan['disk']+'p'+str(entry['index']),'fstype':'btrfs' if target=='/' else 'vfat'}]})
  with patch.object(d,'command',side_effect=response):d.verify_boot_mapping(plan)
 def test_windows_efi_mapping_refused(self):
  original=table();plan={'disk':'/dev/nvme0n1','original':original,'new':d.layout(original)}
  with patch.object(d,'command',return_value=json.dumps({'filesystems':[{'target':'/esp','source':'/dev/nvme0n1p1','fstype':'vfat'}]})),self.assertRaises(RuntimeError):d.verify_boot_mapping(plan)
 def test_unknown_upstream_refused(self):
  spec=importlib.util.spec_from_file_location('dual_transform',R/'dualboot/transform.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'source';p.write_text('unknown')
   with self.assertRaises(RuntimeError):m.transform(p,pathlib.Path(t)/'output')
if __name__=='__main__':unittest.main()
