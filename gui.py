import os
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
from time import sleep
import multiprocessing as mp
from bot import Bot
from TimeManager import TimeManager
from threading import Thread
from ctypes import c_char
from datetime import time, datetime, timedelta
import logging
import selenium
import requests
from bs4 import BeautifulSoup
import pause
import sys




if getattr(sys, 'frozen', False):
    driver_dir = os.path.join(os.path.dirname(sys.executable), 'drivers')
elif __file__:
    driver_dir = os.path.dirname(__file__)


class Task:
    def __init__(self):
        self.submit_time = None
        self.subject_area = StringVar()
        self.lv_number = StringVar()
        self.time_str = StringVar()

    def get_vars(self):
        return self.subject_area, self.lv_number, self.time_str


class TaskContainer:
    def __init__(self):
        self.elems = [Task()]

    def add_elem(self):
        new = Task()
        self.elems.append(new)
        return new

    def pop(self):
        return self.elems.pop()

    def get_list(self):
        ret = {}
        for elem in self.elems:
            try:
                ret[elem.submit_time].append((elem.subject_area.get(), elem.lv_number.get()))
            except KeyError:
                ret[elem.submit_time] = [(elem.subject_area.get(), elem.lv_number.get())]
        return ret


def visit_widgets(root, visitor):
    visitor(root)
    for child in root.winfo_children():
        visit_widgets(child, visitor)


