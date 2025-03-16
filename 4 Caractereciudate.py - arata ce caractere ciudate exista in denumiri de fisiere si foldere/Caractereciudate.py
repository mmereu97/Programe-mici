import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, 
                           QVBoxLayout, QWidget, QTextEdit, QLabel, QLineEdit,
                           QHBoxLayout, QMessageBox, QListWidget, QDialog, 
                           QDialogButtonBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class AddCharacterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adaugă Caracter Nou")
        self.setModal(True)
        
        # Setare font mare pentru dialog
        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        
        layout = QVBoxLayout(self)
        
        # Input pentru caracter nou
        self.char_input = QLineEdit()
        self.char_input.setMaxLength(1)
        self.char_input.setFont(font)
        layout.addWidget(QLabel("Introdu caracterul:"))
        layout.addWidget(self.char_input)
        
        # Butoane OK/Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.setFont(font)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_character(self):
        return self.char_input.text()

class FileScanner(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanner Caractere Neobișnuite")
        self.setGeometry(100, 100, 1200, 800)
        
        # Configurare implicită
        self.config_file = "scanner_config.json"
        self.default_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-.,' + ' ')
        self.allowed_chars = self.default_chars.copy()
        self.custom_chars = set()
        
        # Font mare pentru toată aplicația
        self.font = QFont()
        self.font.setPointSize(12)
        QApplication.setFont(self.font)
        
        # Încarcă configurația dacă există
        self.load_config()
        
        # Inițializare UI
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Layout stânga pentru controalele principale
        left_layout = QVBoxLayout()
        
        # Buton pentru selectarea folderului
        self.folder_btn = QPushButton("📂 Selectează Folder", self)
        self.folder_btn.clicked.connect(self.browse_folder)
        self.folder_btn.setMinimumHeight(40)
        left_layout.addWidget(self.folder_btn)
        
        # Label pentru afișarea căii folderului selectat
        self.folder_label = QLabel("Niciun folder selectat", self)
        self.folder_label.setWordWrap(True)
        left_layout.addWidget(self.folder_label)
        
        # Statistici
        self.stats_frame = QFrame()
        self.stats_frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
        stats_layout = QVBoxLayout(self.stats_frame)
        
        self.stats_label = QLabel("Statistici scanare:", self)
        self.stats_label.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.stats_label)
        
        self.files_count = QLabel("Fișiere cu caractere neobișnuite: 0", self)
        self.folders_count = QLabel("Foldere cu caractere neobișnuite: 0", self)
        self.total_count = QLabel("Total elemente problematice: 0", self)
        
        stats_layout.addWidget(self.files_count)
        stats_layout.addWidget(self.folders_count)
        stats_layout.addWidget(self.total_count)
        
        left_layout.addWidget(self.stats_frame)
        
        # Buton pentru începerea scanării
        self.scan_btn = QPushButton("🔍 Start Scanare", self)
        self.scan_btn.clicked.connect(self.start_scan)
        self.scan_btn.setEnabled(False)
        self.scan_btn.setMinimumHeight(40)
        left_layout.addWidget(self.scan_btn)
        
        # Zona de rezultate
        results_label = QLabel("Rezultate scanare:", self)
        left_layout.addWidget(results_label)
        
        self.results = QTextEdit(self)
        self.results.setReadOnly(True)
        left_layout.addWidget(self.results)
        
        main_layout.addLayout(left_layout, stretch=2)
        
        # Layout dreapta pentru managementul caracterelor
        right_layout = QVBoxLayout()
        
        # Titlu pentru lista de caractere
        chars_label = QLabel("Caractere ignorate (personalizate):", self)
        right_layout.addWidget(chars_label)
        
        # Lista de caractere personalizate
        self.chars_list = QListWidget(self)
        self.chars_list.setFont(self.font)
        self.update_chars_list()
        right_layout.addWidget(self.chars_list)
        
        # Butoane pentru managementul caracterelor
        chars_buttons_layout = QHBoxLayout()
        
        add_char_btn = QPushButton("➕ Adaugă", self)
        add_char_btn.clicked.connect(self.add_character)
        add_char_btn.setMinimumHeight(40)
        chars_buttons_layout.addWidget(add_char_btn)
        
        remove_char_btn = QPushButton("❌ Șterge", self)
        remove_char_btn.clicked.connect(self.remove_character)
        remove_char_btn.setMinimumHeight(40)
        chars_buttons_layout.addWidget(remove_char_btn)
        
        validate_btn = QPushButton("✓ Validează Selecția", self)
        validate_btn.clicked.connect(self.validate_selected)
        validate_btn.setMinimumHeight(40)
        chars_buttons_layout.addWidget(validate_btn)
        
        right_layout.addLayout(chars_buttons_layout)
        
        # Label pentru caracterele implicite
        default_chars_label = QLabel("Caractere ignorate (implicite):", self)
        right_layout.addWidget(default_chars_label)
        
        default_chars_text = QTextEdit(self)
        default_chars_text.setReadOnly(True)
        default_chars_text.setMaximumHeight(100)
        default_chars_text.setText(''.join(sorted(self.default_chars)))
        right_layout.addWidget(default_chars_text)
        
        main_layout.addLayout(right_layout, stretch=1)
        
        self.selected_folder = None
        
    def validate_selected(self):
        if not self.chars_list.selectedItems():
            QMessageBox.warning(self, "Atenție", "Selectează mai întâi caracterele de validat!")
            return
            
        validated_chars = set(item.text() for item in self.chars_list.selectedItems())
        self.custom_chars -= validated_chars
        self.allowed_chars = self.default_chars | self.custom_chars
        self.update_chars_list()
        self.save_config()
        
        # Reafișează rezultatele cu caracterele validate
        if self.selected_folder:
            self.start_scan()
    
    def update_statistics(self, unusual_chars):
        files_count = 0
        folders_count = 0
        
        for path in unusual_chars.keys():
            if os.path.isfile(path):
                files_count += 1
            else:
                folders_count += 1
                
        self.files_count.setText(f"Fișiere cu caractere neobișnuite: {files_count}")
        self.folders_count.setText(f"Foldere cu caractere neobișnuite: {folders_count}")
        self.total_count.setText(f"Total elemente problematice: {files_count + folders_count}")
    
    def update_chars_list(self):
        self.chars_list.clear()
        for char in sorted(self.custom_chars):
            self.chars_list.addItem(char)
    
    def add_character(self):
        dialog = AddCharacterDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_char = dialog.get_character()
            if new_char:
                if new_char in self.default_chars:
                    QMessageBox.information(self, "Info", 
                        "Acest caracter este deja în lista implicită!")
                    return
                self.custom_chars.add(new_char)
                self.allowed_chars = self.default_chars | self.custom_chars
                self.update_chars_list()
                self.save_config()
    
    def remove_character(self):
        current_item = self.chars_list.currentItem()
        if current_item:
            char = current_item.text()
            self.custom_chars.remove(char)
            self.allowed_chars = self.default_chars | self.custom_chars
            self.update_chars_list()
            self.save_config()
    
    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.custom_chars = set(config.get('ignored_chars', ''))
                self.allowed_chars = self.default_chars | self.custom_chars
                self.results_message("Configurație încărcată cu succes din JSON")
        except FileNotFoundError:
            self.results_message("Nu s-a găsit fișierul de configurare. Se folosesc setările implicite.")
        except json.JSONDecodeError:
            self.results_message("Eroare la citirea fișierului JSON. Se folosesc setările implicite.")
    
    def save_config(self):
        config = {
            'ignored_chars': ''.join(sorted(self.custom_chars))
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.results_message("Configurația a fost salvată în JSON!")
        except Exception as e:
            QMessageBox.warning(self, "Eroare", f"Eroare la salvarea configurației: {str(e)}")
    
    def results_message(self, message):
        if hasattr(self, 'results'):
            self.results.append(message)
        else:
            print(message)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selectează Folder")
        if folder:
            self.selected_folder = folder
            self.folder_label.setText(f"Folder selectat: {folder}")
            self.scan_btn.setEnabled(True)
    
    def scan_files(self, folder):
        unusual_chars = {}
        
        for root, dirs, files in os.walk(folder):
            # Verifică numele directoarelor
            for dir_name in dirs:
                unusual = set(dir_name) - self.allowed_chars
                if unusual:
                    full_path = os.path.join(root, dir_name)
                    unusual_chars[full_path] = unusual
            
            # Verifică numele fișierelor
            for file_name in files:
                unusual = set(file_name) - self.allowed_chars
                if unusual:
                    full_path = os.path.join(root, file_name)
                    unusual_chars[full_path] = unusual
        
        return unusual_chars
    
    def start_scan(self):
        if not self.selected_folder:
            return
        
        self.results.clear()
        self.results.append("Scanare în curs...\n")
        
        unusual_chars = self.scan_files(self.selected_folder)
        
        if not unusual_chars:
            self.results.append("Nu s-au găsit caractere neobișnuite!")
            self.update_statistics({})
            return
        
        self.results.append("Caractere neobișnuite găsite:\n")
        for path, chars in unusual_chars.items():
            self.results.append(f"În: {path}")
            self.results.append(f"Caractere neobișnuite: {', '.join(chars)}\n")
            
        self.update_statistics(unusual_chars)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    scanner = FileScanner()
    scanner.show()
    sys.exit(app.exec_())