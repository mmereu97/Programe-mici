import os
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QMessageBox

class FileCleanerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("Ștergere fișiere non-DOC")
        self.setGeometry(100, 100, 400, 200)
        
        layout = QVBoxLayout()
        
        # Label pentru afișarea căii folderului selectat
        self.folder_path_label = QLabel("Folder nespecificat")
        layout.addWidget(self.folder_path_label)
        
        # Buton Browse
        browse_button = QPushButton("Browse", self)
        browse_button.clicked.connect(self.browse_folder)
        layout.addWidget(browse_button)
        
        # Buton Start
        start_button = QPushButton("Start", self)
        start_button.clicked.connect(self.delete_non_doc_files)
        layout.addWidget(start_button)
        
        self.setLayout(layout)
        
    def browse_folder(self):
        # Deschide dialogul de selectare a folderului
        folder_path = QFileDialog.getExistingDirectory(self, "Selectează folder")
        if folder_path:
            self.folder_path_label.setText(folder_path)
    
    def delete_non_doc_files(self):
        folder_path = self.folder_path_label.text()
        
        if folder_path == "Folder nespecificat":
            QMessageBox.warning(self, "Atenție", "Selectați un folder.")
            return
        
        deleted_files_count = 0
        
        # Parcurge toate fișierele și subfolderele din folderul selectat
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # Verifică extensia fișierului
                if not (file.endswith('.doc') or file.endswith('.docx')):
                    try:
                        file_path = os.path.join(root, file)
                        os.remove(file_path)  # Șterge fișierul
                        deleted_files_count += 1
                    except Exception as e:
                        print(f"Eroare la ștergerea fișierului {file_path}: {e}")
        
        # Mesaj de informare cu numărul de fișiere șterse
        QMessageBox.information(self, "Finalizat", f"{deleted_files_count} fișiere au fost șterse.")

# Inițializează aplicația
app = QApplication(sys.argv)
window = FileCleanerApp()
window.show()
sys.exit(app.exec_())