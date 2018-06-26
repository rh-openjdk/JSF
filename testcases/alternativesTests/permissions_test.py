from outputControl import logging_access as la
import sys
import re
import utils.core.base_xtest as bt
import config.global_config as gc
import config.runtime_config as rc
import utils
from outputControl.logging_access import Verbosity
from utils.mock.mock_executor import DefaultMock
from utils.test_utils import log_failed_test, rename_default_subpkg, get_arch, two_lists_diff, get_32bit_id_in_nvra,\
    passed_or_failed
from utils.test_constants import *
import os
from utils import pkg_name_split as pkgsplit
from utils.core.configuration_specific import JdkConfiguration
from utils.core.unknown_java_exception import UnknownJavaVersionException

# TODO: is broken for ojdk10 rolling releases
# TODO: jexec is broken, doc that it is binary in lib and it can not be moved


class BaseTest(JdkConfiguration):
    """
    This test is supposed to check all the files in /usr/lib/jvm/nvra and their permissions. If the checked file is
    a link, we check it's target, if it is still in /usr/lib/jvm/nvra dir. We also check man pages located in MAN_DIR.
    """

    def __init__(self):
        super().__init__()
        self.list_of_failed_tests = []
        self.invalid_file_candidates = []
        self.failed = 0
        self.passed = 0

    def _get_target_java_directory(self, name):
        """Returns a directory where jdk is installed (mostly name-version-release-arch)."""
        directory =  get_32bit_id_in_nvra(pkgsplit.get_nvra(name))
        if DEBUG_SUFFIX in name:
          directory = directory + DEBUG_SUFFIX

        return directory

    def _skipped_subpackages(self):
        """We might want to skip the subpackages that have post install, but do not add any files into jvm directory."""
        return []

    def doc_test_java_files_permissions(self, pkgs):
        """Main test method body."""
        self._document("On all files extracted from RPMs to {}/nvra and {} apply "
                       "following rules:".format(JVM_DIR, MAN_DIR))
        # get default manpages, since we check these too
        DefaultMock().provideCleanUsefullRoot()
        default_manpages, res = DefaultMock().execute_ls(MAN_DIR)
        default_manpages = default_manpages.split("\n")
        if not passed_or_failed(self, res == 0):
            log_failed_test(self, "Default manpages extraction has failed. Manpage tests will be invalid: " + str(res) +
                            str(default_manpages))

        for pkg in pkgs:
            name = os.path.basename(pkg)
            subpackage = rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            PermissionTest.instance.log("Checking {} subpackage...".format(subpackage), la.Verbosity.TEST)
            if subpackage in subpackages_without_alternatives() + self._skipped_subpackages():
                PermissionTest.instance.log("Skipping " + pkg, la.Verbosity.TEST)
                continue

            if not DefaultMock().postinstall_exception_checked(pkg):
                continue

            # get content of jvm directory
            jvm_dir = self._get_target_java_directory(name)
            out, result = DefaultMock().executeCommand(["ls -LR " + JVM_DIR + "/" + jvm_dir
                                                       ])
            if not passed_or_failed(self, result == 0):
                log_failed_test(self, "Java directory not found for " + subpackage + ", for desired directory "
                                + jvm_dir)
                continue
            valid_targets = self._parse_output(out, subpackage)
            self.sort_and_test(valid_targets, subpackage, name)

            manpages = two_lists_diff(DefaultMock().execute_ls(MAN_DIR)[0].split("\n"), default_manpages)
            for manpage in manpages:
                self.sort_and_test([MAN_DIR + "/" + manpage], subpackage, name)

        PermissionTest.instance.log("Failed permissions tests: " + "\n    ".join(self.list_of_failed_tests), la.Verbosity.ERROR)
        PermissionTest.instance.log("Unexpected files, filetypes or errors occured, requires sanity check, these are "
                                    "treated as fails: " + "\n    ".join(self.invalid_file_candidates))
        return self.passed, self.failed

    def _parse_output(self, out, subpackage):
        """Output of the file listing must be parsed into something more readable and easier to process."""
        output_parts = out.split("\n")
        return_targets = []
        header = re.compile("/[^:]*:")
        current_header = ""
        for line in output_parts:
            if line == "":
                continue
            elif "cannot access" in line:
                if subpackage == DEVEL and "/bin/" in line:
                    self.invalid_file_candidates.append(line)
                    PermissionTest.instance.log("In subpackage {} following was found: ".format(subpackage) + line)
                    PermissionTest.instance.log("This might be expected behaviour and should be only sanity checked.")
                    self.passed += 1
                    continue
                else:
                    self.invalid_file_candidates.append(line)
                    PermissionTest.instance.log("Unexpected filetype. Needs manual inspection.")
                    log_failed_test(self, "In subpackage {} following was found: ".format(subpackage) + line)
                    self.failed += 1
                continue
            elif header.search(line):
                current_header = header.match(line)
                current_header = current_header.group(0).strip(":")
                continue
            else:
                return_targets.append(current_header + "/" + line)
        return return_targets

    def sort_and_test(self, valid_targets, subpackage=None, name=None):
        """
        Sorts the files and checks whether permissions are as expected. If ever adding any exclude case, it must be
        documented in the _document method.
        """
        self._document("\n - ".join(["Directories should have 755 permissions.",
                                     "Content of bin directory should have 755 permissions",
                                     "All of the files ending with '.so' should have 755 permissions",
                                     "Regular files should have 644 permissions",
                                     "Symbolic links should have 777 permissions.",
                                     "Permissions of a file classes.jsa must be 444."
                                     "Binary jexec is an exception and must be in lib directory and has "
                                     "755 permissions.",
                                     "Other types of files with different permissions should not be present."]))
        for target in valid_targets:
            out, res = DefaultMock().executeCommand(['stat -c "%F" ' + target])
            if JVM_DIR not in target and MAN_DIR not in target and res == 0:
                PermissionTest.instance.log("This target: " + target + " is located out of the jvm directory. "
                                                                      "These files are not checked.")
                self.passed += 1
                continue
            # this is not easy to reproduce - there is an error in lib directory permissions, but since there is
            # jre subpackage present along with devel (default or headless), this keeps being hidden
            # for now we cover it with this hook, but once reproducible, we will ask for official fix
            # since it behaves correctly so far, this is a PASS
            # TODO: reproduce and fix
            if target == JVM_DIR + "/" + self._get_target_java_directory(name) + "/lib" and "devel" in subpackage:
                self.passed += 1
                PermissionTest.instance.log(target + " in subpackage " + subpackage + ". This is an unknown bug in the"
                                            " framework / jre, that is not reproducible "
                                            "so far. Howewer, in installed JDK, the permissions are correct.",
                                            Verbosity.TEST)
                continue
            if out == "directory":
                self._test_fill_in(target, out, "755")
            elif out == "regular file":
                if "/bin/" in target:
                    self._test_fill_in(target, "binary", "755")
                elif ".so" in target:
                    self._test_fill_in(target, "file ending with .so", "755")
                elif "/lib/server/classes.jsa" in target:
                    self._test_fill_in(target, "file classes.jsa", "444")
                elif "/lib/jexec" in target:
                    self._test_fill_in(target, "binary jexec", "755")
                else:
                    self._test_fill_in(target, out, "644")
            elif out == "symbolic link":
                self._test_fill_in(target, out, "777")
                out, res = DefaultMock().executeCommand(["readlink " + target])
                if not passed_or_failed(self, res == 0):
                    log_failed_test(self, "Target of symbolic link {} does not exist.".format(target) + " Error " + out)
                elif "../" in out:
                    parts = target.split("/")
                    for i in range(2):
                        parts = parts[:-1]
                    replace_dots = "/".join(parts)
                    out = out.replace("../", replace_dots + "/")

                self.sort_and_test([out], subpackage, name)
            else:
                if res != 0:
                    PermissionTest.instance.log("Command stat -c '%F' {} finished with {} exit"
                                                " code".format(target, res))
                    # JRE binaries in SDK packages have broken links that result in failed command.
                    if subpackage == DEVEL and (self._get_target_java_directory(name) + "/jre/bin/") in target:
                        PermissionTest.instance.log("This is expected behaviour in devel subpackage, since this is "
                                                    "consciously broken "
                                                    "symlink to default subpackage binaries. Not treated as fail.")
                        self.passed += 1
                        continue
                    else:
                        log_failed_test(self, "In subpackage {} following was found: Command stat -c '%F' {} finished"
                                              " with message: {}. ".format(subpackage, target, res, out))

                        self.invalid_file_candidates.append(
                            "Target: " + target + " with result: " + res.__str__() + " and output: " + out)
                        self.failed += 1
                        continue


                else:
                    PermissionTest.instance.log("Unexpected filetype. Needs manual inspection.", Verbosity.TEST)

                    log_failed_test(self, "In subpackage {} following was found: Command stat -c '%F' {} finished"
                                    " with message: {}. ".format(subpackage, target, res, out))

                self.invalid_file_candidates.append(target)
                self.failed += 1

    def _test_fill_in(self, file, filetype, expected_permission):
        """
        This method takes as an argument path to a file, type of the file for logs, expected permission and checks,
        if it matches results from chroot. It also documents any fails or successful checks.
        """
        out, res = DefaultMock().executeCommand(['stat -c "%a" ' + file])
        if res != 0:
            log_failed_test(self, filetype + " link is broken, could not find " + file)
            self.failed += 1
            return
        else:
            PermissionTest.instance.log(filetype + " {} exists. Checking permissions... ".format(file),
                                        la.Verbosity.MOCK)
        for p in range(3):
            if not (int(out[p]) == int(expected_permission[p])):
                log_failed_test(self, "Permissions of {} not as expected, should be {} but is "
                                      "{}.".format(file, expected_permission, out))
                self.failed += 1
                return
        PermissionTest.instance.log(filetype + " {} with permissions {}. Check "
                                    "successful.".format(file, out), la.Verbosity.MOCK)
        self.passed += 1
        return


