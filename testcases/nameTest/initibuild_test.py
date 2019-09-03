""""Test whether the content of gc.dir is sane"""
import sys

import config.general_parser
import config.global_config as gc
import config.runtime_config
import testcases.nameTest.connfigs.initbuild_config
import utils.core.base_xtest
from outputControl import logging_access as la
from utils.test_utils import passed_or_failed, _reinit
from outputControl import dom_objects as do


class InitTest(utils.core.base_xtest.BaseTest):
    def __init__(self):
        super().__init__()
        self.failed = 0
        self.passed = 0


    def test_java(self):
        _reinit(self)
        java = config.runtime_config.RuntimeConfig().getRpmList().getJava()
        self.log("prefix is: " + java)
        passed_or_failed(self, java is not None, "Test failed")
        self.csch.checkPrefix(java)
        return self.passed, self.failed

    def test_majorVersion(self):
        _reinit(self)
        version = config.runtime_config.RuntimeConfig().getRpmList().getMajorVersion()
        self.log("Major version is: " + version)
        passed_or_failed(self, version is not None, "Test failed")
        self.csch.checkMajorVersion(version)
        return self.passed, self.failed

    def test_majorVersionSimplified(self):
        _reinit(self)
        version = config.runtime_config.RuntimeConfig().getRpmList().getMajorVersionSimplified()
        self.log("Major version simplified is: " + str(version))
        passed_or_failed(self, version is not None, "Test failed")
        self.csch.checkMajorVersionSimplified(version)
        return self.passed, self.failed

    def test_vendor(self):
        _reinit(self)
        vendor = config.runtime_config.RuntimeConfig().getRpmList().getVendor()
        self.log("Vendor is: " + vendor)
        passed_or_failed(self, vendor is not None, "Test failed")
        self.csch.checkVendor(vendor)
        return self.passed, self.failed

    def test_package(self):
        _reinit(self)
        pkgs = config.runtime_config.RuntimeConfig().getRpmList().getPackages()
        self.log("Found pacakges are: " + ",".join(pkgs))
        passed_or_failed(self, len(pkgs) > 0, "There are no packages to test")
        return self.passed, self.failed

    def test_majorPackage(self):
        _reinit(self)
        java = config.runtime_config.RuntimeConfig().getRpmList().getMajorPackage()
        self.log("Package is: " + java)
        passed_or_failed(self, java is not None, "Test failed")
        return self.passed, self.failed

    def test_subpackage(self):
        _reinit(self)
        subpkgs = config.runtime_config.RuntimeConfig().getRpmList().getSubpackageOnly()
        self.log("found subpackages only are: `" + "`,`".join(subpkgs) + "`")
        passed_or_failed(self, len(subpkgs) > 0, "No subpkgs to test")
        return self.passed, self.failed

    def test_version(self):
        _reinit(self)
        java = config.runtime_config.RuntimeConfig().getRpmList().getVersion()
        self.log("Version is: " + java)
        passed_or_failed(self, java is not None, "Test failed")
        return self.passed, self.failed

    def test_release(self):
        _reinit(self)
        java = config.runtime_config.RuntimeConfig().getRpmList().getRelease()
        self.log("Release is: " + java)
        passed_or_failed(self, java is not None, "Test failed")
        return self.passed, self.failed

    def test_dist(self):
        _reinit(self)
        java = config.runtime_config.RuntimeConfig().getRpmList().getDist()
        self.log("Dist is: " + java)
        passed_or_failed(self, java is not None, "Test failed")
        return self.passed, self.failed

    def test_arches(self):
        _reinit(self)
        arches = config.runtime_config.RuntimeConfig().getRpmList().getAllArches()
        self.log("All arches are: " + ",".join(arches))
        if not config.runtime_config.RuntimeConfig().getRpmList().getJava() == gc.ITW:
            passed_or_failed(self, len(arches) > 1, "less than 1 arch to test")
        else:
            passed_or_failed(self, len(arches) == 1, "itw pkgs should be noarch only")
        return self.passed, self.failed

    def test_nativeArches(self):
        _reinit(self)
        nativeArches = config.runtime_config.RuntimeConfig().getRpmList().getNativeArches()
        self.log("All native arches: " + ",".join(nativeArches))
        if not config.runtime_config.RuntimeConfig().getRpmList().getJava() == gc.ITW:
            passed_or_failed(self, len(nativeArches) > 0, "less than 1 arch to test")
        else:
            passed_or_failed(self, len(nativeArches) == 0, "itw pkgs should be noarch only")
        return self.passed, self.failed

    def test_srpmPackage(self):
        _reinit(self)
        srpm = config.runtime_config.RuntimeConfig().getRpmList().getSrpm()
        self.log("SrcRpm: " + str(srpm))
        return 0, 0
        # no assert, it can be None or exactly one file. On anything else getSrpm should throw exception

    def test_noarchesPackages(self):
        _reinit(self)
        noarches = config.runtime_config.RuntimeConfig().getRpmList().getNoArchesPackages()
        self.log("all no arches packages are: ")
        for pkg in noarches:
            self.log("  " + pkg)
        passed_or_failed(self, len(noarches) > 0, "Number of noarch pkgs to test is less than 1")
        return self.passed, self.failed

    def test_nativeArchesPackages(self):
        _reinit(self)
        nativeArches = config.runtime_config.RuntimeConfig().getRpmList().getNativeArches()
        for na in nativeArches:
            arches = config.runtime_config.RuntimeConfig().getRpmList().getPackagesByArch(na)
            self.log("all " + na + " packages are: ")
            for pkg in arches:
                self.log("  " + pkg)
            passed_or_failed(self, len(arches) > 0, "Number of archs to test is less than 1")
        return self.passed, self.failed

    def test_builds(self):
        _reinit(self)
        nativeArches = config.runtime_config.RuntimeConfig().getRpmList().getNativeArches()
        for na in nativeArches:
            arches = config.runtime_config.RuntimeConfig().getRpmList().getBuildWithoutSrpm(na)
            self.log("build for " + na + " without srpm: ")
            for pkg in arches:
                self.log("  " + pkg)
            passed_or_failed(self, len(arches) > 0, "Number of archs to test is less than 1")
        return self.passed, self.failed

    def test_completeBuilds(self):
        _reinit(self)
        nativeArches = config.runtime_config.RuntimeConfig().getRpmList().getNativeArches()
        for na in nativeArches:
            arches = config.runtime_config.RuntimeConfig().getRpmList().getCompleteBuild(na)
            self.log("build for " + na + ": ")
            for pkg in arches:
                self.log("  " + pkg)
            passed_or_failed(self, len(arches) > 0, "Number of archs to test is less than 1")
        return self.passed, self.failed

    def test_os(self):
        _reinit(self)
        l = config.runtime_config.RuntimeConfig().getRpmList()
        self.log("Os: " + l.getOs())
        self.log("Version: " + l.getOsVersion())
        self.log("Version major: " + str(l.getOsVersionMajor()))
        passed_or_failed(self, l.isFedora() | l.isRhel(), "Pkgs are not rhel, neither fedora")
        passed_or_failed(self, l.isFedora() != l.isRhel(), "Both Rhel and fedora pkgs are present")
        passed_or_failed(self, l.getOs() is not None, "Os was equal to None")
        passed_or_failed(self, l.getOsVersion() is not None, "OsVersion was equal to None")
        passed_or_failed(self, l.getOsVersionMajor() is not None, "OsVersionMajor was equal to None")
        return self.passed, self.failed

    def setCSCH(self):
        if config.runtime_config.RuntimeConfig().getRpmList().getJava() == gc.ITW:
            self.log("Set ItwVersionCheck")
            self.csch = testcases.nameTest.connfigs.initbuild_config.ItwVersionCheck()
        else:
            self.log("Set OthersVersionCheck")
            self.csch = testcases.nameTest.connfigs.initbuild_config.OthersVersionCheck()

    def getTestedArchs(self):
        return None


def testAll():
    return InitTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Build naming conventions")
    return InitTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
