import sys
import string
import json
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCharFormat

class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
    def insertFromMimeData(self, source):
        text = source.text()
        cursor = self.textCursor()
        format = QTextCharFormat()
        format.setFont(self.currentFont())
        cursor.insertText(text)
        self.document().setDefaultFont(self.currentFont())

class MemoryHelperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_file = 'memory_helper_config.json'
        self.load_config()
        
        self.setWindowTitle("Memory Helper")
        self.setGeometry(100, 100, 1200, 600)  # Lățime mărită pentru a acomoda cele două panouri
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)  # Layout principal rămâne vertical
        
        # Layout pentru butoane și controale
        controls_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Browse")
        self.start_btn = QPushButton("Start")
        self.browse_btn.clicked.connect(self.browse_file)
        self.start_btn.clicked.connect(self.process_text)
        
        self.font_size = QSpinBox()
        self.font_size.setMinimum(8)
        self.font_size.setMaximum(72)
        self.font_size.setValue(self.config.get('font_size', 12))
        self.font_size.editingFinished.connect(lambda: self.change_font_size(self.font_size.value()))
        
        controls_layout.addWidget(self.browse_btn)
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(QLabel("Font Size:"))
        controls_layout.addWidget(self.font_size)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Layout orizontal pentru cele două panouri de text
        text_panels_layout = QHBoxLayout()
        
        # Panoul pentru textul original
        original_panel = QVBoxLayout()
        original_panel.addWidget(QLabel("Text Original:"))
        self.text_original = CustomTextEdit(self)
        original_panel.addWidget(self.text_original)
        
        # Panoul pentru textul procesat
        processed_panel = QVBoxLayout()
        processed_panel.addWidget(QLabel("Text Procesat:"))
        self.text_processed = CustomTextEdit(self)
        processed_panel.addWidget(self.text_processed)
        
        # Adaugă cele două panouri în layout-ul orizontal
        text_panels_layout.addLayout(original_panel)
        text_panels_layout.addLayout(processed_panel)
        
        # Adaugă layout-ul orizontal la layout-ul principal
        layout.addLayout(text_panels_layout)
        
        self.change_font_size(self.config.get('font_size', 12))

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {'font_size': 12}
        except:
            self.config = {'font_size': 12}

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def change_font_size(self, value):
        font = QFont()
        font.setPointSize(value)
        self.text_original.setFont(font)
        self.text_processed.setFont(font)
        self.config['font_size'] = value
        self.save_config()
        
        # Reapply font to existing content
        self.text_original.document().setDefaultFont(font)
        self.text_processed.document().setDefaultFont(font)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Text File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.text_original.setText(file.read())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Nu s-a putut citi fișierul: {str(e)}")

    def process_text(self):
        original_text = self.text_original.toPlainText()
        if not original_text:
            return

        processed_text = ""
        current_word = ""
        
        for char in original_text:
            if char.isspace() or char in string.punctuation:
                if current_word:
                    processed_text += current_word[0]
                    current_word = ""
                processed_text += char
            else:
                if not current_word:
                    current_word += char
        
        if current_word:
            processed_text += current_word[0]
        
        self.text_processed.setText(processed_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MemoryHelperApp()
    window.show()
    sys.exit(app.exec_())