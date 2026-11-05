#!/usr/bin/env python3
"""KDE file-picker and optional-extras launchers; no third-party GUI runtime."""
import os,pathlib,pwd,shlex,shutil,subprocess,sys
HERE=pathlib.Path(__file__).resolve().parent
def dialog(*args):
 p=subprocess.run(['kdialog','--title','AOKZOE A1 SteamOS Setup',*args],capture_output=True,text=True)
 if p.returncode:raise KeyboardInterrupt
 return p.stdout.strip()
def terminal(args):subprocess.Popen(['konsole','--hold','-e',*args],start_new_session=True)
def image():
 source=dialog('--getopenfilename',str(pathlib.Path.home()),'Valve recovery images (*.img.bz2 *.img)')
 if not source:return
 name=pathlib.Path(source).name
 if not name.endswith(('.img','.img.bz2')):raise RuntimeError('Select Valve’s original .img.bz2 or .img file. ISO files are not supported.')
 output=dialog('--getsavefilename',str(pathlib.Path(source).parent/'aokzoe-a1-recovery.img'),'Disk image (*.img)')
 if not output:return
 if pathlib.Path(output).exists() or pathlib.Path(output).is_symlink():raise RuntimeError('Choose a new filename. Existing images will not be overwritten.')
 workflow=dialog('--menu','Choose recovery options. Dual boot is experimental and requires at least 32 GiB unallocated at the END of the internal disk.','clean','Full reinstall only (erases internal disk)','dual','Also include Install Alongside Windows (preserve-only)')
 dialog('--yesno','Create an AOKZOE A1 recovery image?\n\nSource: '+source+'\nNew image: '+output+'\n\nAllow at least 9 GiB free. Internet is needed for the display fix. Your password will be requested in a progress terminal.\n\nAfterward, use Etcher to flash the new image to a spare USB. Keep your existing working USB intact.')
 terminal(['sudo','/usr/bin/python3',str(HERE/'patch-image.py'),source,output]+(['--include-dualboot'] if workflow=='dual' else []))
def extras():
 action=dialog('--menu','Run after SteamOS is fully installed.','install','Choose optional extras','undo','Restore previous extras')
 if action=='undo':
  dialog('--yesno','Restore the plugin files and settings saved before this extras setup? Restart afterward. Hardware tweaks have a separate undo command.')
  terminal(['sudo','/usr/bin/python3',str(HERE/'extras.py'),'undo','--user',pwd.getpwuid(os.getuid()).pw_name]);return
 values=shlex.split(dialog('--checklist','Choose the extras you want. Internet access is required.','decky','Decky Loader','off','tdp','SimpleDeckyTDP','off','30w','Set SimpleDeckyTDP default to 30 W','off','glyphs','CSS Loader + Handheld Controller Glyphs (AOKZOE A1)','off'))
 if not values:return
 choices=set(values)
 if '30w' in choices:choices.add('tdp')
 if choices&{'tdp','glyphs'}:choices.add('decky')
 text='Selected: '+', '.join({'decky':'Decky Loader (keep an existing install)','tdp':'SimpleDeckyTDP','30w':'30 W default TDP profile','glyphs':'CSS Loader and AOKZOE A1 glyphs'}[x] for x in sorted(choices))
 if '30w' in choices:text+='\n\nThe 30 W profile takes effect when SimpleDeckyTDP starts in Gaming Mode. Existing per-game profiles are retained.'
 dialog('--yesno',text+'\n\nA password will be requested in a progress terminal. Existing files will be backed up. Restart SteamOS after setup.')
 terminal(['sudo','/usr/bin/python3',str(HERE/'extras.py'),'install','--user',pwd.getpwuid(os.getuid()).pw_name,*['--'+x for x in sorted(choices)]])
if __name__=='__main__':
 try:
  if not shutil.which('kdialog') or not shutil.which('konsole'):raise RuntimeError('These launchers need KDE kdialog and Konsole. Use the terminal commands in README.md on other desktops.')
  {'image':image,'extras':extras}[sys.argv[1]]()
 except KeyboardInterrupt:pass
 except (OSError,RuntimeError,KeyError,IndexError) as e:
  if shutil.which('kdialog'):subprocess.run(['kdialog','--error',str(e)])
  else:print(str(e),file=sys.stderr)
  sys.exit(1)
