#!/usr/bin/env python3
# _*_ coding:utf-8 _*_
import gitlib
import logging
from telegram import Updater
import sys

token = "[TOKEN_HERE]"
# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)


def shutdown(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Goodbye, master!")
    updater.stop()


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Hello, master!")


def git(bot, update, args):
    """
        if message_length >= 4096:
            i = 0
        while i < message_length:
            bot.sendMessage(
                chat_id,
                text="```\n{0}```".format(output[i:i+4095]),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            i += 4095
        else:
    """
    chat_id = update.message.chat_id
    if len(args) < 2:
        bot.sendMessage(chat_id, text="Usage: /git <url> <command> [params]\n"
                                      "Commands:\n"
                                      "ls [dir] — directory listing (try it for first)\n"
                                      "find <query> — search in filenames can use wildcard * (ex.: find *.tgz)\n"
                                      "search <query> — search in all path, working as LIKE in T-SQL\n"
                                      "get <path> — get file content\n")
    else:
        url = args[0]
        cmd = args[1]
        params = args[2:]
        try:
            new = gitlib.GitManager(url, False, True)
            output = new.exec({"cmd": cmd, "args": params})
        except ValueError as e:
            output = e
        message_length = len(output)
        if message_length >= 4096:
            bot.sendMessage(
                chat_id,
                text="```\n{0}```".format(output[0:4092]+"..."),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            bot.sendMessage(
                chat_id,
                text="```\n{0}```".format(output[0:message_length]),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

if __name__ == '__main__':
    updater = Updater(token=token)
    dispatcher = updater.dispatcher
    dispatcher.addTelegramCommandHandler('shutdown', shutdown)
    dispatcher.addTelegramCommandHandler('start', start)
    dispatcher.addTelegramCommandHandler('git', git)
    updater.start_polling()
    sys.exit(0)
