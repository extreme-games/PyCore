'''
Masterbot for cycad's python core written by The Junky<thejunky@gmail.com>
@author: The Junky
'''

import os
import sys
import logging
import traceback
import math
import threading
from collections import deque

from SubspaceBot import SubspaceBot
from SubspaceBot import MESSAGE_TYPE_PUBLIC, MESSAGE_TYPE_TEAM, \
    MESSAGE_TYPE_FREQ, MESSAGE_TYPE_PRIVATE
from SubspaceBot import MESSAGE_TYPE_REMOTE, MESSAGE_TYPE_CHAT
from SubspaceBot import SOUND_NONE, Player


class ModuleData():
    """
    Added moduledata to facilitate adding features to modules in the
    future without breaking the interface
    """
    def __init__(self, module_name, module, param, inifile, args, logger):
        self.module_name = module_name
        self.module = module
        self.param = param
        self.inifile = inifile
        self.logger = logger
        self.module_path = os.path.dirname(self.module.__file__)
        self.args = args


class BotInterface:
    def __init__(self, bot, md):
        self.md = md
        # param defined in config, could be any string
        self.param = md.param
        self.inifile = md.inifile

        # logging module allows modules log to !log,console,and file
        self.logger = md.logger

        # when modules are dynamicly loaded
        # i dont think the rest of the file is easy/possible?
        # to add to the current context, even if it was possible
        # i assume it will cause some sort of name Mangling
        # i assume we can get all the variables we need if
        # i pass the module i get from __import__ to the botclass
        # so if u need you specific Playerinfo for example u
        # can get to it by doing module.playerinfo
        self.module_name = md.module_name
        self.module = md.module
        self.module_path = md.module_path
        self.args = md.args  # any arguments passed by !sb this is a string
        return None

    def HandleEvents(self, ssbot, event):
        msg = (
            "BotInterface Handle Events, %s bot has not overridden this"
            " function"
        )
        self.logger.error(msg % self.name)
        return None

    def Cleanup(self):
        pass


def LogException(logger):
    logger.error(sys.exc_info())
    formatted_lines = traceback.format_exc().splitlines()
    for l in formatted_lines:
        logger.error(l)


# # this looks like a much cleaner way to reload modules but i dont think
# # it works right.
# def LoadModule(name):
#     if name in sys.modules:
#         module = sys.modules[name]
#         reload(module)
#     else:
#         module = __import__( name,fromlist=["*"])
#     return module

# this is fugly and might cause problems when the module is loaded multiple
# times but should work for development at least
def LoadModule(name):
    # if module is already loaded
    if name in sys.modules:
        # unload module
        del sys.modules[name]
    # reload module
    module = __import__(name, globals=globals(), locals=locals(),
                        fromlist=["*"])
    # module = importlib.import_module(name)
    return module


def LoadBot(ssbot, modulename, param, inifile, args, logger):
    bot = None
    try:
        module = LoadModule(modulename)
        if (issubclass(module.Bot, BotInterface)):
            md = ModuleData(modulename, module, param, inifile, args, logger)
            bot = module.Bot(ssbot, md)
        else:
            msg = (
                "%s.Bot() is not a subclass of BotInterface, "
                "and can't be loaded"
            )
            logger.error(msg % modulename)
            bot = None
    except:
            msg = "Trying to instantiate %s caused Exception"
            logger.error(msg % modulename)
            LogException(logger)
            bot = None
    finally:
        return bot


