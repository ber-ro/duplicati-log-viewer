# Browse Duplicati log files
# Copyright (C) 2022 Bernhard Rotter <bernhard.rotter@gmail.com>

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA

from collections import deque
from tkinter import *
from tkinter import ttk
import argparse
import os
import re
import time
import yaml


def main():
    t0 = time.process_time()
    op = os.environ.get("DUPLICATI__OPERATIONNAME")
    if op is not None and op != "Backup":
        return  # do not run on operation List when restoring
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'logfile', nargs='?', default=os.environ.get("DUPLICATI__log_file")
    )
    global args
    args = parser.parse_args()
    loadCfg()
    gui = Gui(readLog())
    t1 = time.process_time()
    print("Start-up time:", t1 - t0, "seconds")
    gui.root.mainloop()


class Gui:
    def __init__(self, logData):
        self.logData = logData
        self.state = []
        self.root = Tk()
        self.root.title(os.path.basename(os.path.realpath(__file__)))
        self.root.geometry("1200x800")
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.label = Label(self.root, anchor=W)
        self.lsbox = Listbox(self.root, activestyle=NONE)
        self.textw = Text(self.root, wrap=NONE, font=("Arial", 9), relief=SOLID)
        self.yscrl = ttk.Scrollbar(self.root, orient=VERTICAL)
        self.xscrl = ttk.Scrollbar(self.root, orient=HORIZONTAL)

        self.label.grid(row=0, column=0, sticky="nsew")
        self.lsbox.grid(row=1, column=0, sticky="nsew")
        self.textw.grid(row=1, column=0, sticky="nsew")
        self.yscrl.grid(row=1, column=1, sticky="ns")
        self.xscrl.grid(row=2, column=0, sticky="ew")
        self.textw.grid_remove()

        self.lsbox.bind("<Key>", self.keyhandler)
        self.textw.bind("<Key>", self.keyhandler)
        self.textw.tag_configure('highlight', background='yellow')
        # tree.bind('<Control-c>', copy)

        self.fillBackups()
        self.select(0)
        self.scrollbars(self.lsbox)

    def keyhandler(self, event):
        if event.keysym == 'Return' or event.keysym == 'Right':
            selected = self.lsbox.curselection()
            if len(selected) == 0:
                return
            current = self.lsbox.get(selected[0])
            if len(self.state) == 0:
                self.newState([current])
                self.lsbox.delete(0, END)
                for t in sorted(self.logData.getTags(current)):
                    self.lsbox.insert(END, t)
                self.select(0)
            elif len(self.state) == 1:
                self.newState([self.state[0], current])
                self.lsbox.grid_remove()
                self.textw.grid()
                self.textw.focus_set()
                self.textw.configure(state=NORMAL)
                self.textw.delete('1.0', END)
                self.scrollbars(self.textw)
                for l in self.logData.getTags(self.state[0])[current]:
                    if not isIgnored(l):
                        highlight_insert(self.textw, l)
                        self.textw.insert(END, "\n")
                self.textw.delete("end-2c", END)  # delete last newline
                self.textw.configure(state=DISABLED)
        elif event.keysym == 'Escape' or event.keysym == 'Left':
            if len(self.state) == 1:
                self.fillBackups(self.state[0])
                self.newState([])
            elif len(self.state) == 2:
                self.textw.grid_remove()
                self.lsbox.grid()
                self.lsbox.focus_set()
                self.scrollbars(self.lsbox)
                self.newState([self.state[0]])

    def newState(self, state):
        self.state = state
        self.label.config(text=" > ".join(state))

    def fillBackups(self, current=None):
        self.lsbox.delete(0, END)
        for name in sorted(self.logData.backups):
            self.lsbox.insert(0, name)
            if name == current:
                self.select(0)

    def select(self, num):
        self.lsbox.activate(num)
        self.lsbox.select_set(num)  # This only sets focus on the first item.
        self.lsbox.event_generate("<<ListboxSelect>>")
        self.lsbox.focus_set()

    def scrollbars(self, widget):
        self.xscrl.config(command=widget.xview)
        self.yscrl.config(command=widget.yview)
        widget.configure(xscrollcommand=self.xscrl.set,
                         yscrollcommand=self.yscrl.set)


