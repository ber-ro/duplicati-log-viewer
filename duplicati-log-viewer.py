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
import re
import sys


def main():
    createGui()
    readLog()
    setFocus()
    root.mainloop()


def createGui():
    global root, tree
    root = Tk()
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
        if len(self.queue) > 5:
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
        with open(sys.argv[1], "r", encoding="utf8") as fh:
            for line in fh:
                yield line

    reStarting = "^(.*) \[Information-Duplicati.Library.Main.Controller-StartingOperation\]"

    with DuplicatiLogTree(tree) as logTree:
        for line in lines():
            match = re.search(reStarting, line)
            if match is not None:
                logTree.addBackup(match[1])
                continue

            match = re.search("\[([^\]]*)\]: (.*)", line)
            if (match is not None):
                logTree.addLine(match[1], match[2])


main()
