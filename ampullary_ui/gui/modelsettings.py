import logging
import pathlib
import urllib
import zipfile

from PySide6.QtWidgets import QWidget, QMessageBox, QFileDialog
from PySide6.QtCore import QSettings, QRunnable, QThreadPool, Slot, Signal

from ampullary_ui.signals import DownloadSignals
from ampullary_ui.ui.manage_model_ui import Ui_ManageModel
from ampullary_ui.utils.saving import get_outputfolder


class DownloadWorker(QRunnable):
    def __init__(self, url: str, destination: pathlib.Path):
        super().__init__()
        self._url = url
        self._destination = destination
        self._signals = DownloadSignals()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @property
    def signals(self):
        return self._signals

    @Slot()
    def run(self):
        dest_file = None
        try:
            with urllib.request.urlopen(self._url) as httpresponse:
                if httpresponse.status != 200:
                    self._signals.error.emit(
                        f"Invalid url ({self._url}), error code is {httpresponse.status} {str(httpresponse)}"
                    )
                    return

                filename = pathlib.Path(httpresponse.url).name
                dest_file = self._destination / filename

                content_length = httpresponse.getheader("Content-Length")
                total_size = int(content_length) if content_length else 0

                self._signals.progress.emit(f"Downloading {filename}...", 0.0)

                chunk_size = 1024 * 1024
                downloaded = 0
                with open(dest_file, "wb") as file_handle:
                    while True:
                        if self._cancelled:
                            raise InterruptedError("Download cancelled by user")
                        chunk = httpresponse.read(chunk_size)
                        if not chunk:
                            break
                        file_handle.write(chunk)
                        downloaded += len(chunk)
                        progress = downloaded / total_size if total_size > 0 else 0.0
                        self._signals.progress.emit(
                            f"Downloading {filename}... {downloaded / (1024 * 1024):.1f} MB",
                            progress,
                        )

            if self._cancelled:
                raise InterruptedError("Download cancelled by user")

            self._signals.progress.emit(f"Extracting {filename}...", 0.5)

            with zipfile.ZipFile(dest_file, "r") as zip_handle:
                zip_handle.extractall(self._destination)
            self._signals.progress.emit(f"Cleaning up {filename}", 0.75)
            dest_file.unlink()
            logging.info("Downloaded and extracted %s to %s", filename, self._destination)
            self._signals.progress.emit("Download and extraction complete.", 1.0)
            self._signals.finished.emit(self._destination)
        except urllib.error.HTTPError as exc:
            self._signals.error.emit(
                f"Invalid url ({self._url}), error code is {exc.code} {str(exc)}"
            )
        except InterruptedError:
            if dest_file is not None and dest_file.exists():
                dest_file.unlink(missing_ok=True)
            self._signals.progress.emit("Download cancelled.", 0.0)
            self._signals.finished.emit(None)
        except (urllib.error.URLError, OSError, zipfile.BadZipFile) as exc:
            if dest_file is not None and dest_file.exists():
                dest_file.unlink(missing_ok=True)
            self._signals.error.emit(str(exc))


