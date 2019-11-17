import json
import sys
import os
import time
import datetime
import PySimpleGUI as pySGUI
import subprocess

mtz = datetime.timezone(datetime.timedelta(hours=3))
notzformat = '{:%d-%m-%Y %H:%M:%S}'

class VerFile(object):
    def __init__(self, file):
        self.file = file
        self.data = {}
        self.coderev = 0
        self.verdata = dict()
        self.ready = False
        self.load()

    def load(self, force=False):
        if not self.ready or force:
            try:
                with open(self.file, "r") as data:
                    self.data = json.load(data)
            except FileNotFoundError:
                print('No previous versioning data found.')
            except json.decoder.JSONDecodeError:
                print('Failure to read malformed previous versioning data file.')
            except Exception as e:
                print('Failure to read previous versioning data.\n{0}: {1}.'.format(type(e).__name__, e.args[0]))
            else:
                self.coderev = int(self.data['coderev'])
                verstring = self.data.get('version', None)
                if verstring is not None:
                    _vdata = verstring.split('-')
                    if len(_vdata) > 1:
                        self.verdata['AV'] = _vdata[1]
                    else:
                        self.verdata['AV'] = ""
                    _vdata = _vdata[0].split('.')
                    self.verdata['PV'] = int(_vdata[0])
                    self.verdata['MJV'] = int(_vdata[1])
                    self.verdata['MNV'] = int(_vdata[2])
                    self.ready = True
            finally:
                if self.ready is False:
                    self.verdata['AV'] = 'not_set'
                    self.verdata['PV'] = 0
                    self.verdata['MJV'] = 0
                    self.verdata['MNV'] = 0
                    self.coderev = -1
                    self.ready = True
                    self.save()

    def save(self):
        if self.ready:
            curtime = datetime.datetime.now()
            self.data = {
                "version": "{0}.{1}.{2}{3}".format(self.verdata['PV'], self.verdata['MJV'], self.verdata['MNV'],
                                                   '-{}'.format(self.verdata['AV']) if len(
                                                       self.verdata['AV']) > 0 else ""),
                "coderev": "{0}".format(self.coderev),
                "buildstamp": round(curtime.timestamp()),
                "buildtime": notzformat.format(curtime.astimezone(mtz))
            }
            try:
                with open(self.file, "w") as data:
                    json.dump(self.data, data, indent=4)
            except Exception as e:
                print('Failure to write versioning data.\n{0}: {1}'.format(type(e).__name__, e.args[0]))


class CSession(object):
    def __init__(self, verf, prod_log_folder):
        self.starttime = datetime.datetime.now().astimezone(mtz)
        self.endtime = None
        self.verd = verf
        self.plfolder = prod_log_folder
        self.startrev = verf.coderev
        self.pauses = []
        self.curpausestarttime = None

    def pause(self):
        if self.curpausestarttime is None:
            self.curpausestarttime = time.time()
            return self.curpausestarttime

    def unpause(self):
        if self.curpausestarttime is not None:
            self.pauses.append(round(time.time() - self.curpausestarttime))
            self.curpausestarttime = None

    def end(self):
        self.endtime = datetime.datetime.now().astimezone(mtz)
        pauses = 0
        for p in self.pauses:
            pauses += p
        slength = round((self.endtime - self.starttime).seconds)
        sessions = None
        endcoderev = self.verd.coderev
        if self.startrev != endcoderev:
            try:
                with open('{0}/{1}.json'.format(self.plfolder, self.starttime.date()), "r") as plog:
                    sessions = json.load(plog)
            except FileNotFoundError:
                pass
            except json.decoder.JSONDecodeError:
                pass
            except Exception:
                pass
            sessionaudit = {
                "sessionstart": notzformat.format(self.starttime),
                "sessionend": notzformat.format(datetime.datetime.now().astimezone(mtz)),
                "full_length": slength,
                "pause_duration": pauses,
                "duration": (slength - pauses),
                "productivity": round(((slength - pauses) / slength) * 100, 2),
                "code_revisions": endcoderev - self.startrev,
                "t_per_revision": round((slength - pauses) / (endcoderev - self.startrev), 1)
            }
            if sessions is not None:
                sessions.append(sessionaudit)
            else:
                sessions = [
                    sessionaudit
                ]
            with open('{0}/{1}.json'.format(self.plfolder, self.starttime.date()), "w") as plog:
                json.dump(sessions, plog, indent=4)


