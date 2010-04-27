scheduler plugin for Big Brother Bot (www.bigbrotherbot.com)
============================================================

By #UbU#Courgette


Description
-----------

This plugin as been made to allow you to easily setup scheduled rcon commands.

Features :
----------

 * hourly tasks
 * daily tasks
 * cron like tasks (http://www.google.com/search?q=man+crontab+5)

Installation
------------

 * copy scheduler.py into b3/extplugins
 * copy scheduler.xml into b3/extplugins/conf
 * update your main b3 config file with :

<plugin name="scheduler" priority="18" config="@b3/extplugins/conf/scheduler.xml"/>


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
  
Support
-------

http://www.bigbrotherbot.com/forums/index.php?topic=947