# follows implementation of configuration specific classes
class OpenJdk6(BaseTest):
    def _skipped_subpackages(self):
        return [JAVADOC]

    def _get_target_java_directory(self, name):
        # ojdk6 is specific in java directory name
        directory = super()._get_target_java_directory(name)
        unnecessary_part = directory.split("-")[-1]
        directory = directory.replace("-" + unnecessary_part, "")
        return directory


class OpenJdk6PowBeArchAndX86(OpenJdk6):
    def _get_target_java_directory(self, name):
        return super()._get_target_java_directory(name) + "." + get_arch(PermissionTest.instance)


class OpenJdk7(OpenJdk6):
    def _skipped_subpackages(self):
        return super()._skipped_subpackages() + [DEFAULT]

    def _get_target_java_directory(self, name):
        return super(OpenJdk6, self)._get_target_java_directory(name)


class OpenJdk8(OpenJdk7):
    def _skipped_subpackages(self):
        return super()._skipped_subpackages() + [JAVADOC + DEBUG_SUFFIX, DEFAULT + DEBUG_SUFFIX,
                                                 JAVADOC + "-zip", JAVADOC + "-zip" + DEBUG_SUFFIX]


class OpenJdk9(OpenJdk8):
    pass


class Oracle(BaseTest):
    pass


