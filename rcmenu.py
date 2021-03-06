import os
import sys
import fcntl
import shlex
import signal
import tkinter
import subprocess
import collections


Entry = collections.namedtuple('Entry', 'name,command,close')


class RCMenu:

    def __init__(self, entries):
        self.entries = entries[:]
        self.count = len(entries)
        root = tkinter.Tk(className='rcmenu')
        self.root = root
        root.title('rcmenu')
        root.bind('<Escape>', self.close)
        root.bind('<Up>', self.up)
        root.bind('<Down>', self.down)
        root.bind('<Return>', self.submit)
        root.bind('<space>', self.submit)
        listbox = tkinter.Listbox(
            root,
            borderwidth=10,
            relief=tkinter.FLAT,
            highlightthickness=0,
            background='#eceff1',
            foreground='#37474f',
            selectbackground='#1e88e5',
            selectforeground='#bbdefb',
            font=('monospace', 40, 'bold'),
            height=self.count,
            width=0,
        )
        self.listbox = listbox
        listbox.pack()
        for entry in self.entries:
            listbox.insert(tkinter.END, entry.name)
        self.current = 0
        self.select_current()

    def run(self):
        self.root.mainloop()

    def select_current(self):
        self.listbox.selection_set(self.current)

    def unselect_current(self):
        self.listbox.selection_clear(self.current)

    def submit(self, event=None):
        entry = self.entries[self.current]
        subprocess.Popen(entry.command)
        if entry.close:
            self.close()

    def up(self, event=None):
        self.unselect_current()
        self.current -= 1
        if self.current < 0:
            self.current = self.count - 1
        self.select_current()

    def down(self, event=None):
        self.unselect_current()
        self.current += 1
        if self.current >= self.count:
            self.current = 0
        self.select_current()

    def close(self, event=None):
        self.root.destroy()


class ConfigParserError(Exception):

    pass


class ConfigParser:

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.expanduser('~'), '.rcmenu')
        self.config_path = os.path.abspath(config_path)

    def parse(self):
        if not os.path.isfile(self.config_path):
            raise ConfigParserError(f'{self.config_path} not found')
        entries = []
        with open(self.config_path) as config_file_obj:
            for line in config_file_obj.readlines():
                line = line.strip()
                if not line:
                    continue
                name, _, command = line.partition('|')
                name = name.strip()
                command = command.strip()
                if command.startswith('^'):
                    command = command.lstrip('^ ')
                    close = True
                else:
                    close = False
                if not name or not command:
                    raise ConfigParserError(f'invalid entry: {line}')
                command = tuple(shlex.split(command))
                entries.append(Entry(name, command, close))
        return entries


if __name__ == '__main__':
    try:
        entries = ConfigParser().parse()
    except ConfigParserError as exc:
        sys.exit(str(exc))
    run_dir = os.getenv('XDG_RUNTIME_DIR')
    if run_dir is None:
        sys.exit('env variable XDG_RUNTIME_DIR not set')
    pid_file_path = os.path.join(run_dir, 'rcmenu.pid')
    mode = 'r+' if os.path.exists(pid_file_path) else 'w'
    pid_file_obj = open(pid_file_path, mode)
    try:
        fcntl.lockf(pid_file_obj, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        pid = int(pid_file_obj.read())
        print(f'RCMenu already started (pid {pid}) -- killing')
        os.kill(pid, signal.SIGKILL)
        pid_file_obj.close()
        os.unlink(pid_file_path)
        sys.exit()
    pid = os.getpid()
    pid_file_obj.seek(0)
    pid_file_obj.truncate()
    pid_file_obj.write(str(pid))
    pid_file_obj.flush()
    RCMenu(entries).run()
    pid_file_obj.close()
    os.unlink(pid_file_path)
