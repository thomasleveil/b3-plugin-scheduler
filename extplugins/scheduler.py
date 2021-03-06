#
# Plugin for BigBrotherBot(B3) (www.bigbrotherbot.net)
# Copyright (C) 2008 courgette@bigbrotherbot.net
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA    02110-1301    USA
#----------------------------------------------------------------------------
#
# Description:
#
# This plugin makes B3 send rcon command to your serveur at predefined time.
#
# Changelog:
#
# 07/06/2009 - 0.1.0 - Courgette
# - initial release
#
# 07/06/2009 - 0.1.1 - Courgette
# - fix spelling
# - hours specified in config are now understood in the timezone setup in 
#     the main B3 config
#
# 27/04/2010 - 1.0 - Courgette
# - config error early detection with userfriendly message
# - can run bfbc2 commands
#
# 28/04/2010 - 1.1 - Courgette
# - fix issue with bfbc2 commands arguments
# - better handling of command errors
#
# 15/11/2010 - 1.2 - Courgette
# - now also work for Medal of Honor
# - changed config file syntax for bfbc2 and moh (old syntax still works)
# - can specify seconds as in the GNU cron syntax
#
# 30/05/2011 - 1.2.1 - Courgette
# - fix bug in hourly and daily tasks introduced in 1.2
#
# 21/08/2011 - 1.3 - Courgette
# - add restart tasks (which are executed when B3 starts/restarts
# - add enable_plugin and disable_plugin commands
#
# 06/10/2012 - 1.4 - Courgette
# - add support for BF3
# 08/10/2012 - 1.4.1 - Courgette
# - fix support for BF3
#
#
__version__ = '1.4.1'
__author__    = 'Courgette'

import threading, time
import b3, b3.plugin

FROSTBITE_GAMES = ('bfbc2', 'moh', 'bf3')

#--------------------------------------------------------------------------------------------------
class SchedulerPlugin(b3.plugin.Plugin):
    _tasks = None
    _tzOffset = 0
    _restart_tasks = set()
    
    def onLoadConfig(self):

        # remove eventual existing tasks
        if self._tasks:
            for t in self._tasks:
                t.cancel()
    
        # Get time_zone from main B3 config
        tzName = self.console.config.get('b3', 'time_zone').upper()
        self._tzOffset = b3.timezones.timezones[tzName]
    
        # load cron tasks from config
        self._tasks = []

        for taskconfig in self.config.get('restart'):
            try:
                task = RestartTask(self, taskconfig)
                self._tasks.append(task)
                self.info("restart task [%s] loaded" % task.name)
            except Exception, e:
                self.error(e)

        for taskconfig in self.config.get('cron'):
            try:
                task = CronTask(self, taskconfig)
                self._tasks.append(task)
                self.info("cron task [%s] loaded" % task.name)
            except Exception, e:
                self.error(e)
     
        # load hourly tasks from config
        for taskconfig in self.config.get('hourly'):
            try:
                task = HourlyTask(self, taskconfig)
                self._tasks.append(task)
                self.info("hourly task [%s] loaded" % task.name)
            except Exception, e:
                self.error(e)     
                
        # load daily tasks from config
        for taskconfig in self.config.get('daily'):
            try:
                task = DaylyTask(self, taskconfig)
                self._tasks.append(task)
                self.info("daily task [%s] loaded" % task.name)
            except Exception, e:
                self.error(e)
     

        self.debug("%d tasks scheduled"% len(self._tasks))

    def onStartup(self):
        # run RestartTasks
        for task in self._restart_tasks:
            try:
                task.runcommands()
            except Exception, e:
                self.error("could not run task %s : %s", (task.name, e))

 
    def onEvent(self, event):
        pass
        
    def _convertCronHourToUTC(self, hourcron):
        """
        works with "*", "*/4", "5" or 9
        """
        if hourcron.strip() == '*': 
            return hourcron
        if '/' in hourcron:
            h,divider = hourcron.split('/')
            if h.strip() == '*':
                return hourcron
            UTChour = (int(h.strip()) - self._tzOffset)%24
            return "%d/%s" % (UTChour, divider)
        else:
            UTChour = (int(hourcron.strip()) - self._tzOffset)%24
            tz = str(self._tzOffset)
            if not tz.startswith('-'):
                tz = '+' + tz
            self.debug("%s (UTC%s) -> %s UTC" % (hourcron, tz, UTChour))
            return UTChour
 
 
