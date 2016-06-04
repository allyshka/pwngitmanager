## PwnGitManager

### Overview
This git manager helps during penetration testing process. When you found opened .git repository on perimeter. On
company web site. What do you do next? Download all files from them by git-ripper scripts, I guess. But it's not always
necessary, because repository can be huge and often you need only some files from it. Config files for example.
Besides, many requests to the server (while downloading objects) can alert IDS.

For that cases I wrote this tool. It's download only index file from repository and next you can search files, paths
and then download and view only what you need.

![Git Pwn](http://s12.postimg.org/vtgyt20il/gitpwn.gif)

### Installation

You do not need special requirements for now. Only **python 3** and *python-telegram-bot* if you want use telegram bot
of course.


### Use
If you use Windows then install **pyreadline**

```
pip install pyreadline
```

Tool can run in two modes: *interactive* and *command*

#### interactive mode:
```
python3 pwngit.py
URL not specified. Run in interactive mode.
> use snoopdogg.com
Valid scheme not found in url. Using http instead.
Working with http://snoopdogg.com repository
Downloading index file (http://snoopdogg.com/.git/index) ...
```

You can use URL with scheme *http* or *https*. You can add path to git (ex.: http://example.com/path/to/.git) or, 
if git folder in web root, you can use short URL (ex.: example.com) 

```
Commands:
help                 show this info
ls [dir]             list files in repository path
get <path|mask>      get, save and show file by path or mask. Ex.: get *.ini
find <query>         find by file names. Ex.: find *.sql
search <query>       find by folder name. Ex.: search wp-content
exit|quit|e|q        exit to select repository mode
```

You can use [TAB] for autocomplete paths. All getted files saves in data/<repo>/ folder by them actual paths 
in repository.

#### command mode:
In this mode you can send command right in command line with **-c/--command** flag.

```
python3 pwngit.py <repo> -c <command>
python3 pwngit.py example.com -c "get wp-config.php"
```

#### proxy:
You can set up proxy with **-p/--proxy** flag. Format is **http(s)://127.0.0.1:8080". Socks5 not supported yet because of minimum requirements.  

### Telegram bot
Install **python-telegram-bot** and replace [TOKEN_HERE] in telegrambot.py by your BotFather token.

```
pip install python-telegram-bot
python3 telegrambot.py
```
Send help to bot and see full command list 

### TODO
- ~~Add get files by mask. Like ```get application/*.cfg```~~
- ~~Add command for all repository files download~~
- ~~Add proxy support~~
- Add multithread downloads
- Add .git directory listing detection
- Add database storage for repository data
- Add packs detection

### Thanks
Big thank to Sean B. Palmer for [gin](https://github.com/sbp/gin) tool. I was take index file parser function from 
there.
