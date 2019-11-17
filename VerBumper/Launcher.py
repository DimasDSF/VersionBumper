import json
import sys
import os
import datetime
import PySimpleGUI as pySGUI
import subprocess

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
            print('No previous projects data found.')
        except json.decoder.JSONDecodeError:
            print('Failure to read malformed previous projects data file.')
        except Exception as e:
            print('Failure to read projects data.\n{0}: {1}.'.format(type(e).__name__, e.args[0]))
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
            print('Failure to write projects.\n{0}: {1}'.format(type(e).__name__, e.args[0]))

class GUInterface:
    def __init__(self):
        self.config = Config('config.json')
        self.selectedproject = None
        self.updater_window = None
        self.layout = [[pySGUI.Text('Projects:', size=(25, 1)), pySGUI.Button('Exit'),pySGUI.Button('Reload Data', key='_RELOAD_DATA_', size=(10, 1))],
                      [pySGUI.Listbox(values=list(map(lambda x: str(x), self.config.db['projects'].keys())), size=(45, 15), enable_events=True, key="ProjectList")],
                      [pySGUI.Text(text=self.get_project_data_string(), size=(40, 4), key="_PROJECT_INFO_")],
                      [pySGUI.Button("Add Project", key="_ADD_PROJECT_"), pySGUI.Button("Remove Project", key="_REMOVE_PROJECT_", disabled=True), pySGUI.Button("Run Project", key="_RUN_PROJECT_", disabled=True)],
                      [pySGUI.Button("Edit Project Directory", key="_EDIT_PROJECT_FOLDER_", disabled=True), pySGUI.Button("Edit Project Name", key="_EDIT_PROJECT_NAME_", disabled=True)]
                     ]
        self.wnd = pySGUI.Window('Projects', layout=self.layout, size=(390, 460))

    def get_project_data_string(self):
        return 'Selected Project:{0}\nPath:\n{1}'.format(self.selectedproject, str(self.get_selected_project_path()))

    def get_project_db_data(self, project):
        return self.config.db['projects'][project] if project in self.config.db['projects'].keys() else None

    def get_selected_project_path(self):
        if self.get_project_db_data(self.selectedproject) is not None:
            return self.get_project_db_data(self.selectedproject).get('path', None)
        return None

    def reload_project_list(self):
        self.wnd.Refresh()
        self.wnd.Element("ProjectList").Update(values=list(map(lambda x: str(x), self.config.db['projects'].keys())))

    def run(self):
        while True:
            event, values = self.wnd.Read()
            if event in (None, 'Exit'):
                sys.exit()
            elif event == "_ADD_PROJECT_":
                _GetFolder = pySGUI.PopupGetFolder("Select a Project Folder")
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
                    self.selectedproject = values["ProjectList"][0]
            elif event == "_RUN_PROJECT_":
                self.updater_window = subprocess.Popen(['pythonw', 'VersionFileManager.py', str(self.get_project_db_data(self.selectedproject)['path']), self.selectedproject], shell=False, stdin=None,
                                                       stdout=None, stderr=None)
                if self.updater_window is not None:
                    self.updater_window.poll()
                    if self.updater_window.returncode is None:
                        sys.exit()
            elif event == "_EDIT_PROJECT_FOLDER_":
                _GetFolder = pySGUI.PopupGetFolder("Select New Project Folder", default_path=self.get_selected_project_path())
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
            elif event == "_RELOAD_DATA_":
                self.reload_project_list()
            self.wnd.Element("_PROJECT_INFO_").Update(value=self.get_project_data_string())
            self.wnd.Element("_EDIT_PROJECT_FOLDER_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_EDIT_PROJECT_NAME_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_REMOVE_PROJECT_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))
            self.wnd.Element("_RUN_PROJECT_").Update(disabled=(self.get_project_db_data(self.selectedproject) is None))

if __name__ == "__main__":
    GUI = GUInterface()
    GUI.run()
