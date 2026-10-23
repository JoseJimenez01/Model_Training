"""Selector auxiliar local de etapa01; no es la interfaz global de E1."""
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from GetPages import extraer


class SelectorPDF:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.events = Queue()
        root.title('E1 - Extraccion de paginas PDF')
        root.minsize(620, 340)
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(1, weight=1)
        self.pdf = tk.StringVar()
        self.destination = tk.StringVar()
        self.kind = tk.StringVar(value='tomo')
        self.pages = tk.StringVar()
        self.status = tk.StringVar(value='Seleccione un PDF y la carpeta donde guardar el resultado.')
        self.controls = []
        for row, label, variable, action in (
            (0, 'Archivo PDF', self.pdf, self.buscar_pdf),
            (1, 'Guardar dentro de', self.destination, self.buscar_salida),
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=6)
            entry = ttk.Entry(frame, textvariable=variable, state='readonly')
            entry.grid(row=row, column=1, sticky='ew', padx=8)
            button = ttk.Button(frame, text='Buscar...', command=action)
            button.grid(row=row, column=2)
            self.controls.append(button)
        ttk.Label(frame, text='Tipo de documento').grid(row=2, column=0, sticky='w', pady=6)
        self.type_box = ttk.Combobox(frame, textvariable=self.kind, values=('tomo', 'indice'), state='readonly')
        self.type_box.grid(row=2, column=1, sticky='w', padx=8)
        ttk.Label(frame, text='Paginas del PDF').grid(row=3, column=0, sticky='w', pady=6)
        self.page_entry = ttk.Entry(frame, textvariable=self.pages)
        self.page_entry.grid(row=3, column=1, sticky='ew', padx=8)
        ttk.Label(frame, text='Vacio: todas. Ejemplo: 1,3-5. Numeracion desde 1.').grid(row=4, column=1, sticky='w', padx=8)
        ttk.Label(frame, text='Salida: PNG RGB a 300 DPI. Se crea una subcarpeta nueva.').grid(row=5, column=0, columnspan=3, sticky='w', pady=12)
        self.run_button = ttk.Button(frame, text='Extraer paginas', command=self.ejecutar)
        self.run_button.grid(row=6, column=1, sticky='w', padx=8)
        self.controls.append(self.run_button)
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.grid(row=7, column=0, columnspan=3, sticky='ew', pady=12)
        ttk.Label(frame, textvariable=self.status, wraplength=600).grid(row=8, column=0, columnspan=3, sticky='w')
        root.protocol('WM_DELETE_WINDOW', self.cerrar)

    def buscar_pdf(self):
        selected = filedialog.askopenfilename(parent=self.root, title='Seleccionar PDF',
            filetypes=[('Documentos PDF', '*.pdf')])
        if selected:
            self.pdf.set(selected)

    def buscar_salida(self):
        selected = filedialog.askdirectory(parent=self.root, title='Carpeta donde crear el resultado', mustexist=True)
        if selected:
            self.destination.set(selected)

    def ejecutar(self):
        if self.busy:
            return
        if not self.pdf.get() or not self.destination.get():
            messagebox.showerror('Faltan datos', 'Seleccione el PDF y la carpeta de destino.', parent=self.root)
            return
        pdf = Path(self.pdf.get())
        output = Path(self.destination.get()) / (pdf.stem + '_extraccion_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        kind, pages = self.kind.get(), self.pages.get().strip() or None
        self.busy = True
        for control in self.controls:
            control.configure(state='disabled')
        self.type_box.configure(state='disabled')
        self.page_entry.configure(state='disabled')
        self.progress.start(12)
        self.status.set('Extrayendo paginas. La ventana seguira disponible; espere el resultado.')

        def work():
            # All Tk operations stay in the UI thread; this worker only processes files.
            try:
                result = extraer(pdf, output, kind, pages, 300)
                self.events.put(('resultado', result, output))
            except Exception as exc:
                self.events.put(('error', str(exc), output))

        Thread(target=work, daemon=True).start()
        self.root.after(100, self.recibir)

    def recibir(self):
        try:
            event, payload, output = self.events.get_nowait()
        except Empty:
            self.root.after(100, self.recibir)
            return
        self.busy = False
        self.progress.stop()
        for control in self.controls:
            control.configure(state='normal')
        self.type_box.configure(state='readonly')
        self.page_entry.configure(state='normal')
        if event == 'error':
            self.status.set('No se completo la extraccion. Revise el error e intentelo de nuevo.')
            messagebox.showerror('Error de extraccion', payload, parent=self.root)
            return
        text = (f"Estado: {payload['estado']}. Extraidas: {payload['paginas_extraidas']}. "
                f"Errores: {payload['paginas_con_error']}.\nResultado: {output}")
        self.status.set(text)
        notify = messagebox.showinfo if payload['estado'] == 'completo' else messagebox.showwarning
        notify('Resultado de extraccion', text, parent=self.root)

    def cerrar(self):
        if self.busy:
            messagebox.showinfo('Extraccion en curso', 'Espere a que termine antes de cerrar.', parent=self.root)
        else:
            self.root.destroy()


def iniciar():
    try:
        root = tk.Tk()
    except tk.TclError:
        text = ('No se pudo iniciar la ventana Tcl/Tk de Python. '
                'Revise la instalacion de Python y el componente Tcl/Tk. '
                'Tambien puede ejecutar GetPages.py por comandos; consulte README.md.')
        if sys.stderr is not None:
            print(text, file=sys.stderr)
        if sys.platform == 'win32':
            # Native dialog works even if the Tcl/Tk runtime cannot start.
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, 'No se pudo abrir el extractor', 0x10)
        return 1
    SelectorPDF(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    iniciar()