class ModelSettings(QWidget):
    busy = Signal()
    done = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings()
        self._ui = Ui_ManageModel()
        self._ui.setupUi(self)

        self._outputFolderBtn = self._ui.outputFolderBtn
        self._outputFolderBtn.clicked.connect(self._on_destination_select)
        self._outputFolderEdit = self._ui.downloadFolderEdit
        self._outputFolderEdit.setText(str(pathlib.Path.cwd()))

        self._downloadBtn = self._ui.downloadBtn
        self._downloadBtn.clicked.connect(self._on_download)
        self._sourceEdit = self._ui.sourceEdit

        self._selectpriorBtn = self._ui.priorBtn
        self._selectpriorBtn.clicked.connect(lambda: self._select_file(self._priorEdit, "*prior*.pkl"))

        self._selectposteriorBtn = self._ui.posteriorBtn
        self._selectposteriorBtn.clicked.connect(lambda: self._select_file(self._posteriorEdit, "*posterior*.pkl"))

        self._selectsummarystatsBtn = self._ui.summarystatsBtn
        self._selectsummarystatsBtn.clicked.connect(lambda: self._select_file(self._summarystatsEdit, "*summary*.h5"))

        self._selectpriorsamplesBtn = self._ui.priorsamplesBtn
        self._selectpriorsamplesBtn.clicked.connect(lambda: self._select_file(self._priorSamplesEdit, "*prior*.h5"))

        self._progressLabel = self._ui.progressLabel
        self._progressBar = self._ui.progressBar
        self._threadpool = QThreadPool()
        self._downloadWorker = None
        self._is_downloading = False

        self._priorEdit = self._ui.priorEdit
        self._posteriorEdit = self._ui.posteriorEdit
        self._priorSamplesEdit = self._ui.priorSampleEdit
        self._summarystatsEdit = self._ui.summaryStatsEdit

        self._sourceEdit.setText(self._settings.value("model/packagesource",
                                                      "https://gin.g-node.org/jgrewe/ampullary_sbi/raw/master/packages/gymnotiform_ampullary_1.0.zip"))
        # FIXME hardcoded!!

        self._priorEdit.setText(self._get_existing_file_setting("model/prior"))
        self._posteriorEdit.setText(self._get_existing_file_setting("model/posterior"))
        self._priorSamplesEdit.setText(self._get_existing_file_setting("model/priorsamples"))
        self._summarystatsEdit.setText(self._get_existing_file_setting("model/summarystats"))

    def _get_existing_file_setting(self, key):
        value = self._settings.value(key, "")
        if value is None:
            return ""
        path_value = pathlib.Path(str(value))
        if path_value.exists() and path_value.is_file():
            return str(path_value)
        return ""

    def _select_file(self, lineedit, pattern):
        file, _ = QFileDialog.getOpenFileName(None, "Select file", filter=pattern)
        if len(file) > 0:
            lineedit.setText(file)

    def store_settings(self):
        logging.info("Modelsettings.store_settings!")
        edits = [self._priorEdit, self._posteriorEdit, self._summarystatsEdit, self._priorSamplesEdit]
        for edit in edits:
            p = pathlib.Path(edit.text())
            if p is None or not p.exists() or not p.is_file():
                logging.error("At least one of the model files is invalid or unset!")
                QMessageBox.critical(self, "Model settings incomplete!",
                                    "At least one of the model files is invalid or unset!")
                logging.info("... failed!")
                return False
        self._settings.setValue("model/prior", self._priorEdit.text())
        self._settings.setValue("model/posterior", self._posteriorEdit.text())
        self._settings.setValue("model/summarystats", self._summarystatsEdit.text())
        self._settings.setValue("model/priorsamples", self._priorSamplesEdit.text())
        logging.info("... succeeded!")
        return True

    def _on_destination_select(self):
        dest = get_outputfolder(store_folder=False)
        if len(dest) == 0 or not dest.exists():
            return
        self._outputFolderEdit.setText(str(dest))

    def _check_archive_and_assign(self, destination):
        prior_samples = list(destination.glob("*prior_samples*.h5"))
        prior = list(destination.glob("*prior*.pkl"))
        posterior = list(destination.glob("*posterior*.pkl"))
        samplestats = list(destination.glob("*summary*.h5"))

        file_lists = {
            "prior samples": prior_samples,
            "prior": prior,
            "posterior": posterior,
            "summary statistics": samplestats,
        }
        empty_keys = [name for name, values in file_lists.items() if len(values) == 0]
        if empty_keys:
            raise FileNotFoundError(
                f"Missing expected extracted files: {', '.join(empty_keys)}"
            )
        self._priorEdit.setText(str(prior[0]))
        self._posteriorEdit.setText(str(posterior[0]))
        self._summarystatsEdit.setText(str(samplestats[0]))
        self._priorSamplesEdit.setText(str(prior_samples[0]))

    def _on_download_progress(self, message, progress):
        self._progressLabel.setText(message)
        self._progressBar.setMaximum(100)
        self._progressBar.setValue(int(progress * 100))

    def _on_download_error(self, message):
        logging.error(message)
        self._is_downloading = False
        self._downloadWorker = None
        self._downloadBtn.setEnabled(True)
        QMessageBox.critical(self, "Download Error", message)
        self.done.emit()

    def _on_download_finished(self, destination):
        self._is_downloading = False
        self._downloadWorker = None
        self._downloadBtn.setEnabled(True)
        if destination is None:
            self.done.emit()
            return
        try:
            self._check_archive_and_assign(destination)
        except FileNotFoundError as exc:
            logging.error(str(exc))
            QMessageBox.critical(self, "Something's wrong with the downloaded archive...", str(exc))
            return
        self.done.emit()

    def cancel_download(self):
        if self._is_downloading and self._downloadWorker is not None:
            self._downloadWorker.cancel()

    def _on_download(self):
        if self._is_downloading:
            QMessageBox.information(self, "Download running", "A download is already in progress.")
            return

        destination = pathlib.Path(self._outputFolderEdit.text())
        if not destination.exists():
            QMessageBox.critical(self, "No download folder!",
                                 "Select a valid download folder first!")
            return
        url = self._sourceEdit.text().strip()
        if len(url) == 0:
            QMessageBox.critical(self, "Download Error", "Enter a valid download URL first!")
            return

        self._downloadBtn.setEnabled(False)
        self._progressBar.setMaximum(100)
        self._progressBar.setValue(0)
        self._progressLabel.setText("Starting download...")
        self._is_downloading = True
        self.busy.emit()

        self._downloadWorker = DownloadWorker(url, destination)
        self._downloadWorker.signals.progress.connect(self._on_download_progress)
        self._downloadWorker.signals.error.connect(self._on_download_error)
        self._downloadWorker.signals.finished.connect(self._on_download_finished)
        self._threadpool.start(self._downloadWorker)