def botMain(Bot, debug=False, isMaster=False, arena="#python"):
    from Credentials import botowner, botname, botpassword
    try:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # set a format
        str_format = '%(asctime)s:%(name)s:%(levelname)s:%(message)s'
        formatter = logging.Formatter(str_format)

        # define a Handler which writes INFO messages or higher
        # to the sys.stderr
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        # tell the handler to use this format
        console.setFormatter(formatter)
        # add the handler to the mainloop logger
        logger.addHandler(console)

        filehandler = logging.FileHandler(
            os.getcwd() + R"/" + __name__ + ".log", mode='a')
        filehandler.setLevel(logging.ERROR)
        filehandler.setFormatter(formatter)
        logger.addHandler(filehandler)

        ssbot = SubspaceBot(
            debug, isMaster, None, logging.getLogger(__name__ + ".Core"))
        ssbot.setBotInfo(__name__, "TestBoT", botowner)

        # get the module object for the current file...
        module = sys.modules[globals()['__name__']]
        md = ModuleData("TesttBot", module, "None", "test.ini", "",
                        logging.getLogger(__name__))
        bot = Bot(ssbot, md)

        ssbot.connect_to_server(
            '66.36.247.83', 7900, botname, botpassword, arena)

        while ssbot.isConnected():
            event = ssbot.wait_for_event()
            bot.HandleEvents(ssbot, event)
    except Exception as e:
        LogException(logger)
        raise e
    finally:
        bot.Cleanup()
        logger.critical("Testbot shutting down")
        filehandler.close()


def Pixels_To_SS_Coords(x, y):
    try:
        ch = "ABCDEFGHIJKLMNOPQRSTU"
        x1 = int(math.floor((x * 20) / 16384))
        y1 = ((y * 20) / 16384) + 1
        return ch[x1] + str(y1)
    except:
        return "InvalidCoord?"


def Tiles_To_SS_Coords(x, y):
    return Pixels_To_SS_Coords(x << 4, y << 4)


def Pixels_To_SS_Area(x, y):
    try:
        f = 3277.6
        xc = ["FarLeft", "Left", "Center", "Right", "FarRight"]
        yc = ["FarUp-", "Up-", "", "Down-", "FarDown-"]
        xi = int(math.floor(x / f))
        yi = int(math.floor(y / f))
        return yc[yi]+xc[xi]
    except:
        return "InvalidCoord?"


def Tiles_To_SS_Area(x, y):
    return Pixels_To_SS_Area(x << 4, y << 4)


