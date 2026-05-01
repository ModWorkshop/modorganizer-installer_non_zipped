import configparser
import os
import shutil

from PyQt6.QtCore import QSettings, QTimer

import mobase


class non_zipped_installer(mobase.IPluginInstallerCustom):
    # Add supported file extensions that only need to be copied into a mod
    installed_mods: dict[str, list[str]]

    def supportedExtensions(self):
        acceptedExt = {"pak", "utoc", "ucas", "bundle", "bk2", "ugc", "pck", "dll", "pck"}
        if self._organizer.managedGame().gameName() == "Road to Vostok":
            acceptedExt = {"vmz", "zip"}
        return acceptedExt

    def updateMetaINI(self, file_path: str, new_mod: mobase.IModInterface):
        file_meta_path = file_path + ".meta"
        if os.path.exists(file_meta_path):
            file_meta = configparser.ConfigParser()
            file_meta.read(file_meta_path)
            try:
                new_mod.setUrl(file_meta["General"]["url"])
                new_mod.setVersion(mobase.VersionInfo(file_meta["General"]["version"]))
                new_mod.setNewestVersion(
                    mobase.VersionInfo(file_meta["General"]["newestVersion"])
                )
            except KeyError:
                pass

    def onInstallationEnd(
        self, result: mobase.InstallResult, new_mod: mobase.IModInterface
    ):
        if result != mobase.InstallResult.SUCCESS:
            return None
        # Have to use this dumb method as "setInstallationFile" is not exposed to python for some reason...
        if new_mod.name() in self.installed_mods:
            archive_name, url = self.installed_mods.pop(new_mod.name())
            path = os.path.join(new_mod.absolutePath(), "meta.ini")
            QTimer.singleShot(
                4000, lambda: self.waitToUpdateINI(archive_name, url, path)
            )  # type: ignore
        return None

    def waitToUpdateINI(self, archive_name: str, url: str, path: str):
        settings = QSettings(path, QSettings.Format.IniFormat, None)
        settings.setValue("installationfile", archive_name)
        settings.setValue("repository", "ModWorkshop")
        settings.setValue("url", url)
        if not self.installed_mods:
            self._organizer.refresh()

    def install(
        self,
        mod_name: mobase.GuessedString,
        game_name: str,
        archive_name: str,
        version: str,
        nexus_id: int,
    ):
        global mod_path
        if nexus_id == 0:
            mod_name.update(os.path.splitext(os.path.basename(archive_name))[0])

        new_mod = self._organizer.createMod(mod_name)

        if not new_mod:
            return mobase.InstallResult.CANCELED

        mod_path = new_mod.absolutePath()

        file_path = os.path.join(self._organizer.downloadsPath(), archive_name)
        self.updateMetaINI(file_path, new_mod)

        # Place non-zipped file into mod directory for ModDataChecker to check
        shutil.copy(file_path, new_mod.absolutePath())

        # retrieve the mod-data-checker
        checker = self._organizer.gameFeatures().gameFeature(mobase.ModDataChecker)

        tree = new_mod.fileTree()
        checkReturn = checker.dataLooksValid(tree)
        if checkReturn == checker.CheckReturn.FIXABLE:
            tree = checker.fix(tree)
            if not tree:
                return mobase.InstallResult.FAILED
        elif checkReturn == checker.CheckReturn.INVALID:
            return mobase.InstallResult.FAILED
        self.installed_mods[new_mod.name()] = [
            os.path.basename(archive_name),
            new_mod.url(),
        ]
        return mobase.InstallResult.SUCCESS

    def isArchiveSupported(self, tree: mobase.IFileTree) -> bool:  # type: ignore
        return True

    def description(self):
        return (
            "Installer that allows for these non-zipped mod files to be installed: "
            + ", ".join(list(self.supportedExtensions()))
        )

    def init(self, organizer: mobase.IOrganizer):
        self._organizer = organizer
        self.installed_mods = {}
        return True

    def name(self):
        return "Non-zipped Installer"

    def author(self):
        return "MaskPlague, modworkshop"

    def isManualInstaller(self):
        return False

    def isActive(self):
        return self._organizer.pluginSetting(self.name(), "enabled")

    def settings(self):  # type: ignore
        return []  # type: ignore

    def settingGroups(self):  # type: ignore
        return []  # type: ignore

    def priority(self):
        return 999

    def version(self):
        return mobase.VersionInfo(0, 0, 2, 8)


def createPlugin() -> mobase.IPluginInstaller:
    return non_zipped_installer()