# def copy(event):
#     # values = [tree.item(i, 'text') for i in tree.selection()]
#     root.clipboard_clear()
#     # root.clipboard_append("\n".join(values))


class DuplicatiLogData:
    def __init__(self, ):
        self.queue = deque()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.prepareData()

    def addBackup(self, date):
        max = cfg.get("show-logs-number") or 0
        if max != 0 and len(self.queue) >= max:
            self.queue.popleft()
        self.queue.append({'date': date, 'lines': [], 'tags': {}})

    def prepareData(self):
        self.backups = {}
        for b in self.queue:
            self.backups[b['date']] = b

    def getTags(self, backup):
        struct = self.backups[backup]
        tags, lines = struct['tags'], struct['lines']
        if lines:
            for l in lines:
                match = re.search("\[(.*)\]: (.*)", l)
                if (match):
                    tag, value = match[1], match[2]
                    if tags.get(tag) is None:
                        tags[tag] = set()
                    tags[tag].add(value)
            for t in tags:
                tags[t] = sorted(tags[t])
            struct['lines'] = None
        return tags

    def addLine(self, text):
        if len(self.queue) != 0:
            self.queue[-1]['lines'].append(text)


def readLog():
    def lines():
        with open(args.logfile, "r", encoding="utf8") as fh:
            for line in fh:
                yield line

    with DuplicatiLogData() as logData:
        for line in lines():
            match = re.search("\[.*-StartingOperation\]", line)
            if match is not None:
                match = re.search("^(.*?) *-? *\[.*-StartingOperation\](.*)", line)
                logData.addBackup(match[1] + match[2])
            else:
                logData.addLine(line)

    return logData


def highlight_insert(text, line):
    try:
        # raise RuntimeError
        if not re.search('(Ex|In)cluding path due to filter: ', line):
            raise RuntimeError
        match = re.search('(.*(?:Ex|In)cluding path due to filter: )(.*)( => \()(.*)(\))', line)
        if not match:
            raise RuntimeError
        pre, path, mid, pattern, post = match[1], match[2], match[3], match[4], match[5]
        if match := re.fullmatch('\[(.*)\]', pattern):
            regex = match[1]
            regex = re.sub(r"^\.\*(/|\\\\)", "", regex)
        else:
            regex = pattern
            # regex = re.sub(r"^\*(/|\\(?=[^\\]))", "", regex)
            regex = re.sub(r"^\*(/|\\)", "", regex)
            regex = re.sub(r"\\", r"\\\\", regex)
            regex.replace("*", ".*")
            regex.replace("?", ".")
        # print(regex)
        match = re.search(regex, path, re.IGNORECASE)
        if not match:
            raise RuntimeError
        text.insert(END, pre)
        text.insert(END, path[:match.start()])
        text.insert(END, path[match.start():match.end()], "highlight")
        text.insert(END, path[match.end():])
        text.insert(END, mid)
        text.insert(END, pattern)
        text.insert(END, post)
    except:
        text.insert(END, line)


def isIgnored(text):
    for regex in cfg.get("ignore-exclude"):
        if regex.fullmatch(text):
            return True


def getInitfile():
    def checkPath(var, subdir):
        if var:
            val = os.environ.get(var)
            if val is None:
                return None
        else:
            val = ""
        path = val + subdir
        return path if os.path.isfile(path) else None

    return (
        checkPath("XDG_CONFIG_HOME", "/duplicati-log-viewer/config.yaml")
        or checkPath("HOME", "/.config/duplicati-log-viewer/config.yaml")
        or checkPath("USERPROFILE", "/.config/duplicati-log-viewer/config.yaml")
        or checkPath(None, os.path.dirname(os.path.realpath(__file__)) + "/.duplicati-log-viewer.yaml")
    )


def loadCfg():
    global cfg
    ini = getInitfile()
    if ini:
        with open(ini, "r") as stream:
            cfg = yaml.safe_load(stream)
    else:
        cfg = {}
    new = []
    # automatically extend in regex '/' to '[/\\]' and '^/' to '[^/\\]'
    for regex in cfg.get("ignore-exclude") or []:
        regex = re.sub(r"(\^?)/", r"[\1/\\\\]", regex)
        regex = "".join(["Excluding path due to filter: ", regex, " => \(.*\)"])
        new.append(regex)
    cfg["ignore-exclude"] = [re.compile(e) for e in new]


main()