class SSmessengerException(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class SSmessenger():
    """
    This class is used  if you want to use differing methods to print/message
    in Subspace. for example Database results can be printed to
    team/freq/pub/chat/remote
    supports
        MESSAGE_TYPE_PUBLIC,
        MESSAGE_TYPE_PRIVATE,MESSAGE_TYPE_REMOTE (target must be a name)
        MESSAGE_TYPE_TEAM,
        MESSAGE_TYPE_FREQ (target must be an freq)
        MESSAGE_TYPE_CHAT (target must be a chat channel)

        for arena or zone or *bot messages use MESSAGE_TYPE_PUBLIC with
        the appropriate prefix

        throws SSmessengerException on error
    """
    def __init__(self, ssbot, mtype, target=None, prefix=""):
        self.ssbot = ssbot
        self.func = None
        self.target = None
        self.prefix = prefix
        if mtype == MESSAGE_TYPE_PUBLIC:
            self.func = self.__pub
        elif mtype == MESSAGE_TYPE_PRIVATE:
            if isinstance(target, str):
                self.player = ssbot.findPlayerByName(target)
                if not self.player:
                    raise SSmessengerException("Player NotFound")
            elif isinstance(Player, target):
                self.player = target
            else:
                raise SSmessengerException((
                    "MessageType private/remote but target isn't "
                    "a string/player"))
            self.func = self.__priv
        elif mtype == MESSAGE_TYPE_REMOTE:
            if isinstance(target, str):
                self.func = self.__rmt
                self.playername = target
            else:
                raise SSmessengerException(
                    "MessageType remote but target is'nt a string")
        elif mtype == MESSAGE_TYPE_TEAM:
            self.func = self.__team
        elif mtype == MESSAGE_TYPE_FREQ:
            if isinstance(target, int):
                raise SSmessengerException(
                    "MessageType freq but target is'nt a freq")
            self.func = self.__freq
            self.freq = target
        elif mtype == MESSAGE_TYPE_CHAT:
            if isinstance(target, int):
                raise SSmessengerException(
                    "MessageType chat but target is'nt a channel")
            self.func = self.__chat
            self.chat = ";"+str(target)+";"
        else:
            raise SSmessengerException("MessageType not supported")

    def __pub(self, message, sound=SOUND_NONE):
        self.ssbot.sendPublicMessage(message, sound)

    def __priv(self, message, sound=SOUND_NONE):
        self.ssbot.sendPrivateMessage(self.player, message, sound)

    def __rmt(self, message, sound=SOUND_NONE):
        self.ssbot.sendRemoteMessage(self.playername, message, sound)

    def __team(self, message, sound=SOUND_NONE):
        self.ssbot.sendTeamMessage(message, sound)

    def __freq(self, message, sound=SOUND_NONE):
        self.ssbot.sendFreqMessage(self.freq, message, sound)

    def __chat(self, message, sound=SOUND_NONE):
        self.ssbot.sendChatMessage(self.chat + message, sound)

    def sendMessage(self, message, sound=SOUND_NONE):
        self.func(self.prefix + message, sound)


class loggingChatHandler(logging.Handler):
    """
    Logging module handler to spew entries to a specific chat
    """
    def __init__(self, level, ssbot, chat_no):
        logging.Handler.__init__(self, level)
        self.ssbot = ssbot
        self.chat = ";" + str(chat_no) + ";"

    def emit(self, record):
        self.ssbot.sendChatMessage(self.chat + self.format(record))


class loggingTeamHandler(logging.Handler):
    """
    Logging module handler to spew entries to a team chat
    """
    def __init__(self, level, ssbot):
        logging.Handler.__init__(self, level)
        self.ssbot = ssbot

    def emit(self, record):
        self.ssbot.sendTeamMessage(self.format(record))


class loggingPublicHandler(logging.Handler):
    """
    Logging module handler to spew entries to pub
    """
    def __init__(self, level, ssbot, prefix):
        logging.Handler.__init__(self, level)

        self.ssbot = ssbot

    def emit(self, record):
        self.ssbot.sendPublicMessage(self.format(record))


class loggingRemoteHandler(logging.Handler):
    """
    Logging module handler to spew entries to pub
    """
    def __init__(self, level, ssbot, name):
        logging.Handler.__init__(self, level)
        self.ssbot = ssbot
        self.name = name

    def emit(self, record):
        self.ssbot.sendRemoteMessage(self.name, self.format(record))


# the logging module allows u to add handlers for log messages
# for example maybe you want certain log entries to be added
# to an offsite server using httppost
# this is simple handler that i made to copy messages to a list
# so it can be spewed to ss without reading the logfile
# you are required to overide __init__ and emit for it to work
class ListHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET, max_recs=100):
        logging.Handler.__init__(self, level)
        self.list = []
        self.max_recs = max_recs
        self.max_slice = -1 * max_recs

    def emit(self, record):
        self.list.append(self.format(record))

    def LoadFromFile(self, filename):
        self.list = open(filename, 'r').readlines()[self.max_slice:]

    def RemoveOld(self):
        if len(self.list) > self.max_recs:
            self.list = self.list[self.max_slice:]

    def GetEntries(self):
        return self.list[self.max_slice:]

    def Clear(self):
        self.list = []


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class MasterQue():
    def __init__(self):
        self.__queue = deque()
        self.__lock = threading.Lock()

    def queue(self, event):
        self.__lock.acquire()
        self.__queue.append(event)
        self.__lock.release()

    def dequeue(self):
        q = None
        self.__lock.acquire()
        if len(self.__queue) > 0:
            q = self.__queue.pop()
        self.__lock.release()
        return q

    def size(self):
        return len(self.__queue)


class ShutDownException(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)
