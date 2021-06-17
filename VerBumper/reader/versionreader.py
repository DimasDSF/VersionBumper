import os
import json
class VersionData(object):
    def __init__(self):
        if os.path.exists('version.json'):
            with open('version.json', 'r') as vd:
                self.vd: dict = json.load(vd)
        else:
            self.vd = dict()

    @property
    def version(self) -> str:
        return self.vd.setdefault('version', 'Unknown')

    @property
    def coderev(self) -> str:
        return self.vd.setdefault('coderev', 'Unknown')

    @property
    def buildstamp(self) -> int:
        return self.vd.setdefault('buildstamp', 0)

    @property
    def buildtime(self) -> str:
        return self.vd.setdefault('buildtime', 'Unknown')