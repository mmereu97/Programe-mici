import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                           QWidget, QFileDialog, QLabel, QProgressBar, QMessageBox,
                           QHBoxLayout, QLineEdit, QGroupBox, QFormLayout)
from PyQt5.QtCore import QThreadPool, QRunnable, pyqtSignal, QObject, Qt, QMutex, QWaitCondition
import win32com.client
import pythoncom
import time
import logging
from datetime import datetime
import re
import gc

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversion_debug.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def normalize_path(path):
    """Normalizează calea pentru Windows"""
    normalized = os.path.abspath(path).replace('/', '\\')
    if not os.path.exists(normalized):
        logging.error(f"Path does not exist: {normalized}")
        return None
    return normalized

class WorkerSignals(QObject):
    """Semnale pentru comunicare între thread-uri"""
    progress = pyqtSignal(int)
    file_status = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(dict)
    stats_update = pyqtSignal(dict)

class ConversionTask(QRunnable):
    """Task pentru conversia documentelor"""
    def __init__(self, files, signals, pause_flag, pause_condition, company_tag, author_tag):
        super(ConversionTask, self).__init__()
        self.files = files
        self.signals = signals
        self.pause_flag = pause_flag
        self.pause_condition = pause_condition
        self.company_tag = company_tag
        self.author_tag = author_tag
        self.BATCH_SIZE = 700
        self.stats = {
            "success": 0,
            "errors": 0,
            "skipped": 0,
            "doc_count": 0,
            "docx_old": 0,
            "docx_modern": 0,
            "processed_files": [],
            "start_time": 0,
            "pause_start": 0,
            "total_pause_time": 0
        }

    def cleanup_word(self, word_app):
        """Curăță complet instanța Word și obiectele COM asociate"""
        try:
            if word_app:
                print("\nCleaning up Word instance...")
                try:
                    for doc in word_app.Documents:
                        try:
                            doc.Close(SaveChanges=False)
                        except:
                            pass
                    word_app.Quit()
                except:
                    pass
                try:
                    import os
                    os.system('taskkill /f /im WINWORD.EXE >nul 2>&1')
                except:
                    pass
                try:
                    del word_app
                except:
                    pass
                gc.collect()
                print("Word cleanup completed")
        except Exception as e:
            print(f"Error during Word cleanup: {str(e)}")
            pass

    def handle_pause(self, index):
        """Gestionează starea de pauză"""
        self.stats["pause_start"] = time.time()
        print("\nConversion paused... Current statistics:")
        self.print_current_stats()
        self.signals.stats_update.emit(self.stats.copy())
        self.signals.file_status.emit("PAUSED - Press Resume to continue")
        mutex = QMutex()
        mutex.lock()
        self.pause_condition.wait(mutex)
        mutex.unlock()
        self.stats["total_pause_time"] += time.time() - self.stats["pause_start"]
        print("Conversion resumed")
        self.signals.file_status.emit(f"Resuming with file {index + 1}/{len(self.files)}")

    def print_current_stats(self):
        """Printează statisticile curente în consolă"""
        print("\n=== Current Statistics ===")
        print(f"File types found so far:")
        print(f"- DOC files: {self.stats['doc_count']}")
        print(f"- Old DOCX files: {self.stats['docx_old']}")
        print(f"- Modern DOCX files: {self.stats['docx_modern']}")
        print(f"\nResults so far:")
        print(f"- Successfully converted: {self.stats['success']}")
        print(f"- Errors: {self.stats['errors']}")
        print(f"- Skipped: {self.stats['skipped']}")
        print("="*30)

    def normalize_path(self, path):
        """Normalizează calea pentru Windows și verifică existența fișierului"""
        try:
            normalized = os.path.abspath(path).replace('/', '\\')
            if not os.path.exists(normalized):
                print(f"Warning: File not found: {normalized}")
                return None
            return normalized
        except Exception as e:
            print(f"Error normalizing path: {str(e)}")
            return None

    def set_document_properties(self, doc):
        """Setează proprietățile documentului"""
        try:
            print("Setting document properties...")
            doc.BuiltInDocumentProperties("Company").Value = self.company_tag
            doc.BuiltInDocumentProperties("Author").Value = self.author_tag
            print("Document properties set successfully")
            return True
        except Exception as e:
            print(f"Error setting document properties: {str(e)}")
            return False

    def preserve_file_dates(self, source_path, target_path):
        """Păstrează datele originale ale fișierului"""
        try:
            stat = os.stat(source_path)
            created_time = stat.st_ctime
            modified_time = stat.st_mtime
            accessed_time = stat.st_atime
            
            os.utime(target_path, (accessed_time, modified_time))
            
            print(f"Original file dates: Created: {datetime.fromtimestamp(created_time)}, "
                  f"Modified: {datetime.fromtimestamp(modified_time)}, "
                  f"Accessed: {datetime.fromtimestamp(accessed_time)}")
            return True
        except Exception as e:
            print(f"Error preserving file dates: {str(e)}")
            return False

    def process_file(self, file_path, word_app):
        """Procesează un singur fișier"""
        original_timestamps = None
        doc = None
        
        try:
            # Salvează timestamp-urile originale înainte de orice operațiune
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                original_timestamps = (stat.st_atime, stat.st_mtime)
                print(f"Original timestamps captured - Access: {datetime.fromtimestamp(original_timestamps[0])}, "
                      f"Modified: {datetime.fromtimestamp(original_timestamps[1])}")
            
            # Deschide documentul
            doc = word_app.Documents.Open(file_path)
            is_doc = file_path.lower().endswith('.doc')
            
            # Determină calea pentru fișierul nou
            output_path = os.path.splitext(file_path)[0] + '.docx'

            needs_conversion = True
            if not is_doc:
                try:
                    initial_mode = doc.CompatibilityMode
                    print(f"Initial compatibility mode: {initial_mode}")
                    
                    if initial_mode == 15 or initial_mode == 16:
                        needs_conversion = False
                        print("Document is already in modern format, updating properties only")
                        self.stats["docx_modern"] += 1
                        self.set_document_properties(doc)
                        doc.Save()
                        doc.Close()
                        
                        # Restaurăm timestamp-urile originale după salvare
                        if original_timestamps:
                            os.utime(file_path, original_timestamps)
                            print(f"Restored original timestamps for modern document: "
                                  f"Access={datetime.fromtimestamp(original_timestamps[0])}, "
                                  f"Modified={datetime.fromtimestamp(original_timestamps[1])}")
                        return True
                    else:
                        print(f"Document needs conversion (mode {initial_mode})")
                        self.stats["docx_old"] += 1
                except Exception as e:
                    print(f"Error checking compatibility mode: {str(e)}")
                    self.stats["docx_old"] += 1
                    needs_conversion = True

            if needs_conversion:
                if is_doc:
                    self.stats["doc_count"] += 1
                    print("File type: DOC")
                
                print("Converting document format...")
                # Încearcă conversia
                try:
                    doc.Convert()
                    print("Convert() successful")
                except:
                    try:
                        doc.ConvertTo2013()
                        print("ConvertTo2013() successful")
                    except Exception as conv_err:
                        print(f"Conversion attempt failed: {str(conv_err)}")

                # Setăm proprietățile documentului
                self.set_document_properties(doc)

                # Salvează documentul
                doc.SaveAs2(output_path, FileFormat=16, CompatibilityMode=15)
                doc.Close()
                print("Document saved with new format and properties")

                # Restaurează timestamp-urile originale
                if original_timestamps and os.path.exists(output_path):
                    os.utime(output_path, original_timestamps)
                    print(f"Restored original timestamps after conversion: "
                          f"Access={datetime.fromtimestamp(original_timestamps[0])}, "
                          f"Modified={datetime.fromtimestamp(original_timestamps[1])}")

                # Șterge fișierul original .doc dacă este cazul
                if is_doc and os.path.exists(output_path):
                    try:
                        os.remove(file_path)
                        print(f"Deleted original .doc file: {file_path}")
                    except Exception as del_err:
                        print(f"Warning: Could not delete original file: {str(del_err)}")

            return True

        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            if doc:
                try:
                    doc.Close(SaveChanges=False)
                except:
                    pass
            return False

    def run(self):
        """Execută conversia"""
        print("\n=== Starting Conversion Process ===")
        print(f"Total files to process: {len(self.files)}")
        
        try:
            os.system('taskkill /f /im WINWORD.EXE >nul 2>&1')
            print("Cleaned up any existing Word processes")
            time.sleep(2)
        except:
            pass

        self.stats["start_time"] = time.time()
        pythoncom.CoInitialize()
        word_app = None
        current_batch = 0
        slow_files_count = 0
        
        try:
            # Împărțim fișierele în loturi
            for batch_start in range(0, len(self.files), self.BATCH_SIZE):
                batch_end = min(batch_start + self.BATCH_SIZE, len(self.files))
                current_batch += 1
                print(f"\n=== Processing batch {current_batch} ===")
                
                # Inițializăm o nouă instanță Word pentru fiecare lot
                print("\nInitializing Word...")
                word_app = win32com.client.Dispatch("Word.Application")
                word_app.Visible = False
                word_app.DisplayAlerts = False
                print("Word initialized successfully")
                
                for index in range(batch_start, batch_end):
                    file_start_time = time.time()
                    
                    if self.pause_flag[0]:
                        self.stats["pause_start"] = time.time()
                        print("\nConversion paused... Current statistics:")
                        self.print_current_stats()
                        self.signals.stats_update.emit(self.stats.copy())
                        self.signals.file_status.emit("PAUSED - Press Resume to continue")
                        mutex = QMutex()
                        mutex.lock()
                        self.pause_condition.wait(mutex)
                        mutex.unlock()
                        self.stats["total_pause_time"] += time.time() - self.stats["pause_start"]
                        print("Conversion resumed")
                        self.signals.file_status.emit(f"Resuming with file {index + 1}/{len(self.files)}")

                    print(f"\n{'='*50}")
                    file_path = self.files[index]
                    status_msg = f"Converting file {index + 1}/{len(self.files)}"
                    print(f"\n{status_msg}: {file_path}")
                    self.signals.file_status.emit(status_msg)

                    normalized_path = self.normalize_path(file_path)
                    if not normalized_path:
                        self.stats["skipped"] += 1
                        continue

                    success = self.process_file(normalized_path, word_app)
                    
                    if success:
                        self.stats["success"] += 1
                    else:
                        self.stats["errors"] += 1

                    progress = int((index + 1) / len(self.files) * 100)
                    self.signals.progress.emit(progress)
                    print(f"Progress: {progress}%")

                    processing_time = time.time() - file_start_time
                    print(f"File processing time: {processing_time:.2f} seconds")

                    if processing_time > 3:
                        slow_files_count += 1
                        print(f"Slow processing detected ({slow_files_count} consecutive slow files)")
                    else:
                        slow_files_count = 0

                    if slow_files_count >= 3:
                        print("\nDetected slow processing, forcing new batch...")
                        break

                print(f"\nBatch {current_batch} completed, cleaning up...")
                try:
                    print("\nClosing Word application...")
                    word_app.Quit()
                    print("Word closed successfully")
                except:
                    print("Error closing Word")
                word_app = None
                gc.collect()
                print(f"Batch cleanup completed")
                slow_files_count = 0
                    
        finally:
            try:
                if word_app:
                    self.cleanup_word(word_app)
                word_app = None
                gc.collect()
                pythoncom.CoUninitialize()
                
                time.sleep(1)
                
                total_time = time.time() - self.stats["start_time"] - self.stats["total_pause_time"]
                
                print("\n=== Conversion Process Completed ===")
                print(f"Successfully converted: {self.stats['success']} files")
                print(f"Errors: {self.stats['errors']} files")
                print(f"Skipped: {self.stats['skipped']} files")
                print(f"DOC files found: {self.stats['doc_count']}")
                print(f"Old DOCX files found: {self.stats['docx_old']}")
                print(f"Modern DOCX files found: {self.stats['docx_modern']}")
                print(f"Total execution time: {total_time:.2f} seconds")
                if self.stats["total_pause_time"] > 0:
                    print(f"Total time spent paused: {self.stats['total_pause_time']:.2f} seconds")
                print("="*50)
                
                self.stats["execution_time"] = total_time
                self.signals.finished.emit(self.stats)
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
                pass

