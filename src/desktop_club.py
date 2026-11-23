"""Standalone desktop frontend for the validated melonDS core and club bridge.

Tk uses only Python's standard library. Native emulation stays in GameSession's
isolated process; the same dynamic fixtures and final-screen protection apply.
"""
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from game_session import GameSession

ROOT=Path(__file__).resolve().parents[1]
KEYS={'Up':'UP','Down':'DOWN','Left':'LEFT','Right':'RIGHT',
      'z':'UP','q':'LEFT','s':'DOWN','d':'RIGHT',
      'a':'A','b':'B','x':'X','y':'Y','Return':'START'}


class ClubWindow:
    def __init__(self, root):
        self.root=root
        root.title('InazumIA — Local du club · cœur melonDS')
        self.scale=2 if root.winfo_screenheight()>=950 else 1
        self.lock=threading.Lock()
        self.held=set();self.taps=set();self.touch=None
        self.outputs=queue.Queue();self.commands=queue.Queue()
        self.stop=threading.Event();self.paused=False
        self.status=tk.StringVar(value='Ouverture du local avec melonDS…')
        ttk.Label(root,textvariable=self.status,padding=8,wraplength=500).pack(fill='x')
        self.canvas=tk.Canvas(root,width=256*self.scale,height=384*self.scale,
                              background='#101820',highlightthickness=0)
        self.canvas.pack()
        self.image_id=self.canvas.create_image(0,0,anchor='nw')
        controls=ttk.Frame(root,padding=8);controls.pack(fill='x')
        ttk.Button(controls,text='Pause / Continuer',command=self.toggle_pause).pack(side='left')
        ttk.Button(controls,text='Retour au local',command=lambda:self.commands.put('reset_match')).pack(side='left',padx=8)
        ttk.Label(root,text='Flèches / ZQSD : marcher · A : parler · B X Y · Entrée : Start\nÉcran du bas : maintenir ou glisser le stylet.',padding=8).pack()
        root.bind('<KeyPress>',self.key_down);root.bind('<KeyRelease>',self.key_up)
        root.bind('<FocusOut>',lambda event:self.release())
        self.canvas.bind('<ButtonPress-1>',self.stylus)
        self.canvas.bind('<B1-Motion>',self.stylus)
        self.canvas.bind('<ButtonRelease-1>',lambda event:self.release_touch())
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
        root.after(30,self.refresh)
        self.canvas.focus_set()

    def key_down(self,event):
        key=KEYS.get(event.keysym)
        if key:
            with self.lock:
                if key not in self.held:self.taps.add(key)
                self.held.add(key)
            return 'break'

    def key_up(self,event):
        with self.lock:self.held.discard(KEYS.get(event.keysym))

    def release(self):
        with self.lock:self.held.clear();self.taps.clear();self.touch=None

    def release_touch(self):
        with self.lock:self.touch=None

    def stylus(self,event):
        self.canvas.focus_set()
        x,y=event.x//self.scale,event.y//self.scale-192
        with self.lock:self.touch=[x,y] if 0<=x<256 and 0<=y<192 else None

    def toggle_pause(self):
        self.paused=not self.paused
        self.release()
        self.canvas.focus_set()

    def run(self):
        game=GameSession()
        try:
            sid=game.open('club',cancel=self.stop)['session_id']
            value=game.request(sid,'observe')
            self.outputs.put(value)
            while not self.stop.is_set():
                started=time.monotonic()
                with self.lock:
                    keys=list(self.held|self.taps);self.taps.clear()
                    touch=self.touch
                try:command=self.commands.get_nowait()
                except queue.Empty:command=None
                if command:
                    value=game.request(sid,command,revision=value['revision'])
                elif not self.paused or keys or touch:
                    value=game.request(sid,'step',revision=value['revision'],frames=6,
                                       keys=keys,touch=touch,continuous=True)
                else:
                    self.stop.wait(.05);continue
                if 'error' in value:raise RuntimeError(value['error'])
                self.outputs.put(value)
                self.stop.wait(max(0,.1-(time.monotonic()-started)))
        except Exception as error:
            if not self.stop.is_set():self.outputs.put({'error':str(error)})
        finally:game.close()

    def refresh(self):
        latest=None
        while True:
            try:latest=self.outputs.get_nowait()
            except queue.Empty:break
        if latest:
            if 'error' in latest:self.status.set('Erreur : '+latest['error'])
            else:
                self.photo=tk.PhotoImage(data=latest['image']).zoom(self.scale,self.scale)
                self.canvas.itemconfigure(self.image_id,image=self.photo)
                phase=latest.get('match',{}).get('phase')
                self.status.set({'club':'Local du club — va voir Hillman et appuie sur A.',
                    'choosing':'Choisis une affiche avec Oui / Non.',
                    'idle':'Match prêt — A pour continuer.',
                    'dialogue':'Les capitaines prennent la parole — A pour avancer.',
                    'playing':'Match amical — commandes DS et stylet.',
                    'result':'Match terminé — A pour revenir au local.'}.get(phase,'Chargement…'))
        if not self.stop.is_set():self.root.after(30,self.refresh)

    def close(self):
        self.stop.set();self.release();self.root.destroy()


def main():
    os.chdir(ROOT)
    root=tk.Tk()
    app=ClubWindow(root)
    root.mainloop()
    app.stop.set();app.thread.join(5)


if __name__=='__main__':main()
