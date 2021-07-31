import sys
import PySimpleGUI as pySGUI

from utils import *

class GUInterface:
    def __init__(self, ignored_files_file, folder, name):
        self.folder = folder
        self.name = name
        self.ignored_paths = IgnoredPathsStorage(ignored_files_file)
        self.selected_path = None
        self.layout = [
            [pySGUI.Text('Ignored Paths:', size=(70, 1)), pySGUI.Button('Exit')],
            [pySGUI.Listbox(values=[str(x) for x in self.ignored_paths.paths], size=(90, 20), enable_events=True, key="LB")],
            [pySGUI.Button("Add File", key="_ADD_FILE"), pySGUI.Button("Add Folder", key="_ADD_FOLDER"), pySGUI.Button("Remove Selected", key="_REMOVE_SELECTED", disabled=True)]
            ]
        self.wnd = pySGUI.Window(f'{name}: Ignored Paths Editor', layout=self.layout, size=(650, 440))

    def run(self):
        while True:
            event, values = self.wnd.Read()
            if event in (None, 'Exit'):
                sys.exit()
            elif event == "LB":
                if len(values["LB"]) > 0:
                    self.selected_path = values["LB"][0]
                else:
                    self.selected_path = None
            elif event == "_ADD_FOLDER":
                _folder = pySGUI.popup_get_folder("Select a folder to add to the ignore list")
                if _folder is not None:
                    self.ignored_paths.paths.add(_folder.replace('\\', '/'))
                    self.ignored_paths.save()
            elif event == "_ADD_FILE":
                _file = pySGUI.popup_get_file("Select a file to add to the ignore list")
                if _file is not None:
                    self.ignored_paths.paths.add(_file.replace('\\', '/'))
                    self.ignored_paths.save()
            elif event == "_REMOVE_SELECTED":
                try:
                    self.ignored_paths.paths.remove(self.selected_path)
                    self.selected_path = None
                except:
                    pass
                finally:
                    self.ignored_paths.save()
            self.wnd.Element("LB").Update(values=[str(x) for x in self.ignored_paths.paths])
            self.wnd.Element("_REMOVE_SELECTED").Update(disabled=self.selected_path is None)


if __name__ == '__main__':
    if len(sys.argv) == 4:
        gui = GUInterface(sys.argv[1], sys.argv[2], sys.argv[3])
        gui.run()
    else:
        pySGUI.Popup('Incorrect number of arguments passed. {0}/3 required - ProjectIgnoredPathsFilePath, ProjectPath, ProjectName'.format(len(sys.argv)-1))
