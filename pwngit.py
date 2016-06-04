#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
import gitlib
import argparse
import sys


def parse_cmd(cmd):
    command = {"cmd": "", "args": []}
    cmds = cmd.split(" ")
    if len(cmds) >= 1:
        command.update({"cmd": cmds[0], "args": cmds[1:]})
    else:
        print("Wrong command!")
        return False
    return command


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs='?', type=str, help="URL with path to git")
    parser.add_argument("-c", "--command", type=str, help="Raw command to execute")
    parser.add_argument("-f", "--force", type=bool, default=False, help="Force reload index file")
    parser.add_argument("-p", "--proxy", type=str, help="Proxy connection to git. ex.: http://127.0.0.1:8080")
    arguments = parser.parse_args()
    if arguments.proxy:
        proxy = arguments.proxy
    else:
        proxy = None
    if not arguments.url:
        cmd_list = ["list", "use", "help"]
        print("URL not specified. Run in interactive mode.")
        gitlib.Interactive(proxy_server=proxy)
    else:
        c = {}
        if arguments.url:
            url = arguments.url
            if arguments.command:
                c = parse_cmd(arguments.command)
                if c is False:
                    sys.exit(1)
            force = arguments.force
            if c:
                try:
                    new = gitlib.GitManager(url, force, True, proxy_server=proxy)
                    print(new.exec(c).rstrip())
                except ValueError as e:
                    print(e)
            else:
                new = gitlib.GitManager(url, force)
                new.run()
