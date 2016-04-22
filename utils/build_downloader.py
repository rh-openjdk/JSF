"""In time of writing this library, the koji python library was not  compatible with python3, so legacy approach was chosen"""

import ntpath
import os
import shutil

import utils.pkg_name_split as split
import urllib3

import config.global_config
import config.runtime_config
import outputControl.logging_access
import utils.rpm_list

BREW = "brew"
KOJI = "koji"


def getBuild(nvr):
    "This method download build from brw. The filtering of arches depends on RuntimeConfig().getArchs();"
    target = _checkDest(config.runtime_config.RuntimeConfig().getPkgsDir())
    command = _getCommand(nvr)
    outputControl.logging_access.LoggingAccess().log("using " + command);
    packages = _getBuildInfo(command, nvr)
    if len(packages) == 0:
        raise Exception("No pkgs to download. Verify build or archs")
    outputControl.logging_access.LoggingAccess().log("going to download " + str(len(packages)) + " rpms")
    _downloadBrewKojiBuilds(packages, target)
    return True


def _downloadBrewKojiBuilds(pkgs, targetDir):
    for i, pkg in enumerate(pkgs):
        mainUrl = _getMainUrl(pkg)
        url = "unknonw_service"
        if KOJI in pkg:
            url = mainUrl + pkg.replace("/mnt/koji/", "/")
        if BREW in pkg:
            url = mainUrl + pkg.replace("/mnt/redhat/", "/")
        outputControl.logging_access.LoggingAccess().log("downloading " + str(i + 1) + "/" + str(len(pkgs)) + " - " + url)
        targetFile = targetDir + "/" + ntpath.basename(pkg)
        http = urllib3.PoolManager()
        with http.request('GET', url, preload_content=False) as r, open(targetFile, 'wb') as out_file:
            shutil.copyfileobj(r, out_file)


def _isRpm(line):
    return line == "RPMs:"

def _getBuildInfo(cmd, nvr):
    allPkgs = utils.process_utils.processAsStrings([cmd, 'buildinfo', nvr], _isRpm, None, False)
    rpms = []
    for pkg in allPkgs :
        if _isArchValid(pkg):
            rpms.append(pkg)
    return rpms


def _checkDest(dir):
    absOne = os.path.abspath(dir)
    if not os.path.exists(absOne):
        outputControl.logging_access.LoggingAccess().log("Creating: " + absOne)
        os.mkdir(absOne)
    if not os.path.isdir(absOne):
        raise Exception(absOne + " Must bean directory, is not")
    if not os.listdir(absOne) == []:
        raise Exception(absOne + " Is not empty, please fix")
    outputControl.logging_access.LoggingAccess().log("Using as download target: " + absOne)
    return absOne


def _isArchValid(rpmLine):
    arches= config.runtime_config.RuntimeConfig().getArchs();
    if arches is None or len(arches) == 0:
        arches = config.global_config.getAllArchs()
    for arch in arches:
        if "/" + arch + "/" in rpmLine or "." + arch + "." in rpmLine:
            return True
    return False


def _getCommand(nvr):
    os = _getOs(nvr + ".fakeArch")
    if utils.rpm_list.isRhel(os):
        return BREW
    if utils.rpm_list.isFedora(os):
        return KOJI
    raise Exception("Unknown os - " + os)


def _getMainUrl(path_rpm):
    rpm = ntpath.basename(path_rpm)
    os = _getOs(rpm)
    if utils.rpm_list.isRhel(os):
        return "http://download.devel.redhat.com/"
    if utils.rpm_list.isFedora(os):
        return "http://koji.fedoraproject.org"
    raise Exception("Unknown os - " + os)


def _getOs(rpm):
    os = split.get_dist(rpm)
    outputControl.logging_access.LoggingAccess().log("in " + rpm + " recognized " + os)
    return os