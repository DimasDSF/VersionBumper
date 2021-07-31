import json
import pathlib
import sys
import os
import time
import PySimpleGUI as pySGUI
import subprocess

from utils import *

DOUBLE_CLICK_MAX_INTERVAL = 0.25

class Config:
    def __init__(self, file):
        self.file = file
        self.db = None
        self.ready = False
        self.load()

    def load(self):
        try:
            with open(self.file) as data:
                self.db = json.load(data)
        except FileNotFoundError:
            debug_print('No previous projects data found.')
        except json.decoder.JSONDecodeError:
            debug_print('Failure to read malformed previous projects data file.')
        except Exception as e:
            debug_print('Failure to read projects data.\n{0}: {1}.'.format(type(e).__name__, e.args[0]))
        else:
            self.ready = True
        finally:
            if self.ready is not True:
                self.db = {
                    "projects": {}
                }
                self.save()

    def save(self):
        try:
            with open(self.file, "w") as data:
                json.dump(self.db, data, indent=4)
        except Exception as e:
            debug_print('Failure to write projects.\n{0}: {1}'.format(type(e).__name__, e.args[0]))

class GUInterface:
    def __init__(self):
        self.config = Config('config.json')
        self.selectedproject = None
        self.selectedprojecttimestamp = 0
        self.updater_window = None
        self.layout = [
            [pySGUI.Text('Projects:', size=(25, 1)), pySGUI.Button('Exit'), pySGUI.Button('Reload Data', key='_RELOAD_DATA_', size=(10, 1))],
            [pySGUI.Listbox(values=list(map(lambda x: str(x), self.config.db['projects'].keys())), bind_return_key=True, select_mode=pySGUI.LISTBOX_SELECT_MODE_SINGLE, size=(47, 15), enable_events=True, key="ProjectList")],
            [pySGUI.Text(text=self.get_project_data_string(), size=(43, 5), text_color='black', background_color="lightblue", key="_PROJECT_INFO_")],
            [pySGUI.Text(text=self.get_selected_project_last_edited(), size=(40, 1), key="_UP_TO_DATE_")],
            [pySGUI.Button("Add Project", key="_ADD_PROJECT_"), pySGUI.Button("Remove Project", key="_REMOVE_PROJECT_", disabled=True), pySGUI.Button("Run Project", key="_RUN_PROJECT_", disabled=True), pySGUI.Button("Explore", key="_EXPLORE_", disabled=True)],
            [pySGUI.Button("Edit Project Directory", key="_EDIT_PROJECT_FOLDER_", disabled=True), pySGUI.Button("Edit Project Name", key="_EDIT_PROJECT_NAME_", disabled=True)],
            [pySGUI.Button("Edit Ignored Paths for Project", key="_EDIT_IGNORE_PATHS", disabled=True)]
            ]
        self.wnd = pySGUI.Window('Projects', layout=self.layout, size=(390, 520))

    def get_project_data_string(self):
        return 'Selected Project:{0}\nPath:\n{1}'.format(self.selectedproject, split_path_string_on(self.get_selected_project_path(), 40, '/'))

    def get_project_db_data(self, project):
        return self.config.db['projects'][project] if project in self.config.db['projects'].keys() else None

    def get_selected_project_path(self, *, return_incorrect: bool = False):
        if self.get_project_db_data(self.selectedproject) is not None:
            _path = self.get_project_db_data(self.selectedproject).get('path', None)
            return _path if os.path.exists(_path) or return_incorrect else None
        return None

    def get_selected_project_ignore_paths(self, as_object: bool = False):
        if self.get_project_db_data(self.selectedproject) is not None:
            _obj = IgnoredPathsStorage(str(pathlib.Path(f'./ProjectData/{self.selectedproject}/ignored_paths.json').absolute()).replace('\\', '/'))
            return _obj if as_object else _obj.paths
        return None if as_object else set()

    def get_project_last_build_timestamp(self, project):
        try:
            with open(os.path.join(self.config.db['projects'][project]['path'], 'version.json'), 'r') as vd:
                ver = json.load(vd)
                return ver['buildstamp']
        except:
            return 0

    def get_project_last_edited(self, project):
        if self.get_project_db_data(project) is not None:
            return f"Changes Built: {get_no_file_changes_after_build_text(self.get_project_last_build_timestamp(project), self.config.db['projects'][project]['path'], ignored=self.get_selected_project_ignore_paths())}"
        else:
            return "Changes Built: ?"

    def get_selected_project_last_edited(self):
        return self.get_project_last_edited(self.selectedproject)

    def reload_project_list(self):
        self.wnd.Refresh()
        self.wnd.Element("ProjectList").Update(values=list(map(lambda x: str(x), self.config.db['projects'].keys())))

    def run_project(self):
        if self.get_selected_project_path() is not None:
            self.updater_window = subprocess.Popen(
                ['pythonw' if not isDebug else 'python', 'VersionFileManager.py', str(self.get_project_db_data(self.selectedproject)['path']),
                 self.selectedproject], shell=False, stdin=None, stdout=None, stderr=None)
            if self.updater_window is not None:
                self.updater_window.poll()
                if self.updater_window.returncode is None:
                    sys.exit()
        else:
            pySGUI.Popup("Selected Project does not have a correct path setup and cannot be launched.", title="Error", button_type=pySGUI.POPUP_BUTTONS_ERROR)

    def run(self):
        while True:
            event, values = self.wnd.Read()
            if event in (None, 'Exit'):
                sys.exit()
            elif event == "_ADD_PROJECT_":
                _GetFolder = pySGUI.PopupGetFolder("Select a Project Folder")
                if _GetFolder is not None:
                    if os.path.exists(_GetFolder):
                        _GetNewName = pySGUI.PopupGetText('Enter New Project Name')
                        if _GetNewName is not None:
                            if _GetNewName not in self.config.db['projects']:
                                self.config.db['projects'][_GetNewName] = {
                                    "path": _GetFolder
                                }
                                self.selectedproject = _GetNewName
                                self.config.save()
                            else:
                                pySGUI.Popup("This Project name already exists.")
                    else:
                        pySGUI.Popup("Incorrect Directory Selected.")
                self.reload_project_list()
            elif event == "_REMOVE_PROJECT_":
                self.config.db['projects'].pop(self.selectedproject, None)
                self.reload_project_list()
                self.selectedproject = None
                self.config.save()
            elif event == "ProjectList":
                if len(values["ProjectList"]) > 0:
                    if self.selectedproject is not None:
                        if self.selectedproject == values['ProjectList'][0] and abs(time.time() - self.selectedprojecttimestamp) <= DOUBLE_CLICK_MAX_INTERVAL:
                            self.run_project()
                    self.selectedproject = values["ProjectList"][0]
                    self.selectedprojecttimestamp = time.time()
            elif event == "_RUN_PROJECT_":
                self.run_project()
            elif event == "_EXPLORE_":
                if self.selectedproject is not None:
                    if os.path.exists(self.get_selected_project_path()):
                        os.system(f'start {self.get_selected_project_path()}')
            elif event == "_EDIT_PROJECT_FOLDER_":
                _GetFolder = pySGUI.PopupGetFolder("Select New Project Folder", default_path=self.get_selected_project_path(return_incorrect=True))
                if _GetFolder is not None:
                    if os.path.exists(_GetFolder):
                        self.config.db['projects'][self.selectedproject]['path'] = _GetFolder
                        self.reload_project_list()
                        self.config.save()
                    else:
                        pySGUI.Popup("Incorrect Directory Selected.")
            elif event == "_EDIT_PROJECT_NAME_":
                _GetNewName = pySGUI.PopupGetText('Enter New Project Name')
                if _GetNewName is not None:
                    if _GetNewName not in self.config.db['projects']:
                        self.config.db['projects'][_GetNewName] = self.get_project_db_data(self.selectedproject)
                        self.config.db['projects'].pop(self.selectedproject, None)
                        self.selectedproject = _GetNewName
                        self.config.save()
                        self.reload_project_list()
                    else:
                        pySGUI.Popup("This Project name already exists.")
            elif event == "_EDIT_IGNORE_PATHS":
                if self.get_selected_project_path() is not None:
                    _ignore_path_editor_window = subprocess.Popen(
                        ['pythonw' if not isDebug else 'python', 'IgnoredPathManager.py', str(pathlib.Path(f'./ProjectData/{self.selectedproject}/ignored_paths.json').absolute()).replace('\\', '/'), str(self.get_project_db_data(self.selectedproject)['path']), self.selectedproject],
                        shell=False, stdin=None, stdout=None, stderr=None)
                    if _ignore_path_editor_window is not None:
                        _ignore_path_editor_window.wait()
                else:
                    pySGUI.Popup("Selected Project does not have a correct path setup and cannot be launched.",
                                 title="Error", button_type=pySGUI.POPUP_BUTTONS_ERROR)
            elif event == "_RELOAD_DATA_":
                self.reload_project_list()
            self.wnd.Element("_PROJECT_INFO_").Update(value=self.get_project_data_string())
            self.wnd.Element("_UP_TO_DATE_").Update(value=self.get_selected_project_last_edited())
            self.wnd.Element("_EDIT_PROJECT_FOLDER_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_EXPLORE_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_EDIT_PROJECT_NAME_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_EDIT_IGNORE_PATHS").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_REMOVE_PROJECT_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_RUN_PROJECT_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))


if __name__ == "__main__":
    GUI = GUInterface()
    GUI.run()
