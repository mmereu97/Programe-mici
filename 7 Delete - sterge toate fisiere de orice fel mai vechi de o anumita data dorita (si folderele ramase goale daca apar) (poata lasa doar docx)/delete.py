import sys
import os
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, QCheckBox

class FileCleanerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("File Cleaner")
        self.setGeometry(100, 100, 400, 250)
        
        layout = QVBoxLayout()

        # Path Label
        self.path_label = QLabel("Select Directory:")
        layout.addWidget(self.path_label)

        # Browse Button
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_directory)
        layout.addWidget(self.browse_button)

        # Date Input
        self.date_input = QLineEdit(self)
        self.date_input.setPlaceholderText("Enter date in DD-MM-YYYY format")
        layout.addWidget(self.date_input)

        # Checkbox for non-doc/docx deletion
        self.delete_non_doc_checkbox = QCheckBox("Delete all non-doc/docx files after initial cleanup")
        layout.addWidget(self.delete_non_doc_checkbox)

        # Start Button
        self.start_button = QPushButton("Start Cleaning")
        self.start_button.clicked.connect(self.start_cleaning)
        layout.addWidget(self.start_button)

        self.setLayout(layout)
        self.directory_path = ""

    def browse_directory(self):
        # Opens a dialog to select directory
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.directory_path = directory
            self.path_label.setText(f"Selected Directory: {self.directory_path}")

    def start_cleaning(self):
        # Validate inputs
        date_text = self.date_input.text()
        if not self.directory_path:
            QMessageBox.warning(self, "Warning", "Please select a directory.")
            return
        if not date_text:
            QMessageBox.warning(self, "Warning", "Please enter a date.")
            return

        # Parse date
        try:
            target_date = datetime.datetime.strptime(date_text, "%d-%m-%Y")
        except ValueError:
            QMessageBox.warning(self, "Warning", "Invalid date format. Use DD-MM-YYYY.")
            return

        # Perform initial cleaning based on date
        self.clean_directory_by_date(self.directory_path, target_date)

        # If checkbox is selected, delete non-doc/docx files in the remaining structure
        if self.delete_non_doc_checkbox.isChecked():
            self.delete_non_doc_files(self.directory_path)

        QMessageBox.information(self, "Completed", "Cleaning completed successfully.")

    def clean_directory_by_date(self, directory, target_date):
        # Traverse and delete files/folders based on date
        for root, dirs, files in os.walk(directory, topdown=False):
            # Delete files older than target date
            for file in files:
                file_path = os.path.join(root, file)
                file_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_modified_time < target_date:
                    os.remove(file_path)

            # Delete empty directories
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                if not os.listdir(dir_path):  # If directory is empty
                    os.rmdir(dir_path)

    def delete_non_doc_files(self, directory):
        # Traverse and delete all non-doc/docx files in the directory structure
        for root, dirs, files in os.walk(directory):
            for file in files:
                if not file.lower().endswith(('.doc', '.docx')):
                    file_path = os.path.join(root, file)
                    os.remove(file_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    cleaner = FileCleanerApp()
    cleaner.show()
    sys.exit(app.exec_())