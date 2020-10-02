import os
import datetime

__all__ = ['recursive_fileiter', 'get_latest_file_change_in_a_folder', 'get_no_file_changes_after_build', 'get_no_file_changes_after_build_text',
           'split_path_string_on', 'get_unbuilt_changed_files', 'get_unbuilt_changed_files_text',

           'mtz', 'notzformat']

mtz = datetime.timezone(datetime.timedelta(hours=3))
notzformat = '{:%d-%m-%Y %H:%M:%S}'

def recursive_fileiter(sdir):
    ret = list()
    if os.path.exists(sdir):
        folders = [f.path for f in os.scandir(sdir) if (f.is_dir() and not f.name.startswith("."))]
        for folder in folders:
            ret.extend(recursive_fileiter(folder))
        if os.path.isfile(sdir):
            if os.path.split(sdir)[1] != "version.json":
                ret.append(sdir)
        with os.scandir(sdir) as directory:
            for item in directory:
                if item.is_file() and item.name != "version.json":
                    ret.append(item)
    return ret

def get_latest_file_change_in_a_folder(path):
    maxts = 0
    for f in recursive_fileiter(path):
        if os.stat(f).st_mtime > maxts:
            maxts = os.stat(f).st_mtime
    return maxts

def get_unbuilt_changed_files(buildtime, path):
    _ucf = list()
    for f in recursive_fileiter(path):
        if os.stat(f).st_mtime > buildtime:
            _ucf.append([f, datetime.datetime.fromtimestamp(os.stat(f).st_mtime)])
    return _ucf

def get_unbuilt_changed_files_text(filelist: list):
    _changed_file_text_format = "{0} - {1}"
    _changed_files_text = [_changed_file_text_format.format('/'.join(x[0].path.split('\\')[1:]), notzformat.format(x[1])) for x in filelist]
    return "\n".join(_changed_files_text)

def get_no_file_changes_after_build(buildtime, path, latest_fc=None):
    if latest_fc is None:
        latest_fc = datetime.datetime.fromtimestamp(get_latest_file_change_in_a_folder(path))
    buildtime_dt = datetime.datetime.fromtimestamp(buildtime)
    return buildtime_dt >= latest_fc

def get_no_file_changes_after_build_text(buildtime, path, force_status=None):
    latest_fc = datetime.datetime.fromtimestamp(get_latest_file_change_in_a_folder(path))
    if force_status is None:
        return "{0} || {1}".format("✓" if get_no_file_changes_after_build(buildtime, path, latest_fc) else "╳", notzformat.format(latest_fc))
    else:
        return "{0} || {1}".format("✓" if force_status else "╳", notzformat.format(latest_fc))

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
