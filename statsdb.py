'''
@author: The Junky

'''

from BotUtilities import *
from SubspaceBot import *
import TimerManager
from Amysql import *


class Bot(BotInterface):
    def __init__(self, bot, md):
        BotInterface.__init__(self, bot, md)
        bot.registerModuleInfo(
            __name__,
            "stats",
            "The Junky",
            "Stats Retrieval Module",
            ".01"
        )
        self._db = Amysql(self.logger)
        self._db.setDbCredentialsFromFile(
            self.module_path + R"/statsdb.conf", "db")
        self._db.start()
        # self.clist = [COMMAND_TYPE_PUBLIC, COMMAND_TYPE_TEAM,
        #   COMMAND_TYPE_FREQ, COMMAND_TYPE_PRIVATE, COMMAND_TYPE_CHAT]
        self.clist = [COMMAND_TYPE_PRIVATE]
        # self._sql_command_id = bot.registerCommand(
        #   '!sql', None, 9, self.clist, "web", "[query]", 'sql it zz')
        # self._sqlnl_command_id = bot.registerCommand(
        #   '!sqlnl', None, 9, self.clist, "web", "[query]", 'sql it zz')
        self._last_jp = bot.registerCommand(
            '!jackpots', None, 0, self.clist, "Stats", "", 'last jackpots won')
        self._recs = bot.registerCommand(
            '!recs', None, 0, self.clist, "Stats", "[reset id]", 'top ratios')
        self._points = bot.registerCommand(
            '!points', None, 0, self.clist, "Stats", "[reset id]",
            'Top points')
        self._squads = bot.registerCommand(
            '!squads', None, 0, self.clist, "Stats", "[reset id]",
            'top squads')
        self._resets = bot.registerCommand(
            '!resets', None, 0, self.clist, "Stats", "", 'recentreset ids')
        self.level = logging.DEBUG
        self.timer_man = TimerManager.TimerManager()
        self.timer_man.set(.01, 1)
        self.timer_man.set(300, 2)
        self.chat = bot.addChat("st4ff")
        self.cache = {
            # !cmd: (Cached_result, time)
            "!jackpots": (None, 0, "jackpots.txt"),
            "!recs": (None, 0, "recs.txt"),
            "!points": (None, 0, "points.txt"),
            "!squads": (None, 0, "squads.txt")
        }

        formatter = logging.Formatter('%(message)s')
        handler = loggingRemoteHandler(logging.DEBUG, bot, "Ratio")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def getMessageTuple(self, event):
        """
            this data will be used later in pretty printer
            when the result is to be printed back to ss
        """
        if event.command_type == MESSAGE_TYPE_PRIVATE:
            target = event.pname
            mtype = event.command_type
        elif event.command_type == MESSAGE_TYPE_REMOTE:
            target = event.pname
            mtype = MESSAGE_TYPE_PRIVATE
        elif event.command_type == MESSAGE_TYPE_FREQ:
            target = event.player.freq
            mtype = event.command_type
        elif event.command_type == MESSAGE_TYPE_CHAT:
            target = event.chat_no
            mtype = event.command_type
        else:
            target = None
            mtype = event.command_type

        return (mtype, target, event.command.name)

    def getResetId(self, event):
        if len(event.arguments) > 0:
            try:
                r = int(event.arguments[0])
                if r < 0:
                    return None
                return r
            except ValueError:
                return None
            return None

    def HandleEvents(self, ssbot, event):

        if event.type == EVENT_COMMAND:
            # if event.command.id in [
            #         self._sql_command_id, self._sqlnl_command_id]:
            #     automatically addlimit or not
            #     if event.command.id == self._sql_command_id:
            #         limit = " limit 100"
            #     else:
            #         limit = ""
            #     mt = self.getMessageTuple(event)
            #     db = self._db
            #     db.query(event.arguments_after[0] + limit, None, mt)
            if event.command.id == self._last_jp:
                q = """SELECT
                        id,
                        IF(
                            jackpot > 1000000,
                            concat(round(jackpot / 1000000, 1), "mil"),
                            concat(round(jackpot/1000, 1), "K")
                        ) AS jp,
                        IF(
                            winning_freq < 100,
                            winning_freq,
                            "Priv"
                        ) AS freq,
                        timediff(end_time, start_time) AS runtime
                    FROM flag_games
                    WHERE to_days(now()) - to_days(end_time) < 1
                    ORDER BY jackpot DESC
                    LIMIT 5"""

                mt = self.getMessageTuple(event)

                db = self._db
                db.query(q, None, mt)
            elif event.command.id == self._points:
                reset_id = self.getResetId(event)
                if reset_id:
                    ps = " pub_stats_arch"
                    rs = " and reset_id=" + str(reset_id) + " "
                else:
                    ps = " pub_stats"
                    rs = ""
                q = """SELECT
                        player.name AS pname,
                        squad.name AS squad,
                        flag_points + kill_points AS points
                    FROM %s ps, player, squad
                    WHERE
                        ps.player_id = player.id
                        AND ps.squad_id = squad.id %s
                    ORDER BY points DESC
                    LIMIT 10""" % (ps, rs)
                mt = self.getMessageTuple(event)

                db = self._db
                db.query(q, None, mt)

            elif event.command.id == self._resets:
                q = "select * from reset order by id desc limit 10"

                mt = self.getMessageTuple(event)

                db = self._db
                db.query(q, None, mt)
            elif event.command.id == self._recs:
                reset_id = self.getResetId(event)
                if reset_id:
                    ps = " pub_stats_arch"
                    rs = " and reset_id=" + str(reset_id) + " "
                else:
                    ps = " pub_stats"
                    rs = ""
                q = """SELECT
                        a.player_id,
                        b.name,
                        GetRating(a.Wins, a.Losses) AS `value`,
                        a.Wins,
                        a.Losses
                    FROM %s a, player b
                    WHERE
                        a.Wins > 50
                        AND a.player_id = b.id %s
                        AND STRCMP(LEFT(b.name, 4), "Bot-")
                        AND STRCMP(LEFT(b.name, 7), "DevBot-")
                    ORDER BY value DESC
                    LIMIT 5""" % (ps, rs)

                mt = self.getMessageTuple(event)

                db = self._db
                db.query(q, None, mt)
            elif event.command.id == self._squads:
                reset_id = self.getResetId(event)
                if reset_id:
                    ps = " pub_stats_arch"
                    rs = " and reset_id=" + str(reset_id) + " "
                else:
                    ps = " pub_stats"
                    rs = ""
                q = """SELECT
                    s.name AS squadname,
                    GetTopAvg(0, s.id, 10) AS Avg,
                    count(squad_id) AS members
                    FROM squad s, %s ps
                    WHERE
                        squad_id <> 1
                        AND s.id = ps.squad_id %s
                    GROUP BY squad_id HAVING members >= 10
                    ORDER BY Avg DESC
                    LIMIT 10""" % (ps, rs)
                mt = self.getMessageTuple(event)

                db = self._db
                db.query(q, None, mt)
        elif event.type == EVENT_TICK:
            timer_expired = self.timer_man.getExpired()  # a timer expired
            # self.logger.info("tick")
            if timer_expired:
                # self.logger.info("timer expired")

                if timer_expired.data == 1:
                    # self.logger.info("1")
                    r = self._db.getResults()
                    if r:  # most of the time this will be None so check first
                        self.HandleResults(ssbot, event, r)
                    self.timer_man.set(1, 1)  # set it to check again in a sec
                elif timer_expired.data == 2:
                    # self.logger.info("2")
                    self._db.ping()
                    self.timer_man.set(300, 2)

    def HtmlResultWriter(self, result, filename):
        """
        this function will print any result nicely on screen with
        proper formatting
        """
        f = open(filename, 'w')

        if self.rows is None or len(self.rows) == 0:
            pass
        else:
            if not self.description:
                f.write("#### NO RESULTS ###")
            else:
                names = []
                lengths = []

                for dd in self.description:  # iterate over description
                    names.append(dd[0])
                    # in case name is bigger then max len of data
                    lengths.append(len(dd[0]))

                for row in self.rows:  # get the max length of each column
                    for i in range(len(row)):
                        lengths[i] = max(lengths[i], len(str(row[i])))
                tb = "-" * (sum(map(int, lengths)) + (len(lengths) * 3) + 1)
                fm = "|"
                for col in lengths:  # make the format string
                    fm += " %" + str(col) + "s |"
                f.write(tb)
                f.write((fm % tuple(names)))
                f.write(tb)

                for row in self.rows:  # output the rows
                    f.write((fm % row))
                f.write(tb)
                f.close()

    def HandleResults(self, ssbot, event, r):
        # message like connection error or connected
        if r.getType() == AElement.TYPE_MESSAGE:
            self.logger.info(r.message)
        else:
            # if r.query.data[2] in self.cache:
            #     self.cache[r.query.data[2]] = (
            #       copy.copy(r), get_tick_count_hs())
            r.GenericResultPrettyPrinter(
                ssbot, r.query.data[0], r.query.data[1])

    def Cleanup(self):
        self._db.CleanUp()

# bot runs in this if not run by master u can ignore this
if __name__ == '__main__':
    botMain(Bot, False, True, "-")
