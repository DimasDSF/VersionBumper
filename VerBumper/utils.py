import json
import os
import datetime
import pathlib
import time

from typing import Optional, Set, List, Tuple

__all__ = ['recursive_fileiter', 'format_seconds_to_str', 'get_latest_file_change_in_a_folder', 'get_no_file_changes_after_build',
           'get_no_file_changes_after_build_text', 'split_path_string_on', 'get_unbuilt_changed_files', 'get_unbuilt_changed_files_text',
           'get_changed_files_paths_from_changelogs', 'replace_slashes',
           'debug_print',

           'IgnoredPathsStorage', 'ChangeLog',

           'debuglvl', 'isDebug', 'mtz', 'notzformat']

import sys

mtz = datetime.timezone(datetime.timedelta(hours=3))
notzformat = '{:%d-%m-%Y %H:%M:%S}'

debuglvl = 0
isDebug = debuglvl > 0

def debug_print(*args, sep=' ', end='\n', file=sys.stdout, flush=False, lvl=1):
    """
    print(value, ..., sep=' ', end='\n', file=sys.stdout, flush=False)

    Prints the values to a stream, or to sys.stdout by default.
    Optional keyword arguments:
    file:  a file-like object (stream); defaults to the current sys.stdout.
    sep:   string inserted between values, default a space.
    end:   string appended after the last value, default a newline.
    flush: whether to forcibly flush the stream.
    """
    if debuglvl >= lvl:
        print(*args, sep=sep, end=end, file=file, flush=flush)


def format_seconds_to_str(sec=0):
    l_time = time.gmtime(sec)
    years = int(l_time.tm_year) - 1970
    days = str((int(l_time.tm_yday) - 1) + years * 366) + 'd ' if ((int(l_time.tm_yday) - 1) + years * 366) != 0 else ""
    hours = str(l_time.tm_hour) + 'h:' if int(l_time.tm_hour) != 0 else ""
    minutes = str(l_time.tm_min) + 'm:' if int(l_time.tm_min) != 0 else ""
    seconds = time.strftime("%S", l_time)
    return '{0}{1}{2}{3}s'.format(days, hours, minutes, seconds)

def replace_slashes(instr: str):
    return instr.replace('\\', '/')

class IgnoredPathsStorage(object):
    def __init__(self, path: str):
        self.config_dir = path
        self.paths = set()
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            self.save()
        self.load()

    def load(self):
        if os.path.exists(self.config_dir):
            with open(self.config_dir, 'r') as _cfg:
                self.paths = set(json.load(_cfg))

    def save(self):
        with open(self.config_dir, 'w') as _cfg:
            json.dump(list(self.paths), _cfg, indent=4)

class ChangeLog(object):
    def __init__(self, projectname: str, coderev: int, *, create: bool = True):
        self.config_dir = str(pathlib.Path(f'./ProjectData/{projectname}/ChangeLogs/{coderev}.clog').absolute()).replace('\\', '/')
        self.coderev = coderev
        self.paths = set()
        if not os.path.exists(self.config_dir):
            if create:
                self.save()
            else:
                raise FileNotFoundError("Changelog does not exist.")
        self.load()

    def load(self):
        if os.path.exists(self.config_dir):
            with open(self.config_dir, 'r') as _cfg:
                _data: dict = json.load(_cfg)
                self.paths = set(_data.get('paths', []))
                self.coderev = _data.get('coderev', -1)

    def save(self):
        if not os.path.exists(os.path.dirname(self.config_dir)):
            os.makedirs(os.path.dirname(self.config_dir), exist_ok=True)
        with open(self.config_dir, 'w') as _cfg:
            json.dump({"coderev": self.coderev, "paths": list(self.paths)}, _cfg, indent=4)

def is_in_ignored(path: str, ignored_paths: Set[Optional[str]]):
    path = path.replace('\\', '/')
    for ip in ignored_paths:
        ip = ip.replace('\\', '/')
        debug_print(f"{path} !?= {ip}", lvl=2)
        if path.startswith(ip):
            return True
    return False

