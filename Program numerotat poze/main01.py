import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import re

class AplicatieRedenumire:
    def __init__(self, root):
        self.root = root
        self.root.title("Redenumire Fișiere JPG")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        # Variabile
        self.folder_path = tk.StringVar()
        self.start_number = tk.StringVar(value="0001")
        
        # Crearea interfeței
        self.create_widgets()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Secțiunea pentru selectarea folderului
        folder_frame = ttk.LabelFrame(main_frame, text="Selectare Folder", padding="10")
        folder_frame.pack(fill=tk.X, pady=10)
        
        ttk.Entry(folder_frame, textvariable=self.folder_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT, padx=5)
        
        # Secțiunea pentru numărul de start
        number_frame = ttk.LabelFrame(main_frame, text="Număr de Start", padding="10")
        number_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(number_frame, text="Introduceți numărul de start (4 cifre):").pack(anchor=tk.W, pady=5)
        
        # Validare pentru a accepta doar 4 cifre
        vcmd = (self.root.register(self.validate_number), '%P')
        ttk.Entry(number_frame, textvariable=self.start_number, width=10, validate="key", validatecommand=vcmd).pack(anchor=tk.W)
        
        # Butonul de aplicare
        ttk.Button(main_frame, text="Aplică Redenumire", command=self.apply_renaming).pack(pady=20)
        
        # Bara de progres
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=460, mode='determinate')
        self.progress.pack(pady=10)
        
        # Eticheta pentru status
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(pady=5)
    
    def validate_number(self, value):
        # Validează ca intrarea să fie 4 cifre
        if value == "":
            return True
        if len(value) <= 4 and value.isdigit():
            return True
        return False
    
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
    
    def apply_renaming(self):
        folder_path = self.folder_path.get()
        start_number_str = self.start_number.get()
        
        # Verificări
        if not folder_path:
            messagebox.showerror("Eroare", "Vă rugăm să selectați un folder.")
            return
        
        if len(start_number_str) != 4 or not start_number_str.isdigit():
            messagebox.showerror("Eroare", "Vă rugăm să introduceți un număr valid de 4 cifre.")
            return
        
        start_number = int(start_number_str)
        
        # Colectează toate fișierele JPG
        jpg_files = []
        
        for file in os.listdir(folder_path):
            if file.lower().endswith('.jpg'):
                jpg_files.append(file)
        
        if not jpg_files:
            messagebox.showinfo("Informație", "Nu s-au găsit fișiere JPG în folderul selectat.")
            return
        
        # Sortează fișierele după nume
        jpg_files.sort()
        
        total_files = len(jpg_files)
        self.progress["maximum"] = total_files
        self.progress["value"] = 0
        self.status_label.config(text=f"Se redenumesc 0/{total_files} fișiere...")
        
        # Procesul de redenumire
        current_number = start_number
        renamed_count = 0
        
        for file in jpg_files:
            old_path = os.path.join(folder_path, file)
            # Păstrează numele original și adaugă prefixul numeric
            new_name = f"{current_number:04d}-{file}"
            new_path = os.path.join(folder_path, new_name)
            
            # Verifică dacă fișierul există deja (pentru a evita suprascrierea)
            counter = 1
            while os.path.exists(new_path):
                new_name = f"{current_number:04d}-({counter}){file}"
                new_path = os.path.join(folder_path, new_name)
                counter += 1
            
            try:
                os.rename(old_path, new_path)
                current_number += 1
                renamed_count += 1
                
                self.progress["value"] = renamed_count
                self.status_label.config(text=f"Se redenumesc {renamed_count}/{total_files} fișiere...")
                self.root.update_idletasks()
            except Exception as e:
                messagebox.showerror("Eroare", f"Eroare la redenumirea fișierului {file}: {str(e)}")
        
        self.status_label.config(text=f"Redenumire completă! {renamed_count} fișiere procesate.")
        messagebox.showinfo("Succes", f"Redenumire completă! {renamed_count} fișiere procesate.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AplicatieRedenumire(root)
    root.mainloop()