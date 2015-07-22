scheduler plugin for BigBrotherBot [![BigBrotherBot](http://i.imgur.com/7sljo4G.png)][B3]
==================================

Description
-----------

This plugin as been made to allow you to easily setup scheduled rcon commands.


******
*NOTE: since B3 v1.10.5 beta this plugin has been included in the standard plugins set, thus all patches and updates will be performed in the official B3 repository.*
******


Features :
----------

Will schedule tasks of type :
 * hourly
 * daily
 * cron like tasks (http://www.google.com/search?q=man+crontab+5)
 * restart
 
which can define rcon commands to be run on your game server or which can
enable or disable any B3 plugin. 


Installation
------------

 * copy scheduler.py into b3/extplugins
 * copy scheduler.xml into b3/extplugins/conf
 * update your main b3 config file with :

<plugin name="scheduler" config="@b3/extplugins/conf/scheduler.xml" />


Changelog
---------

07/06/2009 - v0.1.0 - Courgette
- first public release. Waiting for feedbacks

07/06/2009 - v0.1.1 - Courgette
- correct spelling
- hours specified in config are now understood in the timezone setup in the main B3 config

27/04/2010 - 1.0 - Courgette
- config error early detection with userfriendly message
- can run bfbc2 commands

28/04/2010 - 1.1 - Courgette
- fix issue with bfbc2 commands arguments
- better handling of command errors

15/11/2010 - 1.2 - Courgette
- now also work for Medal of Honor
- changed config file syntax for bfbc2 and moh (old syntax still works)
- can specify seconds as in the GNU cron syntax

30/05/2011 - 1.2.1 - Courgette
- fix bug in hourly and daily tasks introduced in 1.2

21/08/2011 - 1.3 - Courgette
- add restart tasks (which are executed when B3 starts/restarts
- add enable_plugin and disable_plugin commands

06/10/2012 - 1.4 - Courgette
- add support for BF3



Support
-------

http://forum.bigbrotherbot.net/plugins-by-courgette/scheduler-plugin/
