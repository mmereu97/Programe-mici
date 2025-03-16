import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                           QLabel, QFileDialog, QProgressBar, QTextEdit, QHBoxLayout, 
                           QLineEdit, QScrollArea, QWidget, QGridLayout)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QCloseEvent, QTextCursor
import subprocess

class ClickableTextEdit(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | 
            Qt.TextSelectableByKeyboard | 
            Qt.LinksAccessibleByMouse
        )
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        fragment = cursor.charFormat().anchorHref()
        if fragment.startswith('file://'):
            path = fragment.replace('file://', '')
            directory = os.path.dirname(path)
            if os.path.exists(directory):
                if sys.platform == 'win32':
                    os.startfile(directory)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', directory])
                else:
                    subprocess.run(['xdg-open', directory])
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        if cursor.charFormat().anchorHref():
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
        super().mouseMoveEvent(event)

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)
    
    def __init__(self, directory, replacements):
        super().__init__()
        self.directory = directory
        self.replacements = replacements
        self.files_processed = 0
        self.total_files = 0
        self.modified_files = 0
        self.modified_dirs = 0
    
    def fix_name(self, name):
        original = name
        for from_text, to_text in self.replacements:
            if from_text and to_text:
                name = name.replace(from_text, to_text)
        return name, name != original
    
    def count_files(self, directory):
        count = 0
        for root, dirs, files in os.walk(directory):
            count += len(files)
        return count
    
    def run(self):
        self.total_files = self.count_files(self.directory)
        
        for root, dirs, files in os.walk(self.directory, topdown=False):
            for file_name in files:
                old_path = os.path.join(root, file_name)
                new_name, was_modified = self.fix_name(file_name)
                
                if was_modified:
                    try:
                        new_path = os.path.join(root, new_name)
                        os.rename(old_path, new_path)
                        self.modified_files += 1
                        self.log.emit(
                            f'Redenumit: {file_name} -> {new_name}<br>'
                            f'<a href="file://{new_path}" style="color: blue; text-decoration: underline;">Deschide folder</a><br>'
                        )
                    except Exception as e:
                        error_folder = os.path.dirname(old_path)
                        error_message = str(e)
                        self.log.emit(
                            f'<span style="color: red;">Eroare: {error_message}</span><br>'
                            f'<a href="file://{error_folder}" style="color: blue; text-decoration: underline;">Deschide folder cu problema</a><br>'
                            f'Fișier: {old_path} -> {new_path}<br>'
                            f'------------------------<br>'
                        )
                
                self.files_processed += 1
                progress = int((self.files_processed / self.total_files) * 100)
                self.progress.emit(progress)
            
            for dir_name in dirs:
                old_path = os.path.join(root, dir_name)
                new_name, was_modified = self.fix_name(dir_name)
                
                if was_modified:
                    try:
                        new_path = os.path.join(root, new_name)
                        os.rename(old_path, new_path)
                        self.modified_dirs += 1
                        self.log.emit(
                            f'Director redenumit: {dir_name} -> {new_name}<br>'
                            f'<a href="file://{new_path}" style="color: blue; text-decoration: underline;">Deschide folder</a><br>'
                        )
                    except Exception as e:
                        error_folder = os.path.dirname(old_path)
                        error_message = str(e)
                        self.log.emit(
                            f'<span style="color: red;">Eroare la director: {error_message}</span><br>'
                            f'<a href="file://{error_folder}" style="color: blue; text-decoration: underline;">Deschide folder cu problema</a><br>'
                            f'Director: {old_path} -> {new_path}<br>'
                            f'------------------------<br>'
                        )

        self.finished.emit(self.modified_files, self.modified_dirs)

class DynamicInputGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QGridLayout()
        self.replacement_pairs = []
        self.initUI()

    def initUI(self):
        self.setLayout(self.layout)
        self.add_initial_rows()

    def add_initial_rows(self):
        for i in range(15):  # Începem tot cu 15 rânduri pentru datele inițiale
            self.add_row()

    def add_row(self):
        row = len(self.replacement_pairs)
        
        label = QLabel(f"{row+1}.")
        self.layout.addWidget(label, row, 0)
        
        from_input = QLineEdit()
        from_input.setPlaceholderText('Text de înlocuit')
        self.layout.addWidget(from_input, row, 1)
        
        to_input = QLineEdit()
        to_input.setPlaceholderText('Înlocuiește cu')
        self.layout.addWidget(to_input, row, 2)
        
        from_input.textChanged.connect(self.check_for_empty_row)
        to_input.textChanged.connect(self.check_for_empty_row)
        
        self.replacement_pairs.append((from_input, to_input))

    def check_for_empty_row(self):
        # Verificăm dacă există cel puțin o pereche goală
        has_empty_pair = False
        for from_input, to_input in self.replacement_pairs:
            if not from_input.text().strip() and not to_input.text().strip():
                has_empty_pair = True
                break
        
        # Dacă nu există nicio pereche goală, adăugăm una
        if not has_empty_pair:
            self.add_row()

    def get_replacements(self):
        return [(from_input.text().strip(), to_input.text().strip()) 
                for from_input, to_input in self.replacement_pairs
                if from_input.text().strip() and to_input.text().strip()]

    def set_replacements(self, pairs):
        # Ștergem toate perechile existente
        while self.replacement_pairs:
            pair = self.replacement_pairs.pop()
            pair[0].deleteLater()
            pair[1].deleteLater()
        
        # Adăugăm perechile salvate
        for from_text, to_text in pairs:
            self.add_row()
            current_pair = self.replacement_pairs[-1]
            current_pair[0].setText(from_text)
            current_pair[1].setText(to_text)
        
        # Ne asigurăm că există o pereche goală la final
        if not self.replacement_pairs or (
            self.replacement_pairs[-1][0].text().strip() or 
            self.replacement_pairs[-1][1].text().strip()
        ):
            self.add_row()

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_file = 'replace_settings.json'
        self.initUI()
        self.loadSettings()
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.input_grid = DynamicInputGrid()
        scroll.setWidget(self.input_grid)
        
        self.path_label = QLabel('Niciun director selectat')
        self.browse_button = QPushButton('Alege Director')
        self.start_button = QPushButton('Start')
        self.progress_bar = QProgressBar()
        self.log_text = ClickableTextEdit()
        
        main_layout.addWidget(scroll)
        main_layout.addWidget(self.path_label)
        main_layout.addWidget(self.browse_button)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.log_text)
        
        self.setLayout(main_layout)
        self.browse_button.clicked.connect(self.browse_folder)
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setEnabled(False)
        
        self.setWindowTitle('Multiple Replace')
        self.setGeometry(300, 300, 800, 600)
    
    def loadSettings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_pairs = json.load(f)
                    self.input_grid.set_replacements(saved_pairs)
        except Exception as e:
            self.log_text.append(f'Eroare la încărcarea setărilor: {str(e)}')
    
    def saveSettings(self):
        try:
            pairs_to_save = [
                (from_input.text(), to_input.text())
                for from_input, to_input in self.input_grid.replacement_pairs
                if from_input.text().strip() and to_input.text().strip()
            ]
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(pairs_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_text.append(f'Eroare la salvarea setărilor: {str(e)}')
    
    def closeEvent(self, event: QCloseEvent):
        self.saveSettings()
        event.accept()
        
    def browse_folder(self):
        self.directory = QFileDialog.getExistingDirectory(self, 'Alege Director')
        if self.directory:
            self.path_label.setText(f'Director: {self.directory}')
            self.start_button.setEnabled(True)
    
    def start_processing(self):
        replacements = self.input_grid.get_replacements()
                
        if not replacements:
            self.log_text.append('Completează cel puțin o pereche de înlocuire!')
            return
            
        self.worker = WorkerThread(self.directory, replacements)
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.update_log)
        self.worker.finished.connect(self.processing_finished)
        
        self.browse_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self.log_text.append("Reguli de înlocuire aplicate:")
        for i, (from_text, to_text) in enumerate(replacements, 1):
            self.log_text.append(f"{i}. '{from_text}' -> '{to_text}'")
        self.log_text.append("-" * 40)
        
        self.worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_log(self, message):
        self.log_text.append(message)
    
    def processing_finished(self, modified_files, modified_dirs):
        self.browse_button.setEnabled(True)
        self.start_button.setEnabled(True)
        
        self.log_text.append("\nRAPORT FINAL:")
        self.log_text.append("-" * 40)
        self.log_text.append(f"Fișiere modificate: {modified_files}")
        self.log_text.append(f"Directoare modificate: {modified_dirs}")
        self.log_text.append(f"Total elemente modificate: {modified_files + modified_dirs}")
        self.log_text.append("-" * 40)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec_())