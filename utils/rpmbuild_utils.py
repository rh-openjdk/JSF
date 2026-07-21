import outputControl.logging_access as la
import utils.process_utils
import utils.test_utils
import os
import config.verbosity_config as vc
import utils.podman.podman_executor as pe
import utils.podman.podman_execution_exception

# Global podman instance for executing rpm/rpmbuild commands
_podman_instance = None

def _get_podman_instance():
    """Get or create the singleton podman instance.
    Ensures at minimum that the init snapshot exists so current_snapshot is never None.
    """
    global _podman_instance
    if _podman_instance is None:
        _podman_instance = pe.DefaultPodman()
        _podman_instance.provideCleanUsefullRoot()
    return _podman_instance

def _execute_rpm_command_in_container(cmd_list):
    """Execute an rpm command inside the podman container."""
    podman = _get_podman_instance()
    # Convert local file path to container path if it's an RPM file
    container_cmd = []
    for arg in cmd_list:
        if arg.endswith('.rpm') and os.path.exists(arg):
            # Convert to container path: /rpms/filename
            container_cmd.append('/rpms/' + os.path.basename(arg))
        else:
            container_cmd.append(arg)
    
    output, return_code = podman.executeCommand(container_cmd)
    return output

def rpmbuildEval(macro):
    output = _execute_rpm_command_in_container(['rpmbuild', '--eval', '%{' + macro + '}'])
    return output.strip()


def listFilesInPackage(rpmFile):
    output = _execute_rpm_command_in_container(['rpm', '-qlp', rpmFile])
    return output.strip().split('\n') if output.strip() else []


def listDocsInPackage(rpmFile):
    output = _execute_rpm_command_in_container(['rpm', '-qldp', rpmFile])
    return output.strip().split('\n') if output.strip() else []


def listConfigFilesInPackage(rpmFile):
    output = _execute_rpm_command_in_container(['rpm', '-qlcp', rpmFile])
    return output.strip().split('\n') if output.strip() else []


def listOfRequires(rpmFile):
    output = _execute_rpm_command_in_container(['rpm', '--requires', '-qp', rpmFile])
    return output.strip().split('\n') if output.strip() else []


def listOfProvides(rpmFile):
    output = _execute_rpm_command_in_container(['rpm', '--provides', '-qp', rpmFile])
    return output.strip().split('\n') if output.strip() else []


def listOfObsoletes(rpmFile):
    output = _execute_rpm_command_in_container(['rpm', '--obsoletes', '-qp', rpmFile])
    return output.strip().split('\n') if output.strip() else []


def listOfVersionlessRequires(rpmFile):
    return _filterVersions(listOfRequires(rpmFile))


def listOfVersionlessProvides(rpmFile):
    return _filterVersions(listOfProvides(rpmFile))


def listOfVersionlessObsoletes(rpmFile):
    return _filterVersions(listOfObsoletes(rpmFile))


def _filterVersions(listOfStrings):
    filtered = []
    for orig in listOfStrings:
        filtered.append(orig.split()[0])
    return filtered


def _isScripletLine(scriplet, line):
    return line.startswith(scriplet + " " + ScripletStarterFinisher.scriptlet)


PRETRANS = 'pretrans'
PREINSTALL = 'preinstall'
POSTINSTALL = 'postinstall'
TGINSTALL = 'triggerinstall'
TGUNINSTALL = 'triggeuninstall'
PREUNINSTALL = 'preuninstall'
POSTUNINSTALL = 'postuninstall'
TGPOSTUNINSTALL = 'triggerpostuninstall'
POSTTRANS = 'posttrans'


def isScripletNameValid(name):
    return name in ScripletStarterFinisher.allScriplets


class ScripletStarterFinisher:
    # hard to say when rpm uses uninstall or just un or install or just "nothing"
    allScriplets = [
        PRETRANS,
        PREINSTALL,
        POSTINSTALL,
        TGINSTALL,
        TGUNINSTALL,
        PREUNINSTALL,
        POSTUNINSTALL,
        TGPOSTUNINSTALL,
        POSTTRANS
    ]

    installScriptlets = [
        PRETRANS,
        PREINSTALL,
        POSTINSTALL,
        TGINSTALL,
        POSTTRANS
    ]

    uninstallScriptlets = [
        TGUNINSTALL,
        PREUNINSTALL,
        POSTUNINSTALL,
        TGPOSTUNINSTALL
    ]

    postScripts = allScriplets[2:]

    scriptlet = "scriptlet"

    def __init__(self, iid):
        self.id = iid

    def start(self, line):
        return _isScripletLine(self.id, line)

    def stop(self, line):
        for scriptlet in ScripletStarterFinisher.allScriplets:
            if _isScripletLine(scriptlet, line):
                return False  # stop
        return True  # continue


scriptlets = dict()

# returns tuple of executor of the string (eg. lua, shell) and the script itself
def getSrciplet(rpmFile, scripletId):
    if not isScripletNameValid(scripletId):
        la.LoggingAccess().log("warning! Scriplet name " + scripletId
                                                         + " is not known. It should be one of: "
                                                         + ",".join(ScripletStarterFinisher.allScriplets),
                               vc.Verbosity.TEST)
    key = rpmFile+"-"+scripletId
    if key in scriptlets:
        la.LoggingAccess().log(key + " already cached, returning", vc.Verbosity.PODMAN)
        return scriptlets[key]
    la.LoggingAccess().log(key + " not yet cached, reading", vc.Verbosity.PODMAN)
    sf = ScripletStarterFinisher(scripletId)
    
    # Execute rpm command in container
    output = _execute_rpm_command_in_container(['rpm', '-qp', '--scripts', rpmFile])
    lines = output.strip().split('\n') if output.strip() else []
    
    # Filter lines using start/stop functions
    script = []
    started = False
    for line in lines:
        if not started:
            if sf.start(line):
                started = True
                script.append(line)
        else:
            if sf.stop(line):
                script.append(line)
            else:
                break
    
    if len(script) == 0:
        scriptlet = ("/bin/sh", [])
    else:
        #two argumentless strips to accommodate for whitespace before the "<lua>"
        executor = script[0].split("using")[1].strip().strip("):<>").strip()
        scriptlet = (executor, script[1:])
    scriptlets[key] = scriptlet
    return scriptlet


def unpackFilesFromRpm(rpmFile, destination):
    """
    Unpack files from RPM using the podman container.
    Note: This extracts files to a temporary location in the container,
    then we would need to copy them out. For now, keeping the original
    implementation as it works directly with the filesystem.
    """
    absFile = os.path.abspath(rpmFile)
    utils.test_utils.mkdir_p(destination)
    sout, serr, res = utils.process_utils.executeShell("cd "+destination+" && rpm2cpio "+absFile+" | cpio -idmv")
    return sout, serr, res