class PermissionTest(bt.BaseTest):
    instance = None

    def test_alternatives_binary_files(self):
        pkgs = self.getBuild()
        return self.csch.doc_test_java_files_permissions(pkgs)

    def setCSCH(self):
        PermissionTest.instance = self
        rpms = rc.RuntimeConfig().getRpmList()
        self.log("Checking files for " + rpms.getMajorPackage(), la.Verbosity.TEST)
        if rpms.getVendor() == gc.OPENJDK:
            if rpms.getMajorVersionSimplified() == "6":
                if self.getCurrentArch() in (gc.getX86_64Arch() + gc.getPower64BeAchs()):
                    self.csch = OpenJdk6PowBeArchAndX86()
                    return
                else:
                    self.csch = OpenJdk6()
                    return
            if rpms.getMajorVersionSimplified() == "7":
                self.csch = OpenJdk7()
                return
            elif rpms.getMajorVersionSimplified() == "8":
                self.csch = OpenJdk8()
                return
            elif rpms.getMajorVersionSimplified() == "9" or rpms.getMajorVersionSimplified() == "10":
                self.csch = OpenJdk8()
                return
            else:
                raise UnknownJavaVersionException("Unknown version of OpenJDK.")

        if rpms.getVendor() == gc.SUN:
            if self.getCurrentArch() in (gc.getX86_64Arch() + gc.getPower64BeAchs()):
                self.csch = OpenJdk6PowBeArchAndX86()
                return
            else:
                self.csch = OpenJdk6()
                return
        if rpms.getVendor() == gc.ORACLE:
            self.csch = Oracle()
            return

        if rpms.getVendor() == gc.IBM:
            self.csch = BaseTest()
            return

        if rpms.getVendor() == gc.ITW:
            # TODO might be worth to check also other subdirectories
            self.csch = BaseTest()
            return
        raise UnknownJavaVersionException("Unknown JDK version!!!")


def testAll():
    return PermissionTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("File permissions conventions")
    return PermissionTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)
    return PermissionTest().execute_special_docs()


if __name__ == "__main__":
    main(sys.argv[1:])