class TaskConfigError(Exception): pass

class Task(object):
    config = None
    plugin = None
    name = None
    
    def __init__(self, plugin, config):
        self.plugin = plugin
        self.config = config
        
        self.name = config.attrib['name']
        if not 'name' in config.attrib:
            self.plugin.info("attribute 'name' not found in task")
        else:
            self.name = config.attrib['name']

        self.plugin.debug("setting up %s [%s]" % (self.__class__.__name__, self.name) )

        num_commands_found = 0
        num_commands_found += self._init_rcon_commands()
        num_commands_found += self._init_enable_plugin_commands()
        num_commands_found += self._init_disable_plugin_commands()
        if num_commands_found == 0:
            raise TaskConfigError('no action found for task %s' % self.name)

    def _init_rcon_commands(self):
        if self.plugin.console.gameName in FROSTBITE_GAMES:
            frostbitecommands = self.config.findall("frostbite") + self.config.findall("bfbc2")
            for cmd in frostbitecommands:
                if not 'command' in cmd.attrib:
                    raise TaskConfigError('cannot find \'command\' attribute for a frostbite element')
                text = cmd.attrib['command']
                for arg in cmd.findall('arg'):
                    text += " %s" % arg.text
                self.plugin.debug("frostbite : %s" % text)
                return len(frostbitecommands)
        else:
            ## classical Q3 rcon command
            rconcommands = self.config.findall("rcon")
            for cmd in rconcommands:
                self.plugin.debug("rcon : %s" % cmd.text)
            return len(rconcommands)

    def _init_enable_plugin_commands(self):
        commands = self.config.findall("enable_plugin")
        for cmd in commands:
            if not 'plugin' in cmd.attrib:
                raise TaskConfigError('cannot find \'plugin\' attribute for a enable_plugin element')
            if not self.plugin.console.getPlugin(cmd.attrib['plugin']):
                raise TaskConfigError('cannot find plugin %s' % cmd.attrib['plugin'])
            self.plugin.debug("enable_plugin : %s" % cmd.attrib['plugin'])
        return len(commands)

    def _init_disable_plugin_commands(self):
        commands = self.config.findall("disable_plugin")
        for cmd in commands:
            if not 'plugin' in cmd.attrib:
                raise TaskConfigError('cannot find \'plugin\' attribute for a disable_plugin element')
            if not self.plugin.console.getPlugin(cmd.attrib['plugin']):
                raise TaskConfigError('cannot find plugin %s' % cmd.attrib['plugin'])
            self.plugin.debug("disable_plugin : %s" % cmd.attrib['plugin'])
        return len(commands)

    def runcommands(self):
        self.plugin.info("running scheduled commands from %s" % self.name)
        self._run_rcon_commands()
        self._run_enable_plugin_commands()
        self._run_disable_plugin_commands()

    def _run_rcon_commands(self):
        if self.plugin.console.gameName in FROSTBITE_GAMES:
            # send frostbite commands
            nodes = self.config.findall("frostbite") + self.config.findall("bfbc2")
            for frostbitenode in nodes:
                try:
                    commandName = frostbitenode.attrib['command']
                    cmdlist = [commandName]
                    for arg in frostbitenode.findall('arg'):
                        cmdlist.append(arg.text)
                    result = self.plugin.console.write(tuple(cmdlist))
                    self.plugin.info("frostbite command result : %s" % result)
                except Exception, e:
                    self.plugin.error("task %s : %s" % (self.name, e))
        else:
            # send rcon commands
            for cmd in self.config.findall("rcon"):
                try:
                    result = self.plugin.console.write("%s" % cmd.text)
                    self.plugin.info("rcon command result : %s" % result)
                except Exception, e:
                    self.plugin.error("task %s : %s" % (self.name, e))

    def _run_enable_plugin_commands(self):
        for cmd in self.config.findall("enable_plugin"):
            try:
                pluginName = cmd.attrib['plugin'].strip().lower()
                plugin = self.plugin.console.getPlugin(pluginName)
                if plugin:
                    if plugin.isEnabled():
                        self.plugin.info('Plugin %s is already enabled.' % pluginName)
                    else:
                        plugin.enable()
                        self.plugin.info('Plugin %s is now ON' % pluginName)
                else:
                    self.plugin.warn('No plugin named %s loaded.' % pluginName)
            except Exception, e:
                self.plugin.error("task %s : %s" % (self.name, e))

    def _run_disable_plugin_commands(self):
        for cmd in self.config.findall("disable_plugin"):
            try:
                pluginName = cmd.attrib['plugin'].strip().lower()
                plugin = self.plugin.console.getPlugin(pluginName)
                if plugin:
                    if not plugin.isEnabled():
                        self.plugin.info('Plugin %s is already disabled.' % pluginName)
                    else:
                        plugin.disable()
                        self.plugin.info('Plugin %s is now OFF' % pluginName)
                else:
                    self.plugin.warn('No plugin named %s loaded.' % pluginName)
            except Exception, e:
                self.plugin.error("task %s : %s" % (self.name, e))

