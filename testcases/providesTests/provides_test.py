import sys
import outputControl.logging_access as la
import config.global_config as gc
import config.runtime_config as rc
import utils.process_utils as pu

import utils.core.base_xtest as bt

###
import utils.core.configuration_specific as cs
import utils.test_constants as tc
import utils.pkg_name_split as ns
import utils.test_utils as tu
from outputControl import dom_objects as do




class NonITW(cs.JdkConfiguration):
    def __init__(self, this):
        super().__init__()
        self.rpms = rc.RuntimeConfig().getRpmList()
        self.this=this
        self.passed = 0
        self.failed = 0



    def _get_artificial_provides(self, filename):
            output, error, res = pu.executeShell("rpm -q --provides rpms/" + filename)
            lines = output.split("\n")
            provides_dict = {}
            for line in lines:
                if "=" in line and "debuginfo(build" not in line:
                    actual_line = line.split("=")
                    provides_dict[actual_line[0].strip()] = actual_line[1].strip()
            return provides_dict


    def check_artificial_provides(self, this):
        files = self.rpms.files
        documentation = ""
        for filename in files:
            filename = filename.split("/")[-1]
            expected_provides = self._get_expected_artificial_provides(filename)
            documentation += make_rpm_readable(filename) + " should have these and no other provides: " + ", ".join(list(expected_provides.keys())) + "\n"
            if self.documenting:
                continue
            actual_provides = self._get_artificial_provides(filename)
            missing_provides = []
            for provide in expected_provides:
                testcase = do.Testcase("NonITW", "check_artificial_provides")
                do.Tests().add_testcase(testcase)
                if not tu.passed_or_failed(self, provide in actual_provides):
                    missing_provides.append(provide)
                    testcase.set_log_file("none")
                    testcase.set_view_file_stub(make_rpm_readable(filename) + " is missing provide: " + provide)
                else:
                    testcase = do.Testcase("NonITW", "check_artificial_provides")
                    do.Tests().add_testcase(testcase)
                    if not tu.passed_or_failed(self, expected_provides[provide] == actual_provides[provide]):
                        la.LoggingAccess().log("wrong version for provide " + provide + " in "
                                               + make_rpm_readable(filename), la.Verbosity.TEST)
                        testcase.set_log_file("none")
                        testcase.set_view_file_stub("wrong version for provide " + provide + " in "
                                                    + make_rpm_readable(filename))
                    actual_provides.pop(provide)
            if missing_provides:
                la.LoggingAccess().log("missing provide in {}: ".format(make_rpm_readable(filename)) + str(list(missing_provides)), la.Verbosity.TEST)
            testcase = do.Testcase("NonITW", "check_artificial_provides")
            do.Tests().add_testcase(testcase)
            if not tu.passed_or_failed(self, len(actual_provides) == 0):
                la.LoggingAccess().log("found extra provides in rpm \"" + make_rpm_readable(filename) + "\": " +
                                       str(list(actual_provides.keys())))
                testcase.set_log_file("none")
                testcase.set_view_file_stub("found extra provides in rpm \"" + make_rpm_readable(filename) + "\": " +
                                            str(list(actual_provides.keys())))
        self._document(documentation)
        return self.passed, self.failed

    def _get_expected_artificial_provides(self, filename):
        name, java_ver, vendor, pkg, version, end = ns._hyphen_split(filename)
        arch = self._validate_arch_for_provides(ns.get_arch(filename))
        # have to look at this with Jvanek/list through provides myself in future
        if "src" in end:
            provides = Empty(name, java_ver, vendor, pkg, version, end, arch, filename)
        elif "debuginfo" in pkg or "debugsource" in pkg:
            provides = DebugInfo(name, java_ver, vendor, pkg, version, end, arch, filename)
        elif java_ver not in tc.TECHPREVIEWS:
            if "openjfx" in pkg:
                provides = OpenJfx(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "headless" in pkg or (not tu.has_headless_pkg() and self._is_pkg_default(pkg)):
                provides = Headless(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif self._is_pkg_default(pkg):
                provides = Jre(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "devel" in pkg:
                provides = Sdk(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "javadoc-zip" in pkg:
                provides = JavaDocZip(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "javadoc" in pkg:
                provides = JavaDoc(name, java_ver, vendor, pkg, version, end, arch, filename)
            else:
                provides = Default(name, java_ver, vendor, pkg, version, end, arch, filename)
        else:
            if "headless" in pkg or (not tu.has_headless_pkg() and self._is_pkg_default(pkg)):
                provides = HeadlessTechPreview(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif self._is_pkg_default(pkg):
                provides = JreTechPreview(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "devel" in pkg:
                provides = SdkTechPreview(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "javadoc-zip" in pkg:
                provides = JavaDocZipTechPreview(name, java_ver, vendor, pkg, version, end, arch, filename)
            elif "javadoc" in pkg:
                provides = JavaDocTechPreview(name, java_ver, vendor, pkg, version, end, arch, filename)
            else:
                provides = DefaultTechPreview(name, java_ver, vendor, pkg, version, end, arch, filename)
        return provides.get_expected_artificial_provides()

    def cross_check_artificial_provides(self, this):
        files = self.rpms.files
        self._document("according to Jvanek every provide should be provided only once per set of rpms with exception "
                       + "of javadoc-zip having common provides with javadoc")
        for i in range(len(files)):
            files[i] = files[i].replace("rpms/", "")
        if files:
            la.LoggingAccess().log("  Testing VersionRelease: " + ns.get_version_full(files[0]), la.Verbosity.TEST)
        for i in range(len(files) - 1):
            actual_provides = self._get_artificial_provides(files[i])
            for j in range(i + 1, len(files)):
                if ns.get_arch(files[i]) == ns.get_arch(files[j]):
                    if ("zip" in files[i] and "javadoc" in files[j]) or ("zip" in files[j] and "javadoc" in files[i]):
                        continue
                    compared_provides = self._get_artificial_provides(files[j])
                    provides_intersection = [provide for provide in actual_provides if provide in compared_provides]
                    testcase = do.Testcase("NonITW", "cross_check_artificial_provides")
                    do.Tests().add_testcase(testcase)
                    if not tu.passed_or_failed(self, not(len(provides_intersection))):
                        la.LoggingAccess().log("{} and {} have common provides: {}".format(make_rpm_readable(files[i]), make_rpm_readable(files[j]), ", ".join(provides_intersection)))
                        testcase.set_log_file("none")
                        testcase.set_view_file_stub(
                            "{} and {} have common provides: {}".format(make_rpm_readable(files[i]), make_rpm_readable(files[j]),
                                                                        ", ".join(provides_intersection)))

        return

    def check_ghosts(self, filename):
        self._document("")
        pass


    def _get_actual_ghosts(self, filename):
        pass


    def _get_expected_ghosts(self, filename):
        pass


    def _validate_arch_for_provides(self, arch):
        if arch == "aarch64":
            return "aarch-64"
        elif arch == "i386" or arch == "i686":
            return "x86-32"
        elif arch == "armv7hl":
            return "armv7hl-32"
        elif arch == "ppc64le":
            return "ppc-64"
        elif arch == "x86_64":
            return "x86-64"
        elif arch == "s390x":
            return "s390-64"
        else:
            return arch

    def _is_pkg_default(self, pkg):
        return pkg == "" or pkg == "debug" or pkg == "slowdebug"

###

class ProvidesTest(bt.BaseTest):
    """ Framework class that runs the testcase. """
    instance=None

    def __init__(self):
        super().__init__()
        self.list_of_failed_tests = []

    def test_artificial_provides(self):
        self.csch.cross_check_artificial_provides(self)
        return self.csch.check_artificial_provides(self)

    def setCSCH(self):
        ProvidesTest.instance=self
        if rc.RuntimeConfig().getRpmList().getJava() == gc.ITW:
            self.log("Set ItwVersionCheck")
            #set ITW when finished
            self.csch = NonITW(ProvidesTest.instance)
        else:
            self.log("Set OthersVersionCheck")
            self.csch = NonITW(ProvidesTest.instance)

    def getTestedArchs(self):
        pass


class Empty:
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        self.expected_provides = {}

    def get_expected_artificial_provides(self):
        return self.expected_provides


class DebugInfo(Empty):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(DebugInfo, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides[("{}-{}-{}".format(name, java_ver, vendor) + (("-" + pkg) if pkg else pkg) +
                                "({})".format(arch))] = ns.get_version_full(filename)
        self.expected_provides[("{}-{}-{}".format(name, java_ver, vendor) + (("-" + pkg) if pkg else pkg))] = \
            ns.get_version_full(filename)


class DefaultTechPreview(DebugInfo):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(DefaultTechPreview, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides[(name + "-" + java_ver + (("-" + pkg) if pkg else pkg))] = ns.get_version_full(filename)


class SdkTechPreview(DefaultTechPreview):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(SdkTechPreview, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        pkg = pkg.replace("devel", "")
        self.expected_provides[(name + "-sdk" + "-" + java_ver + pkg)] = ns.get_version_full(filename)
        self.expected_provides[(name + "-sdk" + "-" + java_ver + "-" + vendor + pkg)] = \
            ns.get_version_full(filename)


class JreTechPreview(DefaultTechPreview):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(JreTechPreview, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides[("jre" + "-" + java_ver + (("-" + pkg) if pkg else pkg))] = ns.get_version_full(filename)
        self.expected_provides[("jre" + "-" + java_ver + "-" + vendor + (("-" + pkg) if pkg else pkg))] = \
            ns.get_version_full(filename)


class Default(DefaultTechPreview):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(Default, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides[(name + (("-" + pkg) if pkg else pkg))] = ns.get_version_full(filename)
        self.expected_provides[(name + "-" + vendor + (("-" + pkg) if pkg else pkg))] = \
            ns.get_version_full(filename)


class Sdk(Default):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(Sdk, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        pkg = pkg.replace("devel", "")
        self.expected_provides[(name + "-sdk" + pkg)] = ns.get_version_full(filename)
        self.expected_provides[(name + "-sdk-" + vendor + pkg)] = \
            ns.get_version_full(filename)
        self.expected_provides[(name + "-sdk-" + java_ver + pkg)] = ns.get_version_full(filename)
        self.expected_provides[(name + "-sdk-" + java_ver + "-" + vendor + pkg)] = \
            ns.get_version_full(filename)


class Jre(Default):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(Jre, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides["jre" + (("-" + pkg) if pkg else pkg)] = ns.get_version_full(filename)
        self.expected_provides["jre" + "-" + vendor + (("-" + pkg) if pkg else pkg)] = \
            ns.get_version_full(filename)
        self.expected_provides[("jre" + "-" + java_ver + (("-" + pkg) if pkg else pkg))] = ns.get_version_full(filename)
        self.expected_provides[("jre" + "-" + java_ver + "-" + vendor + (("-" + pkg) if pkg else pkg))] = \
            ns.get_version_full(filename)


class HeadlessTechPreview(JreTechPreview):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(HeadlessTechPreview, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides["config({})".format("-".join([name, java_ver, vendor, pkg]))] = \
            ns.get_version_full(filename)


class Headless(Jre):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(Headless, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        self.expected_provides["config({})".format("-".join([name, java_ver, vendor, pkg]))] = \
            ns.get_version_full(filename)


class OpenJfx(DebugInfo):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(OpenJfx, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        pkg = pkg.replace("openjfx", "")
        self.expected_provides[("javafx" + pkg)] = ns.get_version_full(filename)


class JavaDoc(Default):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(JavaDoc, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)


class JavaDocZip(JavaDoc):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(JavaDocZip, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        for provide in list(self.expected_provides):
            if "(" not in provide:
                self.expected_provides[(provide.replace("-zip", ""))] = ns.get_version_full(filename)


class JavaDocTechPreview(DefaultTechPreview):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(JavaDocTechPreview, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)


class JavaDocZipTechPreview(JavaDocTechPreview):
    def __init__(self, name, java_ver, vendor, pkg, version, end, arch, filename):
        super(JavaDocZipTechPreview, self).__init__(name, java_ver, vendor, pkg, version, end, arch, filename)
        for provide in list(self.expected_provides):
            if "(" not in provide:
                self.expected_provides[(provide.replace("-zip", ""))] = ns.get_version_full(filename)


def make_rpm_readable(name):
    return ns.get_package_name(name) + "." + ns.get_arch(name)


def testAll():
    return ProvidesTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Provides")
    return ProvidesTest().execute_special_docs()

def main(argv):
    bt.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])

