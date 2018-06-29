import linecache
import os.path
import pdb
import runpy
import signal
import sys


LOG_PATH = 'log.txt'


from collections import namedtuple
_Frame = namedtuple('_Frame', 'path line_no func_name line module')


class IntPdb(pdb.Pdb):
    def __init__(self, completekey='tab', stdin=None, stdout=None, skip=None):
        pdb.Pdb.__init__(self, completekey, stdin, stdout, skip)
        self.allow_kbdint = False
        signal.signal(signal.SIGINT, self.sigint_handler)

    def sigint_handler(self, signum, frame):
        if self.allow_kbdint:
            raise KeyboardInterrupt
        print >>self.stdout, "\nProgram interrupted. (Use 'cont' to resume)."
        self.set_step()
        self.set_trace(frame)

    def logging_sigint_handler(self, signum, frame):
        stack, i = self.get_stack(sys._getframe().f_back, None)
        #print >>self.stdout, "------\n", stack, "------\n"
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, 'w') as log:
                log.write('from collections import namedtuple\n')
                log.write('_Frame = namedtuple({!r}, {})\n'.format(
                    _Frame.__name__, _Frame._fields))
                log.write('log = []\n')

        with open(LOG_PATH, 'a') as log:
            log.write('log.append([\n')
            for frame, line_no in stack:
                code = frame.f_code
                path = code.co_filename
                func_name = code.co_name
                linecache.checkcache(path)
                line = linecache.getline(path, line_no, frame.f_globals)
                if '__module__' in frame.f_globals:
                    module = frame.f_globals['__module__']
                elif '__name__' in frame.f_globals:
                    module = frame.f_globals['__name__']
                else:
                    module = None
                # Remove any frames from debugging module.
                if module not in ['pdb', 'bdb', 'intpdb']:
                    logframe = _Frame(path, line_no, func_name, line.strip(),
                                      module)
                    log.write('            {!r},\n'.format(logframe))
            log.write('           ])\n')

    def _cmdloop(self):
        while True:
            try:
                # keyboard interrupts allow for an easy way to cancel
                # the current command, so allow them during interactive input
                self.allow_kbdint = True
                self.cmdloop()
                self.allow_kbdint = False
                break
            except KeyboardInterrupt:
                self.message('--KeyboardInterrupt--')

    def bp_commands(self, frame):
        """Call every command that was set for the current active breakpoint
        (if there is one).

        Returns True if the normal interaction function must be called,
        False otherwise."""
        # self.currentbp is set in bdb in Bdb.break_here if a breakpoint was
        # hit.
        if getattr(self, "currentbp", False) and \
                self.currentbp in self.commands:
            currentbp = self.currentbp
            self.currentbp = 0
            lastcmd_back = self.lastcmd
            self.setup(frame, None)
            for line in self.commands[currentbp]:
                self.onecmd(line)
            self.lastcmd = lastcmd_back
            if not self.commands_silent[currentbp]:
                self.print_stack_entry(self.stack[self.curindex])
            if self.commands_doprompt[currentbp]:
                self._cmdloop()
            self.forget()
            return
        return 1

    def setup(self, f, t):
        self.forget()
        self.stack, self.curindex = self.get_stack(f, t)
        self.curframe = self.stack[self.curindex][0]
        # The f_locals dictionary is updated from the actual frame
        # locals whenever the .f_locals accessor is called, so we
        # cache it here to ensure that modifications are not overwritten.
        self.curframe_locals = self.curframe.f_locals
        return self.execRcLines()

    # Can be executed earlier than 'setup' if desired
    def execRcLines(self):
        if not self.rcLines:
            return
        # local copy because of recursion
        rcLines = self.rcLines
        rcLines.reverse()
        # execute every line only once
        self.rcLines = []
        while rcLines:
            line = rcLines.pop().strip()
            if line and line[0] != '#':
                if self.onecmd(line):
                    # if onecmd returns True, the command wants to exit
                    # from the interaction, save leftover rc lines
                    # to execute before next interaction
                    self.rcLines += reversed(rcLines)
                    return True

    def interaction(self, frame, traceback):
        #self.setup(frame, traceback)
        if self.setup(frame, traceback):
            # no interaction desired at this time (happens if .pdbrc contains
            # a command like "continue")
            self.forget()
            return
        self.print_stack_entry(self.stack[self.curindex])
        self.cmdloop()
        self.forget()

    def tb_log(self):
        signal.signal(signal.SIGINT, self.logging_sigint_handler)
        self._set_stopinfo(None, None, -1)
        frame = sys._getframe().f_back
        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        self.onecmd('continue')
        sys.settrace(self.trace_dispatch)


# Simplified interface

def run(statement, globals=None, locals=None):
    IntPdb().run(statement, globals, locals)


def runeval(expression, globals=None, locals=None):
    return IntPdb().runeval(expression, globals, locals)


def runcall(*args, **kwds):
    return IntPdb().runcall(*args, **kwds)


def set_trace():
    IntPdb().set_trace(sys._getframe().f_back)


def tb_log():
    IntPdb().tb_log()


def usage():
    print 'usage: wrap_user.py -h'
    print('       wrap_user.py [-l LOG] (-c command | -m module-name | script)'
          ' [args]')
    exit()


if __name__ == '__main__':
    if sys.argv[1] == '-h':
        usage()

    if sys.argv[1] == '-l':
        if len(sys.argv) < 4:
            usage()
        LOG_PATH = sys.argv[2]
        sys.argv = sys.argv[:1] + sys.argv[3:]

    tb_log()
    __name__ = '__NOT_main__'

    if sys.argv[1] == '-c':
        if len(sys.argv) < 3:
            usage()
        command = sys.argv[2]
        sys.argv = ['-c'] + sys.argv[3:]
        exec command in {'__doc__': None, '__name__': '__main__',
                         '__package__': None}
    elif sys.argv[1] == '-m':
        if len(sys.argv) < 3:
            usage()
        module = sys.argv[2]
        # NB. run_module will overwrite the first value in sys.argv
        sys.argv = [''] + sys.argv[3:]
        runpy.run_module(module, alter_sys=True, run_name='__main__')
    else:
        path = sys.argv[1]
        # NB. run_path will overwrite the first value in sys.argv
        sys.argv = sys.argv[1:]
        runpy.run_path(path, run_name='__main__')
