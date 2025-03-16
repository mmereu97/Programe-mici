import sys
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                           QVBoxLayout, QWidget, QFileDialog, QLabel,
                           QProgressBar, QTextEdit, QComboBox, QHBoxLayout)
from PyQt5.QtCore import QThread, pyqtSignal

logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkerThread(QThread):
    progress = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished = pyqtSignal()
    log_message = pyqtSignal(str)

    def __init__(self, start_path, use_oldest=True):
        super().__init__()
        self.start_path = start_path
        self.is_running = True
        self.use_oldest = use_oldest  # True pentru cea mai veche dată, False pentru cea mai nouă

    def get_extreme_file_date_in_tree(self, folder_path):
        """
        Caută cea mai veche sau cea mai nouă dată a fișierelor în folderul curent ȘI în toate subfolderele sale.
        Returnează (timestamp, calea_fișierului) pentru fișierul găsit.
        """
        extreme_time = None
        extreme_file_path = None

        # Parcurgem toate fișierele din folder și subfoldere
        try:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_time = os.path.getmtime(file_path)
                        if extreme_time is None or \
                           (self.use_oldest and file_time < extreme_time) or \
                           (not self.use_oldest and file_time > extreme_time):
                            extreme_time = file_time
                            extreme_file_path = file_path
                            self.log_message.emit(
                                f"Găsit fișier {'mai vechi' if self.use_oldest else 'mai nou'}: "
                                f"{file_path} cu data {datetime.fromtimestamp(file_time)}")
                    except Exception as e:
                        self.log_message.emit(f"Eroare la citirea datei fișierului {file_path}: {str(e)}")
        
        except Exception as e:
            self.log_message.emit(f"Eroare la parcurgerea folderului {folder_path}: {str(e)}")

        return extreme_time, extreme_file_path

    def process_folder(self, folder_path):
        """Procesează un singur folder."""
        try:
            extreme_time, extreme_file = self.get_extreme_file_date_in_tree(folder_path)
            
            if extreme_time is not None:
                try:
                    os.utime(folder_path, (extreme_time, extreme_time))
                    self.log_message.emit(
                        f"Setat data folderului {folder_path} la {datetime.fromtimestamp(extreme_time)}")
                    self.log_message.emit(
                        f"Data luată de la fișierul: {extreme_file}")
                except PermissionError:
                    self.log_message.emit(
                        f"WARNING: Nu s-a putut modifica data folderului {folder_path} - acces interzis sau folder în lucru. Continuăm cu următorul...")
                except OSError as e:
                    self.log_message.emit(
                        f"WARNING: Nu s-a putut modifica data folderului {folder_path} - {str(e)}. Continuăm cu următorul...")
            else:
                self.log_message.emit(
                    f"Nu s-au găsit fișiere în {folder_path} sau în substructura sa")
        
        except Exception as e:
            self.log_message.emit(f"Eroare la procesarea folderului {folder_path}: {str(e)}")

    def run(self):
        self.log_message.emit(
            f"Începere procesare pentru path: {self.start_path} "
            f"(folosind {'cea mai veche' if self.use_oldest else 'cea mai nouă'} dată)")
        
        # Colectăm toate folderele
        all_folders = []
        try:
            for root, dirs, _ in os.walk(self.start_path):
                for dir_name in dirs:
                    all_folders.append(os.path.join(root, dir_name))
        except Exception as e:
            self.log_message.emit(f"Eroare la colectarea folderelor: {str(e)}")
            return
        
        # Procesăm de la cele mai adânci spre rădăcină
        all_folders.sort(key=lambda x: x.count(os.sep), reverse=True)
        total_folders = len(all_folders)
        
        for index, folder_path in enumerate(all_folders):
            if not self.is_running:
                self.log_message.emit("Procesare anulată!")
                break
                
            self.process_folder(folder_path)
            progress = int((index + 1) / total_folders * 100)
            self.progress_value.emit(progress)
            self.progress.emit(f"Procesat folder {index + 1} din {total_folders}")
        
        if self.is_running:
            # Procesăm și folderul rădăcină la final
            self.process_folder(self.start_path)
            self.progress.emit("Procesare completă!")
        
        self.finished.emit()

    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Folder Date Modifier")
        self.setGeometry(100, 100, 800, 600)

        # Widget și layout principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # Label pentru afișarea căii selectate
        self.path_label = QLabel("Niciun folder selectat")
        layout.addWidget(self.path_label)

        # Layout orizontal pentru butoane și combo
        top_layout = QHBoxLayout()
        
        # Buton Browse
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        top_layout.addWidget(browse_btn)
        
        # ComboBox pentru selecția datei
        self.date_combo = QComboBox()
        self.date_combo.addItem("Cea mai veche dată")
        self.date_combo.addItem("Cea mai nouă dată")
        top_layout.addWidget(self.date_combo)
        
        layout.addLayout(top_layout)

        # Bară de progres
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Text edit pentru loguri
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Butoane
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Anulează")
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        layout.addWidget(self.cancel_btn)

        # Label pentru status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.selected_path = None
        self.worker = None

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selectează folder")
        if folder:
            self.selected_path = folder
            self.path_label.setText(f"Folder selectat: {folder}")
            self.start_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("")
            self.log_text.clear()

    def start_processing(self):
        if not self.selected_path:
            return
        
        use_oldest = self.date_combo.currentText() == "Cea mai veche dată"
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.status_label.setText("Procesare în curs...")
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self.worker = WorkerThread(self.selected_path, use_oldest)
        self.worker.progress.connect(self.update_status)
        self.worker.progress_value.connect(self.update_progress)
        self.worker.finished.connect(self.processing_finished)
        self.worker.log_message.connect(self.add_log)
        self.worker.start()

    def cancel_processing(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.cancel_btn.setEnabled(False)

    def update_status(self, message):
        self.status_label.setText(message)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def add_log(self, message):
        self.log_text.append(message)
        # Auto-scroll la ultimul mesaj
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def processing_finished(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())