class ConversionApp(QMainWindow):
    """Aplicație pentru conversie documente"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DOC/DOCX Converter")
        self.setGeometry(100, 100, 800, 700)  # Am mărit puțin înălțimea pentru noile câmpuri
        self.setup_ui()
        self.thread_pool = QThreadPool()
        self.files_to_convert = []
        
        # Inițializare control pauză
        self.pause_flag = [False]
        self.pause_mutex = QMutex()
        self.pause_condition = QWaitCondition()

    def setup_ui(self):
        """Configurare interfață"""
        main_widget = QWidget()
        layout = QVBoxLayout()

        title_label = QLabel("Document Converter")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title_label)

        # Grup pentru taguri
        tags_group = QGroupBox("Document Tags")
        tags_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        tags_layout = QFormLayout()

        self.company_tag = QLineEdit("Birou Notarial")
        self.author_tag = QLineEdit("BIN Dascalu Oana")
        
        tags_layout.addRow("Company Tag:", self.company_tag)
        tags_layout.addRow("Author Tag:", self.author_tag)
        
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)

        # Layout pentru butoane
        button_layout = QHBoxLayout()
        
        self.browse_button = QPushButton("Select Folder")
        self.browse_button.setStyleSheet("padding: 10px; font-size: 12pt;")
        self.browse_button.clicked.connect(self.browse_folder)
        button_layout.addWidget(self.browse_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.setStyleSheet("padding: 10px; font-size: 12pt;")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)

        layout.addLayout(button_layout)

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 11pt;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("margin: 10px;")
        layout.addWidget(self.progress_bar)

        self.results_label = QLabel("")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet("font-size: 11pt; padding: 10px;")
        layout.addWidget(self.results_label)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: red; font-size: 11pt; padding: 10px;")
        layout.addWidget(self.error_label)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def toggle_pause(self):
        """Handler pentru butonul de pauză"""
        if not self.pause_flag[0]:
            self.pause_flag[0] = True
            self.pause_button.setText("Resume")
            self.status_label.setText("Conversion paused")
            print("Conversion paused by user")
        else:
            self.pause_flag[0] = False
            self.pause_button.setText("Pause")
            self.status_label.setText("Conversion resumed")
            print("Conversion resumed by user")
            self.pause_condition.wakeAll()

    def browse_folder(self):
        """Selectare folder și pornire conversie"""
        print("\n=== Starting Folder Selection ===")
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            normalized_folder = normalize_path(folder)
            print(f"Selected folder: {normalized_folder}")
            self.files_to_convert = []
            
            print("\nScanning for files...")
            for root, _, files in os.walk(normalized_folder):
                for file in files:
                    if file.lower().endswith(('.doc', '.docx')):
                        full_path = os.path.join(root, file)
                        self.files_to_convert.append(full_path)
                        print(f"Found: {full_path}")

            if not self.files_to_convert:
                print("No Word files found")
                QMessageBox.information(self, "Info", "No Word files found.")
                return

            message = f'Found {len(self.files_to_convert)} files to convert.\n'
            message += 'All .DOC files will be converted to .DOCX and originals will be deleted.\n'
            message += 'All .DOCX files will be converted to modern format.\n\n'
            message += 'Do you want to proceed?'
            
            print(f"\n{message}")
            reply = QMessageBox.question(self, 'Confirm', message,
                QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                print("User confirmed, starting conversion...")
                self.start_conversion()
            else:
                print("User cancelled operation")

    def start_conversion(self):
        """Pornește procesul de conversie"""
        self.browse_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.pause_button.setText("Pause")
        self.pause_flag[0] = False
        self.progress_bar.setValue(0)
        self.results_label.setText("")
        self.error_label.setText("")
        
        signals = WorkerSignals()
        signals.progress.connect(self.progress_bar.setValue)
        signals.file_status.connect(self.update_status)
        signals.error.connect(self.handle_error)
        signals.finished.connect(self.conversion_finished)
        signals.stats_update.connect(self.display_stats)

        task = ConversionTask(
            self.files_to_convert, 
            signals,
            self.pause_flag,
            self.pause_condition,
            self.company_tag.text(),  # Transmitem valorile curente ale tagurilor
            self.author_tag.text()
        )
        self.thread_pool.start(task)

    def display_stats(self, stats):
        """Afișează statisticile curente"""
        stats_message = (
            f"Current Statistics:\n\n"
            f"File types processed so far:\n"
            f"- DOC files: {stats['doc_count']}\n"
            f"- Old DOCX files: {stats['docx_old']}\n"
            f"- Modern DOCX files: {stats['docx_modern']}\n\n"
            f"Results so far:\n"
            f"- Successfully converted: {stats['success']}\n"
            f"- Errors: {stats['errors']}\n"
            f"- Skipped: {stats['skipped']}"
        )
        self.results_label.setText(stats_message)

    def update_status(self, message):
        """Actualizează status"""
        self.status_label.setText(message)
        print(f"Status update: {message}")

    def handle_error(self, error_message):
        """Handler pentru erori"""
        current_text = self.error_label.text()
        if current_text:
            self.error_label.setText(f"{current_text}\n{error_message}")
        else:
            self.error_label.setText(error_message)

    def conversion_finished(self, stats):
        """Handler pentru finalizare conversie"""
        self.browse_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        
        result_message = (
            f"Conversion completed!\n\n"
            f"File types found:\n"
            f"- DOC files: {stats['doc_count']}\n"
            f"- Old DOCX files: {stats['docx_old']}\n"
            f"- Modern DOCX files: {stats['docx_modern']}\n\n"
            f"Results:\n"
            f"- Successfully converted: {stats['success']}\n"
            f"- Errors: {stats['errors']}\n"
            f"- Skipped: {stats['skipped']}\n"
            f"- Total execution time: {stats['execution_time']:.2f} seconds"
        )
        
        if stats["total_pause_time"] > 0:
            result_message += f"\n- Total time spent paused: {stats['total_pause_time']:.2f} seconds"
        
        self.status_label.setText("Conversion completed!")
        self.results_label.setText(result_message)
        
        QMessageBox.information(self, "Complete", 
            f"{result_message}\n\nCheck conversion_debug.log for detailed information.")

def main():
    """Pornire aplicație"""
    app = QApplication(sys.argv)
    window = ConversionApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()