def recursive_fileiter(sdir, ignored_paths: Set[Optional[str]] = ()):
    ret = list()
    if os.path.exists(sdir):
        f: os.DirEntry
        folders = [f.path for f in os.scandir(sdir) if (f.is_dir() and not f.name.startswith("."))]
        for folder in folders:
            ret.extend(recursive_fileiter(folder, ignored_paths))
        if os.path.isfile(sdir):
            if os.path.split(sdir)[1] != "version.json" and not is_in_ignored(sdir, ignored_paths):
                ret.append(sdir)
        with os.scandir(sdir) as directory:
            for item in directory:
                item: os.DirEntry
                if item.is_file() and item.name != "version.json" and not is_in_ignored(item.path, ignored_paths):
                    ret.append(item)
    return ret

def get_latest_file_change_in_a_folder(path, ignored_paths: Set[Optional[str]] = ()):
    maxts = 0
    for f in recursive_fileiter(path, ignored_paths):
        if os.stat(f).st_mtime > maxts:
            maxts = os.stat(f).st_mtime
    return maxts

def get_unbuilt_changed_files(buildtime, path, ignored_paths: Set[Optional[str]] = ()) -> List[Tuple[os.DirEntry, datetime.datetime]]:
    _ucf = list()
    for f in recursive_fileiter(path, ignored_paths):
        if os.stat(f).st_mtime > buildtime:
            _ucf.append((f, datetime.datetime.fromtimestamp(os.stat(f).st_mtime)))
    return _ucf

def get_unbuilt_changed_files_text(filelist: list):
    _changed_file_text_format = "{0} - {1}"
    _changed_files_text = [_changed_file_text_format.format('/'.join(x[0].path.split('\\')[1:]), notzformat.format(x[1])) for x in filelist]
    return "\n".join(_changed_files_text)

def get_no_file_changes_after_build(buildtime, path, latest_fc=None, ignored: Set[Optional[str]] = ()):
    if latest_fc is None:
        latest_fc = datetime.datetime.fromtimestamp(get_latest_file_change_in_a_folder(path, ignored))
    buildtime_dt = datetime.datetime.fromtimestamp(buildtime)
    return buildtime_dt >= latest_fc

def get_no_file_changes_after_build_text(buildtime, path, force_status=None, ignored: Set[Optional[str]] = ()):
    latest_fc = datetime.datetime.fromtimestamp(get_latest_file_change_in_a_folder(path, ignored))
    if force_status is None:
        return "{0} || {1}".format("✓" if get_no_file_changes_after_build(buildtime, path, latest_fc, ignored) else "╳", notzformat.format(latest_fc))
    else:
        return "{0} || {1}".format("✓" if force_status else "╳", notzformat.format(latest_fc))

def get_changed_files_paths_from_changelogs(changelog: ChangeLog, current_code_rev: int, projectname: str):
    _filepaths = set()
    for crev_clog_num in range(changelog.coderev, current_code_rev+1):
        try:
            _clog = ChangeLog(projectname, crev_clog_num, create=False)
        except FileNotFoundError:
            debug_print(f"CLog {crev_clog_num} does not exist. skipping")
            continue
        else:
            debug_print(f"Opening {crev_clog_num}.clog")
            _changes = _clog.paths
            debug_print(f"    Adding {len(_changes)} from {crev_clog_num}.clog")
            if isDebug:
                for _c in _changes:
                    debug_print(f"      {_c}")
            _filepaths.update(_changes)
    return _filepaths

def split_path_string_on(path: str, spl: int, sep: str = "/"):
    if isinstance(path, str):
        _split_path = path.split(sep)
        _lines = list()
        _s = ""
        for s in _split_path:
            if len(_s) + len(s) > spl:
                _lines.append(_s)
                _s = ''
            _s = f'{_s}{sep if len(_s) > 0 and not _s.endswith(sep) else ""}{s}{sep}'
        if len(_s) > 0:
            _lines.append(_s)
        return "\n".join(_lines)
    else:
        return ""
