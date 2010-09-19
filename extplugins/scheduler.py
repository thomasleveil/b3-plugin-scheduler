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

__version__ = '1.1'
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
            self.plugin.error("attribute 'name' not found in task")
        else:
            self.name = config.attrib['name']
            
        self.plugin.debug("setting up %s [%s]" % (self.__class__.__name__, self.name) )
        if self.plugin.console.gameName == 'bfbc2':
            bfbc2commands = self.config.findall("bfbc2")
            if len(bfbc2commands) == 0:
                    raise TaskConfigError('no bfbc2 element found for task %s' % self.name)
            for cmd in bfbc2commands:
                if not 'command' in cmd.attrib:
                    raise TaskConfigError('cannot find \'command\' attribute for a bfbc2 element')
                text = cmd.attrib['command']
                for arg in cmd.findall('arg'):
                    text += " %s" % arg.text
                self.plugin.debug("bfbc2 : %s" % text)
        else:
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
            0, self.minutes, self.plugin._convertCronHourToUTC(self.hour), self.day, self.month, self.dow)
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

        if self.plugin.console.gameName == 'bfbc2':
                # send bfbc2 commands     
                for bfbc2node in self.config.findall("bfbc2"):
                    try:
                        commandName = bfbc2node.attrib['command']
                        cmdlist = [commandName]
                        for arg in bfbc2node.findall('arg'):
                            cmdlist.append(arg.text)
                        result = self.plugin.console.write(tuple(cmdlist))
                        self.plugin.info("bfbc2 command result : %s" % result)
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

        if not 'minutes' in attrib:
            self.plugin.warning("attribute 'minutes' not found in task, using '*' as default")
            self.minutes = '*'
        else:
            self.minutes = attrib['minutes']        
            
        if not 'hour' in attrib:
            self.plugin.error("attribute 'hour' not found in task, using '*' as default")
            self.hour = '*'
        else:
            self.hour = attrib['hour']
            
        if not 'day' in attrib:
            self.plugin.error("attribute 'day' not found in task, using '*' as default")
            self.day = '*'
        else:
            self.day = attrib['day']
                        
        if not 'month' in attrib:
            self.plugin.error("attribute 'month' not found in task, using '*' as default")
            self.month = '*'
        else:
            self.month = attrib['month']
            
        if not 'dow' in attrib:
            self.plugin.error("attribute 'dow' not found in task, using '*' as default")
            self.dow = '*'
        else:
            self.dow = attrib['dow']
            
 
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
    from b3.fake import fakeConsole
    import time
    
    from b3.config import XmlConfigParser
    
    conf = XmlConfigParser()
    conf.setXml("""
    <configuration plugin="scheduler">
        <cron name="test1">
            <bfbc2 command="punkBuster.pb_sv_command">
                <arg>pb_sv_update</arg>
            </bfbc2>
        </cron>
    </configuration>
    """)
    
    
    ## create an instance of the plugin to test
    fakeConsole.gameName = 'bfbc2'
    p = SchedulerPlugin(fakeConsole, conf)
    p.onStartup()

    time.sleep(60*5)
    