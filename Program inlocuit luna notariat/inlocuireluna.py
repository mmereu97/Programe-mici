import os
from tkinter import Tk, Label, Entry, Button, filedialog, messagebox
from docx import Document
import tkinter.font as tkFont

class WordReplacerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Word Replacer")
        self.root.geometry("600x300")  # Dimensiuni mai mari pentru fereastră

        # Fonturi mai mari
        self.font_large = tkFont.Font(family="Arial", size=14)
        self.font_medium = tkFont.Font(family="Arial", size=12)

        # Variabilele pentru path și cuvinte
        self.folder_path = ""
        self.word_to_find = ""
        self.word_to_replace = ""

        # Elemente UI
        self.create_widgets()

    def create_widgets(self):
        # Buton pentru selectarea folderului
        self.browse_button = Button(self.root, text="Browse Folder", font=self.font_large, command=self.browse_folder)
        self.browse_button.pack(pady=20)

        # Câmpuri de text pentru cuvinte
        self.word_label1 = Label(self.root, text="Cuvânt de înlocuit:", font=self.font_medium)
        self.word_label1.pack()
        self.word_entry1 = Entry(self.root, font=self.font_large, width=30)
        self.word_entry1.pack(pady=10)

        self.word_label2 = Label(self.root, text="Cuvânt de înlocuire:", font=self.font_medium)
        self.word_label2.pack()
        self.word_entry2 = Entry(self.root, font=self.font_large, width=30)
        self.word_entry2.pack(pady=10)

        # Butonul Start
        self.start_button = Button(self.root, text="Start", font=self.font_large, command=self.start_replacement)
        self.start_button.pack(pady=20)

    def browse_folder(self):
        # Deschide dialogul de selectare a folderului
        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            messagebox.showinfo("Folder selected", f"Folderul selectat: {self.folder_path}")

    def start_replacement(self):
        # Ia cuvintele de înlocuit și înlocuire
        self.word_to_find = self.word_entry1.get().strip()
        self.word_to_replace = self.word_entry2.get().strip()

        # Verifică dacă toate câmpurile sunt completate
        if not self.folder_path or not self.word_to_find or not self.word_to_replace:
            messagebox.showwarning("Warning", "Toate câmpurile trebuie completate!")
            return

        # Parcurge toate fișierele din folderul selectat și subfolderele
        for root, _, files in os.walk(self.folder_path):
            for file in files:
                if file.startswith("@@") and file.endswith(".docx"):
                    file_path = os.path.join(root, file)
                    self.replace_word_in_file(file_path)

        messagebox.showinfo("Info", "Înlocuirea s-a terminat cu succes!")

    def replace_word_in_file(self, file_path):
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    if self.word_to_find in run.text:
                        # Înlocuiește cuvântul oriunde apare
                        run.text = run.text.replace(self.word_to_find, self.word_to_replace)
            doc.save(file_path)  # Salvează fișierul modificat
        except Exception as e:
            messagebox.showerror("Error", f"Eroare la procesarea fișierului {file_path}: {e}")

# Inițializarea aplicației
if __name__ == "__main__":
    root = Tk()
    app = WordReplacerApp(root)
    root.mainloop()