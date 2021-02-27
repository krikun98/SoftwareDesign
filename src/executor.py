from abc import abstractmethod
from .clparser import CmdIR
import io
import os
import sys
import subprocess


class CmdExecutor(object):
    """
    An abstract class for a command execution

    Args:
        cmd (CmdIR): the command which need to be executed

    Attributes:
        name (str): the command name
        args (list): the command args

    Raises:
        RuntimeError: if there is some error

        FileNotFoundError: for `cat` and `wc` command only,
            if no such file in directory

    """

    def __init__(self, cmd: CmdIR) -> None:
        self.name = cmd.name
        self.args = cmd.args

    @abstractmethod
    def execute(self, istream: io.StringIO) -> io.StringIO:
        """
        Execute the command

        Args:
            istream (io.StringIO): input stream

        Returns:
            io.StringIO: output stream with the result of execution

        """

        pass


class EchoExecutor(CmdExecutor):
    """
    `echo`: print given arguments

    """

    def __init__(self, cmd: CmdIR) -> None:
        super().__init__(cmd)

    def execute(self, istream: io.StringIO) -> io.StringIO:
        ostream = io.StringIO()

        try:
            ostream.write(self.args)
        except Exception:
            raise RuntimeError('echo: check your arguments')

        return ostream


class PwdExecutor(CmdExecutor):
    """
    `pwd`: print current directory
    args isn't required

    """

    def __init__(self, cmd: CmdIR) -> None:
        super().__init__(cmd)

    def execute(self, istream: io.StringIO) -> io.StringIO:
        ostream = io.StringIO()

        try:
            ostream.write(os.getcwd())
        except Exception:
            raise RuntimeError('pwd: some bads with pwd')

        return ostream


class CatExecutor(CmdExecutor):
    """
    `cat FILE`: print the FILE content
    can be used only with one file

    """

    def __init__(self, cmd: CmdIR) -> None:
        super().__init__(cmd)

    @staticmethod
    def _catFromFile(filename: str) -> str:
        contet: str = ''

        try:
            with open(filename, 'r') as f:
                contet = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f'cat: {filename}: no such file')

        return contet

    @staticmethod
    def _catFromConsole() -> str:
        result: str = ''
        for line in sys.stdin:
            result += line
        return result

    def execute(self, istream: io.StringIO) -> io.StringIO:
        ostream = io.StringIO()
        cntArgs: int = len(self.args.split())
        realInput: str = ''

        if cntArgs == 1:
            filename: str = self.args
            realInput = self._catFromFile(filename)
        elif cntArgs == 0:
            istreamText: str = istream.getvalue()
            if not istreamText:
                realInput = self._catFromConsole().rstrip()
            else:
                realInput = istreamText
        else:
            raise RuntimeError(
                f'cat: cat supports only one file, but given {cntArgs}')

        ostream.write(realInput)

        return ostream


class WcExecutor(CmdExecutor):
    """
    `wc FILE`: print a count of line,
    count of word, count of char in the FILE

    """

    def __init__(self, cmd: CmdIR) -> None:
        super().__init__(cmd)

    @staticmethod
    def _wcFromFile(filename: str) -> list[str]:
        content: list[str]

        try:
            with open(filename, 'r') as f:
                content = f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f'wc: {filename}: no such file')

        return content

    @staticmethod
    def _wcFromConsole() -> list[str]:
        result: list[str] = []
        for line in sys.stdin:
            result.append(line)
        return result

    @staticmethod
    def _wcFromIStream(istream: io.StringIO) -> list[str]:
        splited = istream.getvalue().split('\n')
        return [s + '\n' for s in splited][:-1]

    def execute(self, istream: io.StringIO) -> io.StringIO:
        ostream = io.StringIO()
        cntArgs: int = len(self.args.split())
        realInput: list[str] = []
        filename: str = self.args

        if cntArgs == 1:
            realInput = self._wcFromFile(filename)
        elif cntArgs == 0:
            inputText: str = istream.getvalue()
            if inputText:
                realInput = self._wcFromIStream(istream)
            else:
                realInput = self._wcFromConsole()
        else:
            raise RuntimeError(
                f'wc: wc supports only one file, but given {cntArgs}')

        lineCnt, wordCnt, charCnt = 0, 0, 0

        for line in realInput:
            lineCnt += 1
            wordCnt += len(line.split())
            charCnt += len(line)

        ostream.write(f'{lineCnt} {wordCnt} {charCnt} {filename}')
        return ostream


class ExternalExecutor(CmdExecutor):
    """
    Run some external process

    """

    def __init__(self, cmd: CmdIR) -> None:
        super().__init__(cmd)

    def execute(self, istream: io.StringIO) -> io.StringIO:
        ostream = io.StringIO()

        externalProcess = subprocess.Popen([self.name, self.args],
                                           stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)

        encodedInput = bytes(istream.getvalue().encode('utf-8'))

        externalProcess.stdin.write(encodedInput)
        result = externalProcess.communicate()[0].decode('utf-8')
        externalProcess.stdin.close()

        ostream.write(result)

        return ostream


def processCmd(cmd: CmdIR) -> CmdExecutor:
    """
    Map the command to its executor

    Args:
        cmd (CmdIR): the command

    Returns:
        CmdExecutor: the executor for the command

    """

    name: str = cmd.name

    if name == 'echo':
        return EchoExecutor(cmd)

    if name == 'pwd':
        return PwdExecutor(cmd)

    if name == 'cat':
        return CatExecutor(cmd)

    if name == 'wc':
        return WcExecutor(cmd)

    return ExternalExecutor(cmd)


def runCommand(cmds: list[CmdIR]) -> io.StringIO:
    """
    Execute the command

    Args:
        cmds (list[CmdIR]): commands

    Returns:
        io.StringIO: the output stream with the result of the command

    """

    result = io.StringIO()
    cmdsExec: list[CmdExecutor] = list(map(processCmd, cmds))

    for cmd in cmdsExec:
        try:
            result = cmd.execute(result)
        except Exception as e:
            raise e

    result.write('\n')

    return result
