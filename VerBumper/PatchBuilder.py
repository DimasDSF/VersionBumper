import pathlib
import sys
import os
import PySimpleGUI as pySGUI
import shutil

from utils import *

class GUInterface:
    def __init__(self, name, projectpath, current_coderev):
        self.name = name
        self.project_path = projectpath
        self.cur_coderev = int(current_coderev)
        self.changelogs_path = str(pathlib.Path(f"./ProjectData/{name}/ChangeLogs").absolute())
        self.patches_folder = str(pathlib.Path(f'./ProjectData/{name}/Patches').absolute())
        self.selected_coderev = None
        self.changelog = None
        self.changes_paths = set()
        self.layout = [
            [pySGUI.Text('CodeRev Changelogs:', size=(28, 1)), pySGUI.Text('List of Changed Files: ')],
            [pySGUI.Listbox(values=[x.name for x in os.scandir(self.changelogs_path)], size=(30, 20), enable_events=True, key="LB"), pySGUI.Listbox(values=[], size=(90, 20), key="_CHANGES")],  # noqa
            [pySGUI.Button("Build a patch", key="_BUILD_PATCH", disabled=True), pySGUI.Button('Exit')],
            ]
        self.wnd = pySGUI.Window(f'{name}: Ignored Paths Editor', layout=self.layout, size=(800, 440))

    def run(self):
        while True:
            event, values = self.wnd.Read()
            if event in (None, 'Exit'):
                sys.exit()
            elif event == "LB":
                if len(values["LB"]) > 0:
                    self.selected_coderev = os.path.splitext(values["LB"][0])[0]
                    self.changelog = ChangeLog(self.name, coderev=self.selected_coderev)
                else:
                    self.selected_coderev = None
                    self.changelog = None
                if self.changelog is not None:
                    self.changes_paths = get_changed_files_paths_from_changelogs(self.changelog, self.cur_coderev, self.name)
            elif event == "_BUILD_PATCH":
                _patch_dir = f'{self.patches_folder}/{self.changelog.coderev}#{self.cur_coderev}'
                if not os.path.exists(_patch_dir):
                    os.makedirs(_patch_dir, exist_ok=True)
                for _pf in self.changes_paths:
                    debug_print(f'    Copying {_pf}')
                    _end_dir = _patch_dir
                    if _pf.startswith(self.project_path):
                        _patch_subdir = os.path.dirname(_pf)[len(self.project_path):].replace('\\', '/')
                        if _patch_subdir.startswith('/'):
                            _patch_subdir = _patch_subdir[1:]
                        debug_print(f"      Patch subdir: {_patch_subdir}")
                        _end_dir = os.path.join(_patch_dir, _patch_subdir).replace('\\', '/')
                        if not os.path.exists(_end_dir):
                            debug_print(f"      Creating {_end_dir}")
                            os.makedirs(_end_dir, exist_ok=True)
                    debug_print(f'      to {_end_dir}')
                    shutil.copy2(_pf, _end_dir)
                # Get the version file as well if it exists
                try:
                    shutil.copy2(os.path.join(self.project_path, 'version.json'), _patch_dir)
                except:
                    pass
                os.system(f'start {_patch_dir}/')
            self.wnd.Element("_CHANGES").Update(values=[x[len(self.project_path) if x.startswith(self.project_path) else 0:] for x in self.changes_paths])
            self.wnd.Element("_BUILD_PATCH").Update(disabled=self.selected_coderev is None)


if __name__ == '__main__':
    if len(sys.argv) == 4:
        gui = GUInterface(sys.argv[1], sys.argv[2], sys.argv[3])
        gui.run()
    else:
        pySGUI.Popup('Incorrect number of arguments passed. {0}/3 required - ProjectName, ProjectPath, CurrentCodeRev'.format(len(sys.argv)-1))
