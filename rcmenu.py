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
        self.entries = tuple(entries)
        self.root = root = tkinter.Tk(className='rcmenu')
        root.title('rcmenu')
        root.bind('<Escape>', self.close)
        root.bind('<Return>', self.submit)
        root.bind('<space>', self.submit)
        self.listbox = listbox = tkinter.Listbox(
            root,
            borderwidth=10,
            relief=tkinter.FLAT,
            highlightthickness=0,
            background='#eceff1',
            foreground='#37474f',
            selectbackground='#1e88e5',
            selectforeground='#bbdefb',
            font=('monospace', 40, 'bold'),
            height=len(self.entries),
            width=0,
        )
        listbox.pack()
        for entry in self.entries:
            listbox.insert(tkinter.END, entry.name)
        listbox.select_set(0)
        # listbox.focus()

    def run(self):
        self.root.mainloop()

    def submit(self, event=None):
        selected = self.listbox.curselection()[0]
        entry = self.entries[selected]
        subprocess.Popen(entry.command)
        if entry.close:
            self.close()

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
