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
# 15/11/2010 - 1.2 - Courgete
# - now also work for Medal of Honor
# - changed config file syntax for bfbc2 and moh (old syntax still works)
# - can specify seconds as in the GNU cron syntax

__version__ = '1.2'
__author__    = 'Courgette'

import thread, time, string, os
import b3, b3.events, b3.plugin


#--------------------------------------------------------------------------------------------------
class SchedulerPlugin(b3.plugin.Plugin):
    _tasks = None
    _tzOffset = 0
    
    def onStartup(self):
        pass
        
    def onLoadConfig(self):
        
        # remove eventual existing tasks
        if self._tasks:
            for t in self._tasks:
                t.cancel()
    
        # Get time_zone from main B3 config
        tzName = self.console.config.get('b3', 'time_zone').upper()
        self._tzOffest = b3.timezones.timezones[tzName]
    
        # load cron tasks from config
        self._tasks = []
        for taskconfig in self.config.get('cron'):
            try:
                task = Task(self, taskconfig)
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
            UTChour = (int(h.strip()) - self._tzOffest)%24
            return "%d/%s" % (UTChour, divider)
        else:
            return (int(hourcron.strip()) - self._tzOffest)%24
 
 
class TaskConfigError(Exception): pass

class Task(object):
    config = None
    cronTab = None
    plugin = None
    name = None
    seconds = None
    minutes = None
    hour = None
    day = None
    month = None
    dow = None
    
    def __init__(self, plugin, config):
        self.plugin = plugin
        self.config = config
        
        self.name = config.attrib['name']
        if not 'name' in config.attrib:
            self.plugin.info("attribute 'name' not found in task")
        else:
            self.name = config.attrib['name']
            
        self.plugin.debug("setting up %s [%s]" % (self.__class__.__name__, self.name) )
        if self.plugin.console.gameName in ('bfbc2', 'moh'):
            frostbitecommands = self.config.findall("frostbite") + self.config.findall("bfbc2")
            if len(frostbitecommands) == 0:
                    raise TaskConfigError('no frostbite element found for task %s' % self.name)
            for cmd in frostbitecommands:
                if not 'command' in cmd.attrib:
                    raise TaskConfigError('cannot find \'command\' attribute for a frostbite element')
                text = cmd.attrib['command']
                for arg in cmd.findall('arg'):
                    text += " %s" % arg.text
                self.plugin.debug("frostbite : %s" % text)
        else:
            ## classical Q3 rcon command
            rconcommands = self.config.findall("rcon")
            if len(rconcommands) == 0:
                    raise TaskConfigError('no rcon element found for task %s' % self.name)
            for cmd in rconcommands:
                self.plugin.debug("rcon : %s" % cmd.text)
            
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
        
    def runcommands(self):
        self.plugin.info("running scheduled commands from %s" % self.name)

        if self.plugin.console.gameName in ('bfbc2', 'moh'):
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
 
class HourlyTask(Task):
    def _getScheduledTime(self, attrib):

        if not 'minutes' in attrib:
            self.plugin.debug("default minutes : 0. Provide a 'minutes' attribute to override")
            self.minutes = 0
        else:
            self.minutes = attrib['minutes']        
            
        self.hour = '*'
        self.day = '*'
        self.month = '*'
        self.dow = '*'
        
class DaylyTask(Task):
    def _getScheduledTime(self, attrib):
    
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
        if self.gameName in ('bfbc2','moh'):
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
        p3.onStartup()
    
    
    
    
    
    test_classic_syntax()
    test_old_bfbc2_syntax()
    test_frostbite_syntax()
    test_frostbite_combined_syntaxes()
    
    for i in range(60*5):
        print time.asctime(time.localtime())
        time.sleep(1)
        
