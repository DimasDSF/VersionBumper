import json
import os
import sys
import PySimpleGUI as pySGUI

from utils import *

def fill_text_with_data(data):
    prod = data.get('productivity', 'Unknown')
    if isinstance(prod, (int, float)):
        prod = round(prod, 2)
    return f"Start Time: {data.get('sessionstart', 'Unknown')}\nEnd Time: {data.get('sessionend', 'Unknown')}\nFull Length: {format_seconds_to_str(data.get('full_length', 0))}\nPause Duration: {format_seconds_to_str(data.get('pause_duration', 0))}\nActual Duration: {format_seconds_to_str(data.get('duration', 0))}\nCode Revisions: {str(data.get('code_revisions', 'Unknown'))} | Average Revision Time: {format_seconds_to_str(data.get('t_per_revision', 0))}\nSession Productivity: {str(prod)}%"

class GUInterface:
    def __init__(self, folder):
        self.folder = folder
        self.pld = {}
        self.load()
        self.layout = [
            [pySGUI.Text('Log Dates:', size=(14, 1)), pySGUI.Text('Start Times:', size=(9, 1)), pySGUI.Button('Exit'),
             pySGUI.Button('Reload Data', key='_RELOAD_DATA_', size=(10, 1))],
            [pySGUI.Listbox(values=list(map(lambda x: str(x), self.pld.keys())), size=(14, 15), enable_events=True,
                            key="LB"),
             pySGUI.Listbox(values=[], key="SesList", enable_events=True, size=(27, 15))],
            [pySGUI.Text('_' * 48, justification='center')],
            [pySGUI.Text(fill_text_with_data({}), key="SesText")]
            ]
        self.wnd = pySGUI.Window('Productivity Log Data', layout=self.layout, size=(390, 460))

    def load(self):
        if os.path.exists(self.folder):
            for pl in os.listdir(path=self.folder):
                fn = pl.split('.')[0]
                self.pld[fn] = []
                with open(os.path.join(self.folder, pl)) as data:
                    jd = json.load(data)
                    for d in jd:
                        self.pld[fn].append(d)

    def run(self):
        while True:
            event, values = self.wnd.Read()
            if event in (None, 'Exit'):
                sys.exit()
            elif event == "LB":
                if len(values["LB"]) > 0:
                    LBSel = list(
                        map(lambda x: (str(x['sessionstart'].split(" ")[1]) + " - " + str(x['sessionend'].split(" ")[1])),
                            self.pld[values["LB"][0]]))
                    self.wnd.Element("SesList").Update(values=LBSel)
            elif event == "SesList":
                if len(values["SesList"]) > 0:
                    ses = self.wnd.Element("SesList").GetListValues()
                    dt = self.pld[values["LB"][0]][ses.index(values["SesList"][0])]
                    txt = fill_text_with_data(dt)
                    self.wnd.Element("SesText").Update(value=txt)
            elif event == "_RELOAD_DATA_":
                self.pld = {}
                self.load()
                self.wnd.Refresh()
                self.wnd.Element("LB").Update(values=list(map(lambda x: str(x), self.pld.keys())))
                self.wnd.Element("SesList").Update(values=[])


if __name__ == '__main__':
    if len(sys.argv) == 2:
        gui = GUInterface(sys.argv[1])
        gui.run()
    else:
        pySGUI.Popup('Incorrect number of arguments passed. {0}/1 required - ProjectProdLogPath'.format(len(sys.argv)-1))
