from .config import os_name
import collections
import re
import os


__all__ = ['CoreFilenameInfo', 'core_filename_info']


CoreFilenameInfo = collections.namedtuple(
    'CoreFilenameInfo',
    ['filename',
     'is_zip',
     'is_keentools_core',
     'version',
     'os',
     'is_nightly',
     'nightly_build_number'])


def _parse_installation_filename(filename):
    m = re.match('keentools-core-(?P<version>\d+\.\d+\.\d+)' + \
                 '(?:\.(?P<nightly_version>\d+))?-(?P<os>[^-]+)\.zip',
                 filename)
    if not m:
        return None
    
    version_parsed = tuple([int(x) for x in m.group('version').split('.')])
    
    return (version_parsed, m.group('nightly_version'), m.group('os'))


def core_filename_info(filepath):
    _, filename = os.path.split(filepath)
    is_zip = filename.lower().endswith('.zip')
    parse_result = _parse_installation_filename(filename)
    if parse_result is None:
        return CoreFilenameInfo(filename, is_zip, False, None, None, None, None)
    
    version, nightly_version, os_parsed = parse_result
    
    return CoreFilenameInfo(filename, is_zip,
        True, version, os_parsed,
        nightly_version is not None, nightly_version)
