import subprocess
import shlex
import re


class _File(object):
    DELEGATE_METHODS = ['close', 'fileno', 'flush', 'isatty', 'mode', 'name', 'newlines', 'next', 'read', 'readinto', 'readline', 'readlines', 'seek', 'tell', 'truncate', 'write', 'writelines', 'xreadlines']

    def __new__(cls, f, *args, **kwargs):
        if f is None:
            return None
        elif f is Command.PIPE:
            return Command.PIPE
        else:
            return object.__new__(cls, f, *args, **kwargs)

    def __init__(self, f, *args, **kwargs):
        self._close = True
        try:
            self._file = open(f, *args, **kwargs)
        except TypeError:
            self._file = f
            self._close = False

        self._delegate()

    def _delegate(self):
        for method_name in _File.DELEGATE_METHODS:
            self.__setattr__(method_name, getattr(self._file, method_name))

    def close_if_needed(self):
        if self._close:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_if_needed()

class Command(object):
    ATTRIBUTES = ['command', 'variables', 'ATTRIBUTES', 'PIPE']
    PIPE = subprocess.PIPE

    def __init__(self, command, **variables):
        try:
            self.command = shlex.split(command)
        except AttributeError:
            self.command = list(command)

        self.variables = {}

        for name, value in variables.iteritems():
            self.__setattr__(name, value)

        self.ATTRIBUTES = Command.ATTRIBUTES + self.__dict__.items()

        self.parsed_command = lambda command: [command.parse(argument) for argument in command.command]

    def _setattr(self, name, value):
        object.__setattr__(self, name, value)

    def __setattr__(self, name, value):
        if name in self.ATTRIBUTES:
            self._setattr(name, value)
        else:
            self.variables[name] = value

    def __getattr__(self, name):
        try:
            attr = self.variables[name]
        except KeyError:
            raise AttributeError()

        if callable(attr): attr = attr(self)

        try:
            return self.parse(attr)
        except TypeError:
            return attr

    def parse(self, string):
        for pattern in set(re.findall('\{.+?\}', string)):
            try:
                value = str(self.__getattr__(pattern[1:-1]))
            except AttributeError:
                continue
            else:
                string = string.replace(pattern, value)

        return string

    def append(self, other):
        try:
            self.command = self.command + other
        except TypeError:
            self.command = self.command + Command(other)

    def prepend(self, other):
        try:
            self.command = other + self.command
        except TypeError:
            self.command = Command(other) + self.command

    def __add__(self, other):
        try:
            result = Command(self.command + other.command, dict(self.variables, **other.variables))
        except AttributeError:
            result = self + Command(other)

        return result

    def run(self, input=None, output=self.PIPE, echo=False, dry_run=False):
        c = self.parsed_command
        if echo:
            print ' '.join(c)

        input_file = _File(input)
        output_file = _File(output)

        if not dry_run:
            p = subprocess.Popen(c, stdin=input_file, stdout=output_file)
            result = p.communicate()
            if p.returncode!=0:
                raise subprocess.CalledProcessError(p.returncode, ' '.join(c))

        else:
            result = (None, None)

        try:
            input_file.close_if_needed()
        except AttributeError:
            pass

        try:
            output_file.close_if_needed()
        except AttributeError:
            pass

        return result
