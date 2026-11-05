"""Stage our post-install GUI locally; no third-party download or plugin install here."""
import pathlib,shutil
FILES=['tools/desktop.py','tools/extras.py','tools/wifi.py','extras/packages.json']
def stage_extras(repo,stage):
 destination=stage/'etc/aokzoe-a1/extras'
 for name in FILES:
  q=destination/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,q);q.chmod(0o644)
