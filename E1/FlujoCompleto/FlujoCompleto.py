"""Entrada unica: selector de PDF y ejecucion provisional de las cinco etapas."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from queue import Queue, Empty
import sys
from threading import Event, Thread
import webbrowser


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    try:
        root=tk.Tk()
    except tk.TclError:
        text='No se pudo iniciar Tcl/Tk. Revise el componente Tcl/Tk de Python o use --config; consulte README.md.'
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,text,'Flujo E1',0x10)
        return 1
    root.title('E1 - Flujo provisional de tomos')
    root.minsize(800,600)
    frame=ttk.Frame(root,padding=16);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
    fields={name:tk.StringVar() for name in ('pdf','destino','modelo','modelo_carnet','python_modelo','tesseract')}
    fields['paginas']=tk.StringVar(value='1')
    fields['variante']=tk.StringVar(value='original')
    fields['binarizacion']=tk.StringVar(value='otsu')
    txt=tk.BooleanVar(value=False)
    settings=Path(__file__).resolve().parent/'ajustes.local.json'
    if settings.is_file():
        try:
            saved=json.loads(settings.read_text(encoding='utf-8'))
            for key in ('destino','modelo','modelo_carnet','python_modelo','tesseract'):
                if saved.get(key):fields[key].set(saved[key])
        except (OSError,ValueError):pass
    status=tk.StringVar(value='Elija PDF y modelos. Se empieza por pagina1; vacio significa todas.')
    queue=Queue();cancel=Event();state={'busy':False,'result':None}
    controls=[]
    defaults=Path(__file__).resolve().parent/'pesos'
    for key,file in [('modelo','detector_v32.pt'),('modelo_carnet','carnet_v76.pt')]:
        if (defaults/file).is_file():fields[key].set(str(defaults/file))
    labels={'pdf':'Tomo PDF','destino':'Guardar dentro de','modelo':'Detector v32 (.pt)',
        'modelo_carnet':'Localizador carnet (.pt, opcional)','python_modelo':'Python del detector (opcional)',
        'tesseract':'Tesseract.exe (opcional)'}
    def choose(name):
        if name=='destino':value=filedialog.askdirectory(parent=root,mustexist=True)
        else:
            types=[('PDF','*.pdf')] if name=='pdf' else [('Modelos','*.pt')] if name in ('modelo','modelo_carnet') else [('Ejecutables','*.exe')]
            value=filedialog.askopenfilename(parent=root,title=labels[name],filetypes=types)
        if value:fields[name].set(value)
    for row,(name,label) in enumerate(labels.items()):
        ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=6)
        entry=ttk.Entry(frame,textvariable=fields[name]);entry.grid(row=row,column=1,sticky='ew',padx=8)
        button=ttk.Button(frame,text='Buscar...',command=lambda n=name:choose(n));button.grid(row=row,column=2)
        controls.extend([entry,button])
    for row,name,label,values in [(6,'paginas','Paginas PDF (ej.: 1,3-5)',None),
        (7,'variante','Tratamiento para OCR',('original','gris','clahe_gamma','vertical_1x3')),
        (8,'binarizacion','Binarizacion del cuerpo',('otsu','sauvola'))]:
        ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=6)
        control=ttk.Combobox(frame,textvariable=fields[name],values=values,state='readonly') if values else ttk.Entry(frame,textvariable=fields[name])
        control.grid(row=row,column=1,sticky='ew',padx=8);controls.append(control)
    box=ttk.Checkbutton(frame,text='Generar tambien TXT completo (opcional)',variable=txt)
    box.grid(row=9,column=0,columnspan=3,sticky='w',pady=8);controls.append(box)
    ttk.Label(frame,text='Resultado experimental: puede omitir texto y dejar manuscritos residuales. Revise alertas.',wraplength=750).grid(row=10,column=0,columnspan=3,sticky='w',pady=8)
    bar=ttk.Progressbar(frame);bar.grid(row=11,column=0,columnspan=3,sticky='ew',pady=8)
    ttk.Label(frame,textvariable=status,wraplength=750).grid(row=12,column=0,columnspan=3,sticky='w',pady=8)
    buttons=ttk.Frame(frame);buttons.grid(row=13,column=0,columnspan=3,sticky='w')
    def opening():
        if state['result']:webbrowser.open(Path(state['result']['visor']).resolve().as_uri())
    def receive():
        try:
            while True:
                event,payload=queue.get_nowait()
                if event=='progress':
                    text,done,total=payload;status.set(text);bar.configure(maximum=total,value=done)
                else:
                    state['busy']=False
                    for control in controls:control.configure(state='readonly' if isinstance(control,ttk.Combobox) else 'normal')
                    start.configure(state='normal');stop.configure(state='disabled')
                    if event=='result':
                        state['result']=payload;open_button.configure(state='normal')
                        status.set(payload['estado']+'\n'+payload['salida'])
                        messagebox.showinfo('Resultado',payload['estado']+'\nJSON y visor guardados en:\n'+payload['salida'],parent=root)
                    else:
                        status.set('Proceso detenido. No se sustituyo el detector.')
                        messagebox.showerror('No se pudo completar el flujo',payload,parent=root)
        except Empty:pass
        if state['busy']:root.after(100,receive)
    def launch():
        if state['busy']:return
        if any(not fields[k].get().strip() for k in ('pdf','destino','modelo')):
            messagebox.showerror('Faltan datos','Seleccione PDF, destino y detector v32.',parent=root);return
        config={k:v.get().strip() for k,v in fields.items() if k!='destino'}
        config['guardar_txt']=txt.get()
        config['salida']=str(Path(fields['destino'].get())/('flujo_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')))
        try:
            settings.write_text(json.dumps({k:fields[k].get().strip() for k in
                ('destino','modelo','modelo_carnet','python_modelo','tesseract')},ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError:pass
        state.update(busy=True,result=None);cancel.clear();open_button.configure(state='disabled')
        for control in controls:control.configure(state='disabled')
        start.configure(state='disabled');stop.configure(state='normal');status.set('Comprobando dependencias...')
        def work():
            try:
                from pipeline import run
                value=run(config,lambda *p:queue.put(('progress',p)),cancel)
                queue.put(('result',value))
            except Exception as exc:queue.put(('error',f'{type(exc).__name__}: {exc}'))
        Thread(target=work,daemon=True).start();root.after(100,receive)
    start=ttk.Button(buttons,text='Procesar tomo',command=launch);start.pack(side='left',padx=5)
    stop=ttk.Button(buttons,text='Detener',command=lambda:(cancel.set(),status.set('Detencion solicitada; esperando operacion actual...')),state='disabled');stop.pack(side='left',padx=5)
    open_button=ttk.Button(buttons,text='Ver resultado por pagina',command=opening,state='disabled');open_button.pack(side='left',padx=5)
    def close():
        if state['busy']:cancel.set();status.set('Espere la operacion actual antes de cerrar.')
        else:root.destroy()
    root.protocol('WM_DELETE_WINDOW',close);root.mainloop();return 0


def main():
    if len(sys.argv)==1:return gui()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    try:
        from pipeline import run
        config=json.loads(args.config.read_text(encoding='utf-8'))
        for key in ('pdf','salida','modelo','modelo_carnet','python_modelo','tesseract'):
            if config.get(key):
                value=Path(config[key]);config[key]=str(value if value.is_absolute() else args.config.parent/value)
        result=run(config,lambda text,done,total:print(f'{done}/{total}: {text}',flush=True),Event())
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 2 if result['estado'] in ('cancelado','incompleto') else 0
    except Exception as exc:
        print(f'Flujo detenido: {type(exc).__name__}: {exc}',file=sys.stderr);return 1


if __name__=='__main__':
    raise SystemExit(main())