class Gui:
    def __init__(self):
        self.logger = logging.getLogger('main')
        self.window = Tk()
        self.window.title("LPIS script")
        try:
            icon_path = os.path.join(driver_dir, 'icon.ico')
            self.window.iconbitmap(icon_path)
        except Exception:
            pass
        self.window.resizable(False, False)

        self.entry_frame = Frame(self.window)
        self.entry_frame.pack(padx=(3,10), expand=YES, fill=X)
        self.task_frames = []

        self.buttons_frame = Frame(self.window)
        self.buttons_frame.pack(padx=(3, 10), expand=YES, fill=X)

        self.driver_status = mp.Array(c_char, 200)
        self.driver_status.value = b'Not started'
        self.fields = ('Subject Area', 'Course ID(4-digit)', 'Time (hh:mm)')
        self.tasks = TaskContainer()

        self.field_font = ('Calibri', 14)
        self.label_font = ('Calibri', 12)
        self.button_style = Style()
        self.button_style.configure('my.TButton', font=('Calibri', 13))

        info_text = Label(self.entry_frame, text="Enter your LPIS login", font=('Calibri', 16))
        info_text.pack()

        self.username = StringVar(self.window, '')
        self.pw = StringVar(self.window, '')
        self.makefields(fields=('Matriculation nb', 'Password'), vars=(self.username, self.pw))

        current_task = self.tasks.elems[0]
        self.makefields(fields=self.fields, vars=current_task.get_vars())

        current_task.time_str.set('now')

        row = Frame(self.buttons_frame)
        lab = Label(row, width=12, text="Browser:", anchor='w', font=self.label_font)
        row.pack(side=TOP, fill=X, padx=5, pady=2)
        lab.pack(side=LEFT)
        self.browser = StringVar()
        self.browser.set('Google Chrome')
        dropdown = tk.OptionMenu(row, self.browser, 'Google Chrome', 'Firefox')
        dropdown.config(width=35)
        dropdown.pack(side=RIGHT, expand=NO)

        self.headless = IntVar()
        self.headless.set(1)
        self.check_button1 = Checkbutton(self.buttons_frame, text='Run with visual browser (less efficient) ', variable=self.headless)
        self.check_button1.pack()

        self.atomic_watch = IntVar()
        self.atomic_watch.set(1)
        self.check_button2 = Checkbutton(self.buttons_frame, text='Use online atomic time instead of local', variable=self.atomic_watch)
        self.check_button2.pack()

        self.add_button = Button(self.buttons_frame, text="Add course", command=self.add_onclick, style='my.TButton')
        self.add_button.pack(padx=20, side=LEFT)
        self.submit_button = Button(self.buttons_frame, text="Start Script", command=self.submit_onclick, style='my.TButton')
        self.submit_button.pack(side=RIGHT, padx=10, pady=10)
        self.window.bind('<Return>', self.submit_onclick)
        self.remove_button = Button(self.window, text='Remove course', command=self.remove_onclick, style='my.TButton')

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.exit_event = mp.Event()
        self.window.mainloop()

    def makefields(self, fields, vars):
        if len(fields) != len(vars):
            raise RuntimeError('Unequal amount')
        i = 0
        container = Frame(self.entry_frame)
        container.pack(pady=7, expand=YES, fill=X)
        while i < len(fields):
            row = Frame(container)
            lab = Label(row, width=16, text=fields[i] + ": ", anchor='w', font=self.label_font)
            ent = Entry(row, width=25, font=self.field_font, textvariable=vars[i])
            if fields[i] == 'Password':
                ent.config(show='*')
            row.pack(side=TOP, fill=X, padx=5, pady=2)
            lab.pack(side=LEFT)
            ent.pack(side=RIGHT, fill=X)
            i += 1
        return container

    def remove_onclick(self):
        self.task_frames.pop().pack_forget()
        self.tasks.pop()
        if len(self.task_frames) == 0:
            self.remove_button.pack_forget()

    def add_onclick(self):
        task = self.tasks.add_elem()
        frame = self.makefields(fields=self.fields, vars=(task.get_vars()))
        self.task_frames.append(frame)
        task.time_str.set('now')
        self.remove_button.pack(pady=(0,4), padx=20, side=LEFT)

    def submit_onclick(self, event=None):
        if not len(self.username.get()) or not len(self.pw.get()):
            return

        try:
            time_manager = TimeManager(vanilla=not self.atomic_watch.get())
            corrected_datetime = time_manager.corrected_now()
            for task in self.tasks.elems:
                if not all([len(x.get()) for x in [task.time_str, task.lv_number, task.subject_area]]):
                    return

                try:
                    time_input = [int(string) for string in task.time_str.get().split(':')]
                    if len(time_input) == 2:
                        time_input.append(0)
                        time_input.append(0)
                    elif len(time_input) == 3:
                        time_input.append(0)
                    time_tmp = time(hour=time_input[0], minute=time_input[1], second=time_input[2], microsecond=time_input[3]*100000)
                    date_tmp = datetime.today()
                    if (datetime.combine(datetime.today(), time_tmp) - timedelta(minutes=1, seconds=10)) < corrected_datetime:
                        date_tmp += timedelta(days=1)
                    task.submit_time = datetime.combine(date_tmp, time_tmp)
                except (IndexError, ValueError) as e:
                    if str(task.time_str.get()) == 'now':
                        task.submit_time = 'now'
                    else:
                        return
        except requests.exceptions.ConnectionError:
            time_manager = None
            pass

        bot = Bot(username=self.username.get(), password=self.pw.get(), tasks=self.tasks.get_list(),
                  exit_event=self.exit_event, browser=self.browser.get(), driver_status=self.driver_status,
                  time_manager=time_manager, headless=not self.headless.get())

        self.ui_update_thread = Thread(target=self.ui_update)
        self.ui_update_thread.setDaemon(True)
        self.ui_update_thread.start()

        self.driver_process = mp.Process(target=bot)
        self.driver_process.daemon = True
        self.driver_process.start()

    def ui_update(self):
        self.driver_status.value = b'Preparing'
        if len(self.task_frames) != 0:
            self.remove_button.pack_forget()

        def visitor(widget):
            try:
                widget.config(state='disabled')
            except Exception:
                pass
        visit_widgets(self.window, visitor)

        line = Separator(self.window, orient=HORIZONTAL)
        line.pack(fill=X)
        status_label = Label(self.window, text="", font=self.field_font)
        status_label.pack(pady=(5, 12))

        while self.driver_process.is_alive():
            status_label.config(text=self.driver_status.value)
            sleep(0.2)
        else:
            status_label.pack_forget()
            line.pack_forget()
            if len(self.task_frames) != 0:
                self.remove_button.pack(pady=(0,4), padx=20, side=LEFT)

            def visitor(widget):
                try:
                    widget.config(state='normal')
                except Exception:
                    pass
            visit_widgets(self.window, visitor)

        self.driver_status.value = b'Not started'

    def add_label(self, text, side):
        label = Label(self.window, font=self.field_font, text=text)
        if side == 'right':
            label.pack(side=RIGHT, pady=(0, 12))
        elif side == 'left':
            label.pack(side=LEFT)
        else:
            label.pack()

    def on_closing(self):
        try:
            if self.driver_process.is_alive():
                self.exit_event.set()
                sleep(0.4)

        except AttributeError:
            pass

        finally:
            self.window.destroy()


if __name__ == '__main__':
    mp.freeze_support()
    gui = Gui()