class RestartTask(Task):
    def __init__(self, plugin, config):
        Task.__init__(self, plugin, config)
        self.schedule()

    def schedule(self):
        """
        schedule this task
        """
        self.plugin._restart_tasks.add(self)

    def cancel(self):
        """
        remove this task from schedule
        """
        self.plugin._restart_tasks.remove(self)

    def runcommands(self):
        if 'delay' in self.config.attrib:
            delay_minutes = b3.functions.time2minutes(self.config.attrib['delay'])
            threading.Timer(delay_minutes * 60, Task.runcommands, [self]).start()
        else:
            Task.runcommands(self)


class CronTask(Task):
    cronTab = None
    seconds = None
    minutes = None
    hour = None
    day = None
    month = None
    dow = None

    def __init__(self, plugin, config):
        Task.__init__(self, plugin, config)
        self.schedule()
        
    def schedule(self):
        """
        schedule this task
        """
        self._getScheduledTime(self.config.attrib)
        self.cronTab = b3.cron.PluginCronTab(self.plugin, self.runcommands, 
            self.seconds, self.minutes, self.plugin._convertCronHourToUTC(self.hour), self.day, self.month, self.dow)
        self.plugin.console.cron + self.cronTab
        
    def cancel(self):
        """
        remove this task from schedule
        """
        if self.cronTab:
            self.plugin.info("canceling scheduled task [%s]" % self.name)
            self.plugin.console.cron - self.cronTab

    def _getScheduledTime(self, attrib):

        if not 'seconds' in attrib:
            self.seconds = 0
        else:
            self.seconds = attrib['seconds']
                    
        if not 'minutes' in attrib:
            self.minutes = '*'
        else:
            self.minutes = attrib['minutes']        
            
        if not 'hour' in attrib:
            self.hour = '*'
        else:
            self.hour = attrib['hour']
            
        if not 'day' in attrib:
            self.day = '*'
        else:
            self.day = attrib['day']
                        
        if not 'month' in attrib:
            self.month = '*'
        else:
            self.month = attrib['month']
            
        if not 'dow' in attrib:
            self.dow = '*'
        else:
            self.dow = attrib['dow']
        
        self.plugin.info('%s %s %s\t%s %s %s' % (self.seconds, self.minutes, self.hour, self.day, self.month, self.dow))
 
class HourlyTask(CronTask):
    def _getScheduledTime(self, attrib):
        self.seconds = 0

        if not 'minutes' in attrib:
            self.plugin.debug("default minutes : 0. Provide a 'minutes' attribute to override")
            self.minutes = 0
        else:
            self.minutes = attrib['minutes']        
            
        self.hour = '*'
        self.day = '*'
        self.month = '*'
        self.dow = '*'
        
