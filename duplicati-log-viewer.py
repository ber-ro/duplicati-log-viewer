# Structure Duplicati log file as tree view
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
    createGui()
    readLog()
    setFocus()
    t1 = time.process_time()
    print("Start-up time:", t1 - t0, "seconds")
    root.mainloop()


def createGui():
    global root, tree
    root = Tk()
    root.title(os.path.basename(os.path.realpath(__file__)))
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    tree = ttk.Treeview(root, height=40, show="tree")
    tree.column("#0", width=900, minwidth=2000)  # minwidth: horizontal scroll
    tree.grid(column=0, row=0, sticky="nsew")
    tree.bind('<Control-c>', copy)

    tree_yscroll = ttk.Scrollbar(root, orient=VERTICAL, command=tree.yview)
    tree_xscroll = ttk.Scrollbar(root, orient=HORIZONTAL, command=tree.xview)
    tree_yscroll.grid(row=0, column=1, sticky="ns")
    tree_xscroll.grid(row=1, column=0, sticky="ew")
    tree.configure(yscrollcommand=tree_yscroll.set,
                   xscrollcommand=tree_xscroll.set)


def setFocus():
    tree.focus_set()
    children = tree.get_children()
    if children:
        tree.focus(children[-1])
        tree.selection_set(children[-1])


def copy(event):
    values = [tree.item(i, 'text') for i in tree.selection()]
    root.clipboard_clear()
    root.clipboard_append("\n".join(values))


class DuplicatiLogTree:
    def __init__(self, tree):
        self.tree = tree
        self.queue = deque()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.fillTree()

    def addBackup(self, date):
        max = cfg.get("show-logs-number") or 10
        if max != 0 and len(self.queue) >= max:
            self.queue.popleft()
        self.queue.append({'date': date, 'lines': {}})

    def fillTree(self):
        for backup in self.queue:
            parent = self.tree.insert("", 'end', text=backup['date'])
            for tag in sorted(backup['lines']):
                parent2 = self.tree.insert(parent, 'end', text=tag)
                for f in sorted(backup['lines'][tag]):
                    self.tree.insert(parent2, 'end', text=f)

    def addLine(self, tag, text):
        if len(self.queue) == 0:
            return
        lines = self.queue[-1]['lines']
        if lines.get(tag) is None:
            lines[tag] = set()
        lines[tag].add(text)


def readLog():
    def lines():
        with open(args.logfile, "r", encoding="utf8") as fh:
            for line in fh:
                yield line

    with DuplicatiLogTree(tree) as logTree:
        for line in lines():
            match = re.search("\[.*-StartingOperation\]", line)
            if match is not None:
                match = re.search("^(.*?) *-? *\[.*-StartingOperation\](.*)", line)
                logTree.addBackup(match[1] + match[2])
                continue

            match = re.search("\[(.*)\]: (.*)", line)
            if (match is not None and not isIgnored(match[2])):
                logTree.addLine(match[1], match[2])


def isIgnored(text):
    for regex in cfg.get("ignore-exclude"):
        if re.fullmatch(regex, text):
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
    cfg["ignore-exclude"] = new


main()