def parse_version_info_to_string(data, with_av=True, text=True):
    av = ('-' + data.get('AV', '')) if len(data.get('AV', '')) > 0 else ''
    return f"{'Current Version: ' if text else ''}{data.get('PV', '')}.{data.get('MJV', '')}.{data.get('MNV', '')}{av if with_av else ''}"


def parse_code_rev_string(data):
    return f"Code Revision: {data}"


def parse_build_time(data):
    return f"Built: {data}"

def get_prodlogger_button_text(state):
    return f"{'Launch Productivity Logger' if state else 'End Productivity Logger Session'}"

class GUInterface:
    def __init__(self, path, name):
        self.cses = None
        self.changes_made = False
        self.add_ver_changed = False
        self.manual_version_entry_active = False
        self.prod_log_reader_inst = None
        if not os.path.exists('ProdLogs/'):
            os.mkdir('ProdLogs/')
        if not os.path.exists(os.path.join('ProdLogs', name)):
            os.mkdir(os.path.join('ProdLogs', name))
        self.prod_log_folder = os.path.join('ProdLogs', name)
        self.forceupdatecoderev = False
        self.vf = VerFile(os.path.join(path, 'version.json'))
        self.main_gui_layout = [[pySGUI.Text(parse_version_info_to_string(self.vf.verdata), key="_VERSION_TEXT_", size=(25, 1)),
                                pySGUI.Button("Exit", key="_EXIT_BUTTON_"), pySGUI.Button("Cancel", key="_CANCEL_CHANGES_", disabled=True)],
                                [pySGUI.Text(parse_code_rev_string(self.vf.coderev), key="_CODEREV_TEXT_", size=(22, 1)),
                                pySGUI.Button("Save Version Data", key="_SAVE_VER_DATA_", disabled=(not self.changes_made))],
                                [pySGUI.Text(parse_build_time(self.vf.data['buildtime']), key="_BUILDTIME_TEXT_", size=(22, 1)),
                                pySGUI.Button("ProdLog Reader", key="_PROD_LOG_READER_")],
                                [pySGUI.Text("Prod Tracker Start Time: "),
                                pySGUI.Text("N/A", size=(15, 1), key="_PRODLOGGER_START_TIME_TEXT_")],
                                [pySGUI.Button("Major Update", key="_UPD_PROJ_"),
                                pySGUI.Button("Launch Productivity Logger", key="_PRODLOGGER_START_BUTTON_")],
                                [pySGUI.Button("Minor Update", key="_UPD_MAJ_"), pySGUI.Button("Increment CodeRev", key="_PL_INCR_CR_")],
                                [pySGUI.Button("Patch Update", key="_UPD_MIN_"), pySGUI.Button("Pause", key="_PL_PAUSE_", disabled=True)],
                                [pySGUI.Button("Unlock Version Entry", key="_MAN_VER_ENT_BUTTON_"), pySGUI.Text("SubVersion: "),
                                pySGUI.InputText(default_text=self.vf.verdata['AV'], enable_events=True, size=(10, 1), key="_UPD_ADD_VER_")],
                                [pySGUI.Text("Manual Version Entry: "),
                                pySGUI.InputText(default_text=parse_version_info_to_string(self.vf.verdata, False, False), size=(20, 1),
                                                 key="_MANUAL_VER_INPUT_", disabled=True)]
                                ]
        self.updater_gui_wnd = pySGUI.Window("Version Updater", self.main_gui_layout, disable_close=True)
        self.run_gui()

    def run_gui(self):
        while True:
            if self.vf.coderev == -1:
                _CodeRevStart = pySGUI.PopupGetText('Enter Code Revision', title="Code Revision Missing")
                if _CodeRevStart is not None:
                    if isinstance(_CodeRevStart, str):
                        if _CodeRevStart.isnumeric():
                            if int(_CodeRevStart) >= 0:
                                self.vf.coderev = int(_CodeRevStart)
                                self.forceupdatecoderev = True
                                self.vf.save()
                            else:
                                pySGUI.Popup('Incorrect Code Revision Entered. Needs to be >= 0.')
                        else:
                            pySGUI.Popup('Incorrect Code Revision Entered. Needs to be an Integer.')
                    elif isinstance(_CodeRevStart, int):
                        if _CodeRevStart >= 0:
                            self.vf.coderev = _CodeRevStart
                            self.forceupdatecoderev = True
                            self.vf.save()
                        else:
                            pySGUI.Popup('Incorrect Code Revision Entered. Needs to be >= 0.')
                    else:
                        pySGUI.Popup("Incorrect Input Type.")
                else:
                    sys.exit()
            else:
                event, values = self.updater_gui_wnd.Read(timeout=10 if self.forceupdatecoderev else None)
                if self.forceupdatecoderev is True:
                    self.updater_gui_wnd.Element("_CODEREV_TEXT_").Update(value=parse_code_rev_string(self.vf.coderev))
                    self.forceupdatecoderev = False
                else:
                    if event == '_UPD_PROJ_':
                        self.vf.verdata["PV"] += 1
                        self.vf.verdata["MJV"] = 0
                        self.vf.verdata["MNV"] = 0
                        self.changes_made = True
                    elif event == '_UPD_MAJ_':
                        self.vf.verdata["MJV"] += 1
                        self.vf.verdata["MNV"] = 0
                        self.changes_made = True
                    elif event == '_UPD_MIN_':
                        self.vf.verdata["MNV"] += 1
                        self.changes_made = True
                    elif event == '_UPD_ADD_VER_':
                        if self.updater_gui_wnd.Element('_UPD_ADD_VER_').Get() != self.vf.verdata['AV']:
                            self.add_ver_changed = True
                        else:
                            self.add_ver_changed = False
                    elif event == '_PL_INCR_CR_':
                        self.vf.coderev += 1
                        self.changes_made = True
                    elif event == '_SAVE_VER_DATA_':
                        if self.cses is not None and self.cses.startrev == self.vf.coderev:
                            self.vf.coderev += 1
                        adver = self.updater_gui_wnd.Element('_UPD_ADD_VER_').Get()
                        self.vf.verdata['AV'] = adver
                        self.vf.save()
                        self.changes_made = False
                        self.add_ver_changed = False
                    elif event == '_CANCEL_CHANGES_':
                        self.vf.load(True)
                        self.updater_gui_wnd.Element('_UPD_ADD_VER_').Update(value=self.vf.verdata['AV'])
                        self.updater_gui_wnd.Element("_MANUAL_VER_INPUT_").Update(
                            value=parse_version_info_to_string(self.vf.verdata, False, False))
                        self.changes_made = False
                        self.add_ver_changed = False
                    elif event == '_PRODLOGGER_START_BUTTON_':
                        if self.cses is None:
                            self.cses = CSession(self.vf, str(self.prod_log_folder))
                        else:
                            self.cses.end()
                            self.cses = None
                        self.updater_gui_wnd.Element("_PL_PAUSE_").Update(disabled=(self.cses is None))
                        self.updater_gui_wnd.Element("_PRODLOGGER_START_TIME_TEXT_").Update(
                            value=notzformat.format(self.cses.starttime) if self.cses else 'N/A')
                    elif event == '_MAN_VER_ENT_BUTTON_':
                        if not self.manual_version_entry_active:
                            self.manual_version_entry_active = True
                            self.updater_gui_wnd.Element("_MANUAL_VER_INPUT_").Update(disabled=(not self.manual_version_entry_active))
                            self.updater_gui_wnd.Element("_MAN_VER_ENT_BUTTON_").Update(text='Manual Version Entry')
                        else:
                            vdata = self.updater_gui_wnd.Element('_MANUAL_VER_INPUT_').Get()
                            if len(vdata) > 0:
                                if len(vdata.split('.')) == 3:
                                    vdata = vdata.split('.')
                                    self.vf.verdata['PV'] = int(vdata[0])
                                    self.vf.verdata['MJV'] = int(vdata[1])
                                    self.vf.verdata['MNV'] = int(vdata[2])
                                    self.manual_version_entry_active = False
                                    self.updater_gui_wnd.Element("_MAN_VER_ENT_BUTTON_").Update(text='Unlock Version Entry')
                                    self.updater_gui_wnd.Element("_MANUAL_VER_INPUT_").Update(
                                        disabled=(not self.manual_version_entry_active))
                                    self.changes_made = True
                                else:
                                    self.updater_gui_wnd.Element("_MANUAL_VER_INPUT_").Update(
                                        value=parse_version_info_to_string(self.vf.verdata, False, False))
                            else:
                                self.updater_gui_wnd.Element("_MANUAL_VER_INPUT_").Update(
                                    value=parse_version_info_to_string(self.vf.verdata, False, False))
                    elif event == '_PL_PAUSE_':
                        if self.cses.curpausestarttime is None:
                            self.cses.pause()
                        else:
                            self.cses.unpause()
                        self.updater_gui_wnd.Element("_PL_PAUSE_").Update(
                            text='Pause' if self.cses.curpausestarttime is None else 'Paused since {}'.format(
                                notzformat.format(datetime.datetime.fromtimestamp(round(self.cses.curpausestarttime)))))
                    elif event == "_PROD_LOG_READER_":
                        if self.prod_log_reader_inst is not None:
                            self.prod_log_reader_inst.poll()
                            if self.prod_log_reader_inst.returncode is not None:
                                self.prod_log_reader_inst = None
                        if self.prod_log_reader_inst is None:
                            self.prod_log_reader_inst = subprocess.Popen(['pythonw', 'ProdLogReader.py', str(self.prod_log_folder)], shell=False, stdin=None,
                                                                         stdout=None, stderr=None)
                    elif event == '_EXIT_BUTTON_':
                        if self.prod_log_reader_inst is not None:
                            if self.prod_log_reader_inst.poll() is None:
                                self.prod_log_reader_inst.kill()
                        sys.exit()
                    self.updater_gui_wnd.Element("_MANUAL_VER_INPUT_").Update(value=parse_version_info_to_string(self.vf.verdata, False, False))
                    self.updater_gui_wnd.Element("_PRODLOGGER_START_BUTTON_").Update(text=get_prodlogger_button_text(self.cses is None))
                    self.updater_gui_wnd.Element("_PRODLOGGER_START_BUTTON_").Update(
                        disabled=(self.changes_made or self.add_ver_changed))
                    self.updater_gui_wnd.Element("_VERSION_TEXT_").Update(value=parse_version_info_to_string(self.vf.verdata))
                    self.updater_gui_wnd.Element("_CODEREV_TEXT_").Update(value=parse_code_rev_string(self.vf.coderev))
                    self.updater_gui_wnd.Element("_BUILDTIME_TEXT_").Update(value=parse_build_time(self.vf.data['buildtime']))
                    self.updater_gui_wnd.Element("_CANCEL_CHANGES_").Update(disabled=(not self.changes_made and not self.add_ver_changed))
                    self.updater_gui_wnd.Element("_EXIT_BUTTON_").Update(
                        disabled=(self.cses is not None or self.changes_made or self.add_ver_changed))
                    self.updater_gui_wnd.Element("_SAVE_VER_DATA_").Update(disabled=(not self.changes_made and not self.add_ver_changed))

if __name__ == '__main__':
    if len(sys.argv) == 3:
        GUIinst = GUInterface(sys.argv[1], sys.argv[2])
    else:
        pySGUI.Popup('Incorrect number of arguments passed. {0}/2 required - Path, ProjectName'.format(len(sys.argv)-1))
        raise(RuntimeError('Incorrect number of arguments passed. 2 required - Path, ProjectName'))