class DaylyTask(CronTask):
    def _getScheduledTime(self, attrib):
        self.seconds = 0

        if not 'hour' in attrib:
            self.plugin.debug("default hour : 0. Provide a 'hour' attribute to override")
            self.hour = 0
        else:
            self.hour = attrib['hour']     
            
        if not 'minutes' in attrib:
            self.plugin.debug("default minutes : 0. Provide a 'minutes' attribute to override")
            self.minutes = 0
        else:
            self.minutes = attrib['minutes']        
            
        self.day = '*'
        self.month = '*'
        self.dow = '*'
        
        
if __name__ == '__main__':
    ## tests :
    from b3.fake import FakeConsole, fakeConsole
    import time
    
    def write(self, *args):
        """send text to the console"""
        print "### %r" % args
        if self.gameName in FROSTBITE_GAMES:
            return ['OK']
    FakeConsole.write = write
    
    from b3.config import XmlConfigParser
    
    def test_classic_syntax():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration plugin="scheduler">
            <cron name="test0" seconds="0">
                <rcon>say "hello you"</rcon>
                <rcon>say "hello world"</rcon>
            </cron>
        </configuration>
        """)
        fakeConsole.gameName = 'urt41'
        p = SchedulerPlugin(fakeConsole, conf)
        p.onLoadConfig()
        p.onStartup()
    
    def test_old_bfbc2_syntax():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration plugin="scheduler">
            <cron name="test1" seconds="5,25">
                <bfbc2 command="admin.say">
                    <arg>hello world</arg>
                    <arg>all</arg>
                </bfbc2>
                <bfbc2 command="punkBuster.pb_sv_command">
                    <arg>pb_sv_update</arg>
                </bfbc2>
            </cron>
        </configuration>
        """)
        fakeConsole.gameName = 'bfbc2'
        p1 = SchedulerPlugin(fakeConsole, conf)
        p1.onLoadConfig()
        p1.onStartup()
    
    def test_frostbite_syntax():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration plugin="scheduler">
            <cron name="test2" seconds="10,30">
                <frostbite command="admin.say">
                    <arg>server shuting down</arg>
                    <arg>all</arg>
                </frostbite>
                <frostbite command="admin.shutDown" />
            </cron>
        </configuration>
        """)
        fakeConsole.gameName = 'moh'
        p2 = SchedulerPlugin(fakeConsole, conf)
        p2.onLoadConfig()
        p2.onStartup()
    
    def test_frostbite_combined_syntaxes():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration plugin="scheduler">
            <cron name="test3" seconds="15,35">
                <bfbc2 command="mycommand">
                    <arg>myArg1</arg>
                    <arg>myArg2</arg>
                </bfbc2>
            </cron>
            <cron name="test4" seconds="20,40">
                <frostbite command="mycommand">
                    <arg>myArg1</arg>
                    <arg>myArg2</arg>
                </frostbite>
            </cron>
        </configuration>
        """)
        fakeConsole.gameName = 'bfbc2'
        p3 = SchedulerPlugin(fakeConsole, conf)
        p3.onLoadConfig()
        p3.onStartup()

    def test_plugin_tasks():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration plugin="scheduler">
            <cron name="test_plugin_enable" seconds="0,10,20,30,40,50">
                <enable_plugin plugin="admin"/>
            </cron>
            <cron name="test_plugin_disable" seconds="5,15,25,35,45,55">
                <disable_plugin plugin="admin"/>
            </cron>
            <cron name="test_plugin_fail">
                <enable_plugin plugin="foo"/>
                <disable_plugin plugin="bar"/>
            </cron>
        </configuration>
        """)
        fakeConsole.gameName = 'iourt41'
        p3 = SchedulerPlugin(fakeConsole, conf)
        p3.onLoadConfig()
        p3.onStartup()
    
    def test_daily():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration>
            <daily name="dayly1" hour="19" minutes="11">
                <rcon>say "^9Nightime maprotation in effect."</rcon>
                <rcon>set sv_maprotation "gametype ctf map mp_carentan gametype ctf map mp_toujane gametype ctf map mp_buhlert gametype ctf map mp_railyard gametype ctf map mp_sfrance_final gametype ctf map mp_leningrad gametype ctf map mp_farmhouse gametype ctf map mp_decoy gametype ctf map mp_carentan gametype ctf map mp_dawnville gametype ctf map mp_matmata gametype ctf map mp_breakout gametype ctf map mp_burgundy"</rcon>
            </daily>

            <daily name="dayly2" hour="19" minutes="12">
                <rcon>say "^9Daytime maprotation in effect."</rcon>
                <rcon>set sv_maprotation "gametype ctf map mp_carentan gametype ctf map mp_toujane gametype ctf map mp_xfireb gametype ctf map rnr_neuville gametype ctf map mp_buhlert gametype ctf map mp_railyard gametype ctf map mp_farmhouse gametype ctf map mp_decoy gametype ctf map mp_carentan gametype ctf map mp_alcazaba gametype ctf map mp_dawnville gametype ctf map mp_powcamp gametype ctf map mp_matmata gametype ctf map mp_breakout gametype ctf map mp_burgundy gametype ctf map mp_canal3 gametype ctf map mp_destroyed_village gametype ctf map mp_trainstation"</rcon>
            </daily>
        </configuration>
        """)
        fakeConsole.gameName = 'urt41'
        p3 = SchedulerPlugin(fakeConsole, conf)
        p3.onLoadConfig()
        p3.onStartup()
    
    def test_hourly():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration>
            <hourly name="hourly1" minutes="13">
                <rcon>say "^9Nightime maprotation in effect."</rcon>
                <rcon>set sv_maprotation "gametype ctf map mp_carentan gametype ctf map mp_toujane gametype ctf map mp_buhlert gametype ctf map mp_railyard gametype ctf map mp_sfrance_final gametype ctf map mp_leningrad gametype ctf map mp_farmhouse gametype ctf map mp_decoy gametype ctf map mp_carentan gametype ctf map mp_dawnville gametype ctf map mp_matmata gametype ctf map mp_breakout gametype ctf map mp_burgundy"</rcon>
            </hourly>
        </configuration>
        """)
        fakeConsole.gameName = 'urt41'
        p3 = SchedulerPlugin(fakeConsole, conf)
        p3.onLoadConfig()
        p3.onStartup()
    
    def test_restart():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration>
            <restart name="at restart">
                <rcon>say "we just restarted"</rcon>
            </restart>
        </configuration>
        """)
        fakeConsole.gameName = 'urt41'
        p3 = SchedulerPlugin(fakeConsole, conf)
        p3.onLoadConfig()
        p3.onStartup()
    
    def test_restart_with_delay():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration>
            <restart name="at restart + 7s" delay="7s">
                <rcon>say "we just restarted 7s ago"</rcon>
            </restart>
        </configuration>
        """)
        fakeConsole.gameName = 'urt41'
        p3 = SchedulerPlugin(fakeConsole, conf)
        p3.onLoadConfig()
        p3.onStartup()

    def test_bf3():
        conf = XmlConfigParser()
        conf.setXml("""
        <configuration plugin="scheduler">
            <cron name="every3m" minutes="*/3">
                <frostbite command="yell">
                    <arg>my text</arg>
                    <arg>10</arg>
                    <arg>all</arg>
                </frostbite>
            </cron>
        </configuration>
        """)
        fakeConsole.gameName = 'bf3'
        p2 = SchedulerPlugin(fakeConsole, conf)
        p2.onLoadConfig()
        p2.onStartup()


    #test_daily()
    #test_hourly()
    #test_restart()
    #test_restart_with_delay()
    #test_classic_syntax()
    #test_old_bfbc2_syntax()
    #test_frostbite_syntax()
    #test_frostbite_combined_syntaxes()
    #test_plugin_tasks()
    test_bf3()


    for i in range(60):
        print time.asctime(time.localtime())
        time.sleep(5)

