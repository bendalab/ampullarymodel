import logging
import pathlib
import urllib
import zipfile

from PySide6.QtWidgets import QWidget, QMessageBox, QApplication, QFileDialog
from PySide6.QtCore import QSettings

from ampullary_ui.ui.manage_model_ui import Ui_ManageModel
from ampullary_ui.utils.saving import get_outputfolder


class ModelSettings(QWidget):
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

        self._priorEdit = self._ui.priorEdit
        self._posteriorEdit = self._ui.posteriorEdit
        self._priorSamplesEdit = self._ui.priorSampleEdit
        self._summarystatsEdit = self._ui.summaryStatsEdit

        self._sourceEdit.setText(self._settings.value("model/packagesource",
                                                      "https://gin.g-node.org/jgrewe/ampullary_sbi/raw/master/packages/gymnotiform_ampullary_1.0.zip"))
        # FIXME hardcoded!!
        self._priorEdit.setText(self._settings.value("model/prior", ""))
        self._posteriorEdit.setText(self._settings.value("model/posterior", ""))
        self._priorSamplesEdit.setText(self._settings.value("model/priorsamples", ""))
        self._summarystatsEdit.setText(self._settings.value("model/summarystats", ""))

    def _select_file(self, lineedit, pattern):
        file, _ = QFileDialog.getOpenFileName(None, "Select file", filter=pattern)
        if len(file) > 0:
            lineedit.setText(file)

    def store_settings(self):
        logging.info("Modelsettings.store_settings")
        edits = [self._priorEdit, self._posteriorEdit, self._summarystatsEdit, self._priorSamplesEdit]
        for edit in edits:
            p = pathlib.Path(edit.text())
            if p is None or not p.exists() or not p.is_file():
                logging.error("At least one of the model files is invalid or unset!")
                QMessageBox.critical(self, "Model settings incomplete!",
                                    "At least one of the model files is invalid or unset!")
                return False

        self._settings.setValue("model/prior", self._priorEdit.text())
        self._settings.setValue("model/posterior", self._posteriorEdit.text())
        self._settings.setValue("model/summarystats", self._summarystatsEdit.text())
        self._settings.setValue("model/priorsamples", self._priorSamplesEdit.text())
        return True

    def _on_destination_select(self):
        dest = get_outputfolder(store_folder=False)
        if len(dest) == 0 or not dest.exists():
            return
        self._outputFolderEdit.setText(str(dest))

    @staticmethod
    def _open_url(url):
        try:
            return urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            # "e" can be treated as a http.client.HTTPResponse object
            return e

    def _perform_download(self, httpresponse, destination: pathlib.Path):
        filename = pathlib.Path(httpresponse.url).name
        dest_file = destination / filename

        content_length = httpresponse.getheader("Content-Length")
        total_size = int(content_length) if content_length else 0

        self._progressBar.setMaximum(total_size if total_size > 0 else 0)
        self._progressBar.setValue(0)
        self._progressLabel.setText(f"Downloading {filename}...")
        QApplication.processEvents()

        chunk_size = 1024 * 1024  # 1 MB
        downloaded = 0
        with open(dest_file, "wb") as f:
            while True:
                chunk = httpresponse.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    self._progressBar.setValue(downloaded)
                self._progressLabel.setText(
                    f"Downloading ... {downloaded / (1024 * 1024):.1f} MB"
                )
                QApplication.processEvents()

        self._progressLabel.setText(f"Extracting ...")
        QApplication.processEvents()
        with zipfile.ZipFile(dest_file, "r") as zf:
            zf.extractall(destination)

        if total_size > 0:
            self._progressBar.setValue(total_size)
        self._progressLabel.setText("Download and extraction complete.")
        logging.info("Downloaded and extracted %s to %s", filename, destination)
        dest_file.unlink()

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
            msg = ', '.join(empty_keys)
            logging.error("Missing expected extracted files: %s", msg)
            return
        self._priorEdit.setText(str(prior[0]))
        self._posteriorEdit.setText(str(posterior[0]))
        self._summarystatsEdit.setText(str(samplestats[0]))
        self._priorSamplesEdit.setText(str(prior_samples[0]))


    def _on_download(self):
        destination = pathlib.Path(self._outputFolderEdit.text())
        if not destination.exists():
            QMessageBox.critical(self, "No download folder!",
                                 "Select a valid download folder first!")
            return
        url = self._sourceEdit.text().strip()
        rr = self._open_url(url)
        if rr.status != 200:
            logging.error("Invalid url (%s), error code is %i %s", url, rr.status, str(rr))
            QMessageBox.critical(self, "Download Error",
                                 f"Invalid url ({url}), error code is {rr.status} {str(rr)}")
            return
        self._perform_download(rr, destination)

        try:
            self._check_archive_and_assign(destination)
        except FileNotFoundError as exc:
            logging.error(str(exc))
            QMessageBox.critical(self, "Something's wrong with the downloaded archive...", str(exc))
            return
