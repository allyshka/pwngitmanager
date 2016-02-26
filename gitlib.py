# _*_ coding:utf-8 _*_
try:
    import readline
except ImportError:
    import pyreadline as readline
import urllib.request
from urllib.parse import urlparse

# from gin
import binascii
import collections
import json
import mmap
import struct
import zlib
import os.path
import sys


def check(boolean, message):
    if not boolean:
        import sys
        print("error: " + message, file=sys.stderr)
        sys.exit(1)


def parse(filename, pretty=True):
    with open(filename, "rb") as o:
        if hasattr(mmap, 'PROT_READ'):
            f = mmap.mmap(o.fileno(), 0, prot=mmap.PROT_READ)
        else:
            f = mmap.mmap(o.fileno(), 0, access=mmap.ACCESS_READ)

        def read(format):
            # "All binary numbers are in network byte order."
            # Hence "!" = network order, big endian
            format = "! " + format
            bytes = f.read(struct.calcsize(format))
            return struct.unpack(format, bytes)[0]

        index = collections.OrderedDict()

        # 4-byte signature, b"DIRC"
        index["signature"] = f.read(4).decode("ascii")
        check(index["signature"] == "DIRC", "Not a Git index file")

        # 4-byte version number
        index["version"] = read("I")
        check(index["version"] in {2, 3},
              "Unsupported version: %s" % index["version"])

        # 32-bit number of index entries, i.e. 4-byte
        index["entries"] = read("I")

        yield index

        for n in range(index["entries"]):
            entry = collections.OrderedDict()

            entry["entry"] = n + 1

            entry["ctime_seconds"] = read("I")
            entry["ctime_nanoseconds"] = read("I")
            if pretty:
                entry["ctime"] = entry["ctime_seconds"]
                entry["ctime"] += entry["ctime_nanoseconds"] / 1000000000
                del entry["ctime_seconds"]
                del entry["ctime_nanoseconds"]

            entry["mtime_seconds"] = read("I")
            entry["mtime_nanoseconds"] = read("I")
            if pretty:
                entry["mtime"] = entry["mtime_seconds"]
                entry["mtime"] += entry["mtime_nanoseconds"] / 1000000000
                del entry["mtime_seconds"]
                del entry["mtime_nanoseconds"]

            entry["dev"] = read("I")
            entry["ino"] = read("I")

            # 4-bit object type, 3-bit unused, 9-bit unix permission
            entry["mode"] = read("I")
            if pretty:
                entry["mode"] = "%06o" % entry["mode"]

            entry["uid"] = read("I")
            entry["gid"] = read("I")
            entry["size"] = read("I")

            entry["sha1"] = binascii.hexlify(f.read(20)).decode("ascii")
            entry["flags"] = read("H")

            # 1-bit assume-valid
            entry["assume-valid"] = bool(entry["flags"] & (0b10000000 << 8))
            # 1-bit extended, must be 0 in version 2
            entry["extended"] = bool(entry["flags"] & (0b01000000 << 8))
            # 2-bit stage (?)
            stage_one = bool(entry["flags"] & (0b00100000 << 8))
            stage_two = bool(entry["flags"] & (0b00010000 << 8))
            entry["stage"] = stage_one, stage_two
            # 12-bit name length, if the length is less than 0xFFF (else, 0xFFF)
            namelen = entry["flags"] & 0xFFF

            # 62 bytes so far
            entrylen = 62

            if entry["extended"] and (index["version"] == 3):
                entry["extra-flags"] = read("H")
                # 1-bit reserved
                entry["reserved"] = bool(entry["extra-flags"] & (0b10000000 << 8))
                # 1-bit skip-worktree
                entry["skip-worktree"] = bool(entry["extra-flags"] & (0b01000000 << 8))
                # 1-bit intent-to-add
                entry["intent-to-add"] = bool(entry["extra-flags"] & (0b00100000 << 8))
                # 13-bits unused
                # used = entry["extra-flags"] & (0b11100000 << 8)
                # check(not used, "Expected unused bits in extra-flags")
                entrylen += 2

            if namelen < 0xFFF:
                entry["name"] = f.read(namelen).decode("utf-8", "replace")
                entrylen += namelen
            else:
                # Do it the hard way
                name = []
                while True:
                    byte = f.read(1)
                    if byte == "\x00":
                        break
                    name.append(byte)
                entry["name"] = b"".join(name).decode("utf-8", "replace")
                entrylen += 1

            padlen = (8 - (entrylen % 8)) or 8
            nuls = f.read(padlen)
            check(set(nuls) == {0}, "padding contained non-NUL")

            yield entry

        indexlen = len(f)
        extnumber = 1

        while f.tell() < (indexlen - 20):
            extension = collections.OrderedDict()
            extension["extension"] = extnumber
            extension["signature"] = f.read(4).decode("ascii")
            extension["size"] = read("I")

            # Seems to exclude the above:
            # "src_offset += 8; src_offset += extsize;"
            extension["data"] = f.read(extension["size"])
            extension["data"] = extension["data"].decode("iso-8859-1")
            if pretty:
                extension["data"] = json.dumps(extension["data"])

            yield extension
            extnumber += 1

        checksum = collections.OrderedDict()
        checksum["checksum"] = True
        checksum["sha1"] = binascii.hexlify(f.read(20)).decode("ascii")
        yield checksum

        f.close()


def parse_file(arg, pretty=True):
    data = ""
    file_hash = {}
    if pretty:
        properties = {
            "version": "[header]",
            "entry": "[entry]",
            "extension": "[extension]",
            "checksum": "[checksum]"
        }
    else:
        data += "["

    for item in parse(arg, pretty=pretty):
        c_name = c_hash = ""
        if pretty:
            for key, value in properties.items():
                if key in item:
                    data += value
                    break
            else:
                data += "[?]"

        if pretty:
            for key, value in item.items():
                if key == "name":
                    c_name = value
                if key == "sha1":
                    c_hash = value
                data += "\n    " + str(key) + "=" + str(value)
        else:
            data += json.dumps(item)
        last = "checksum" in item
        if not last:
            if pretty:
                data += "\n"
            else:
                data += ","

        if c_name and c_hash:
            file_hash.update({c_name: c_hash})

    if not pretty:
        data += "]"
    return data, file_hash


def gin_file(path):
    return parse_file(path, pretty=True)


def ensure_dir(f):
    if not os.path.exists(f):
        os.makedirs(f)


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def get_url(url, mess="index", exit_on_error=True, raw=False):
    try:
        response = urllib.request.urlopen(url, timeout=5)
        return {"error": 0, "response": response}
    except urllib.error.HTTPError as e:
        mess = "Error! Cannot get {0} file: {1}".format(mess, e)
        if raw:
            return {"error": 1, "response": mess}
        else:
            print(mess)
            if exit_on_error:
                sys.exit(1)
    except urllib.error.URLError as e:
        if raw:
            return {"error": 1, "response": e}
        else:
            print(e)
            if exit_on_error:
                sys.exit(1)
    return False


# This class enable list autocompletion
class ListCompleter(object):  # Custom completer

    def __init__(self, options):
        self.options = options

    def complete(self, text, state):
        result = []
        if state == 0:  # on first trigger, build possible matches
            if text:  # cache matches (entries that start with entered text)
                current_options = self.options
                current_path = os.path.dirname(text)
                path = text.split("/")
                if len(path) > 1:
                    path = current_path.split("/")
                    current_path += "/"
                    text = os.path.basename(text)
                    for p in path:
                        if type(current_options) is dict:
                            if p in current_options:
                                current_options = current_options[p]
                            else:
                                return None
                        else:
                            break
                if type(current_options) is dict:
                    for k, v in current_options.items():
                        value = ""
                        if type(v) is dict:
                            value = k + "/"
                        elif type(k) is str:
                            value = k
                        if value and value.startswith(text):
                            result.append(current_path + value)
            else:  # no text entered, all matches possible
                for k, v in self.options.items():
                    if type(v) is dict:
                        result.append(k + "/")
                    elif type(k) is str:
                        result.append(k)
            self.matches = sorted(result)

        # return match indexed by state
        try:
            return self.matches[state]
        except IndexError:
            return None


class RunCommand(object):
    def __init__(self, data, files, opts, raw_cmd=False):
        self.raw_cmd = True if raw_cmd else False
        self.data = data
        self.files = files
        self.options = opts

    def ret(self, message):
        if self.raw_cmd:
            return message
        else:
            print(message)

    def search(self, arg):
        needle = " ".join(arg)
        if len(needle) >= 3:
            out = self.__find(needle)
            if out:
                return self.ret("\n".join(out))
            else:
                return self.ret("Cannot find any objects contains this search query.")
        else:
            return self.ret("Search query must be greater than 3 characters.")

    def find(self, arg):
        needle = " ".join(arg)
        if len(needle) >= 3:
            out = self.__find(needle, True)
            if out:
                return self.ret("\n".join(out))
            else:
                return self.ret("Cannot find any objects contains this search query.")
        else:
            return self.ret("Search query must be greater than 3 characters.")

    def ls(self, arg):
        if arg:
            return self.ret(self.__dir("".join(arg)))
        else:
            return self.ret(self.__dir())

    def help(self, arg):
        print("Commands:\n"
              "help                 show this info\n"
              "ls [dir]             list files in repository path\n"
              "get <path|mask>      get, save and show file by path or mask. Ex.: get *.ini\n"
              "find <query>         find files by name or path. Ex.: find *.sql\n"
              "search <query>       find folders by name or path. Ex.: search wp-content\n"
              "exit|quit|e|q        exit to select repository mode\n")

    def get(self, arg):
        for a in arg:
            files = self.__find(a, True)
            if files:
                answer = True
                show = True
                files_count = len(files)
                if files_count > 1:
                    show = False
                if files_count > 100:
                    answer = query_yes_no("Are you sure to load {0} files from repository?".format(len(files)))
                if answer is True:
                    for file in files:
                        self.__get(file, show)
            else:
                return self.ret("Cannot find any file(s)".format(files))

    def __get(self, a, show):
        folder = self.data[a][0:2]
        file = self.data[a][2:]
        object_file_path = self.options["git_obj_dir"] + "/" + folder + "/" + file
        file_path = self.options["dir_name"] + "/" + a
        url_path = self.options["git_obj_url"] + "/" + folder + "/" + file
        if os.path.isfile(file_path) is True:
            if self.raw_cmd is True or (show is True and query_yes_no("File already exists. View?")):
                return self.ret(self.__show(file_path))
        if os.path.isfile(object_file_path) is True:
            if self.raw_cmd or (show is True and query_yes_no("Object file already exists. Unpack?")):
                with open(object_file_path, "rb") as ofile:
                    deflate_data = self.__deflate(ofile.read())
                    self.__write(file_path, deflate_data[deflate_data.find(b'\x00')+1:])
                    ofile.close()
                return self.ret(self.__show(file_path))
        else:
            ensure_dir(self.options["git_obj_dir"] + "/" + folder)
            print("Downloading '{0}' file ...".format(a))
            resp = self.__download(url_path)
            if resp is False:
                return resp
            if resp["error"] is 1:
                return self.ret(resp["response"])
            else:
                resp = resp["response"]
                data = resp.read()
                deflate_data = self.__deflate(data)
                self.__write(object_file_path, data)
                self.__write(file_path, deflate_data[deflate_data.find(b'\x00')+1:])
                if show is True:
                    return self.ret(self.__show(file_path))
                else:
                    return self.ret("File '{0}' downloaded successfully.".format(a))

    def __find(self, needle, in_files=False):
        haystack = self.data.keys()
        needle = needle.casefold()
        dirname = os.path.dirname(needle).casefold()
        filename = os.path.basename(needle).casefold()
        if in_files:
            if filename.startswith("*"):
                if dirname:
                    out = [s for s in haystack if os.path.dirname(s.casefold()) == dirname]
                    if out and filename:
                        out = [s for s in out if os.path.basename(s.casefold()).endswith(filename[1:])]
                else:
                    out = [s for s in haystack if os.path.basename(s.casefold()).endswith(needle[1:])]
            elif needle.endswith("*"):
                if dirname:
                    out = [s for s in haystack if os.path.dirname(s.casefold()) == dirname]
                    if out and filename:
                        out = [s for s in out if os.path.basename(s.casefold()).startswith(filename[:-1])]
                else:
                    out = [s for s in haystack if os.path.basename(s.casefold()).startswith(needle[:-1])]
            else:
                out = [s for s in haystack if needle in os.path.basename(s.casefold())]
        else:
            if needle.endswith("*"):
                out = list(set(
                    [os.path.dirname(s) for s in haystack if needle[:-1] in os.path.dirname(s.casefold())]
                ))
            else:
                out = list(set(
                    [os.path.dirname(s) for s in haystack if os.path.dirname(s.casefold()).endswith(needle)]
                ))
        return out

    def __dir(self, text=""):
        result = []
        if text:  # cache matches (entries that start with entered text)
            current_options = self.files
            current_path = os.path.dirname(text)
            path = text.split("/")
            if len(path) > 1:
                path = current_path.split("/")
                current_path += "/"
                text = os.path.basename(text)
                for p in path:
                    if type(current_options) is dict:
                        if p in current_options:
                            current_options = current_options[p]
                        else:
                            return None
                    else:
                        break
            if type(current_options) is dict:
                for k, v in current_options.items():
                    value = ""
                    if type(v) is dict:
                        value = k + "/"
                    elif type(k) is str:
                        value = k
                    if value and value.startswith(text):
                        result.append(current_path + value)
        else:  # no text entered, all matches possible
            for k, v in self.files.items():
                if type(v) is dict:
                    result.append(k + "/")
                elif type(k) is str:
                    result.append(k)
        return "\n".join(sorted(result))

    def __download(self, url):
        return get_url(url, "object ({0})".format(url), False, self.raw_cmd)

    def __deflate(self, data):
        return zlib.decompress(data)

    def __write(self, fpath, data):
        ensure_dir(os.path.dirname(fpath))
        with open(fpath, "wb") as f:
            f.write(data)
            f.close()

    def __show(self, fpath):
        f = open(fpath, encoding="utf-8")
        data = f.read()
        f.close()
        if os.name == "nt":
            return data.encode("utf-8").decode(sys.stdout.encoding)
        else:
            return data


def build_nested_helper(path, text, container):
    segs = path.split('/')
    head = segs[0]
    tail = segs[1:]
    if not tail:
        container[head] = 1
    else:
        if head not in container:
            container[head] = {}
        build_nested_helper('/'.join(tail), text, container[head])


def build_nested(paths):
    container = {}
    for path in paths:
        build_nested_helper(path, path, container)
    return container


class GitManager:
    def __init__(self, url, reload=False, raw_cmd=False, interactive=False):
        self.interactive = True if interactive else False
        self.raw_cmd = True if raw_cmd else False
        self.message = ""
        self.data_dir = "data/"
        self.url = url
        self.files = self.index_data = {}
        if reload:
            self.reload = True
        else:
            self.reload = False
        # check scheme
        if urlparse(self.url).scheme not in ["http", "https"]:
            if self.raw_cmd is False:
                print("Valid scheme not found in url. Using http instead.")
            self.git_url = self.url = "http://" + self.url
            if self.raw_cmd is False:
                print("Working with {0} repository".format(self.url))
        else:
            self.git_url = self.url
        if urlparse(self.url).path is "":
            self.git_url += "/.git"
            self.url += "/.git/index"
        else:
            self.url += "/index"
        url_o = urlparse(self.url)
        if url_o.scheme == "https":
            self.dir_name = self.data_dir + "https_"+url_o.netloc.replace(":", "_")
        else:
            self.dir_name = self.data_dir + url_o.netloc.replace(":", "_")
        self.git_dir = self.dir_name + "/.git"
        self.tree_file = self.dir_name + "/.git/files.tree"
        self.index_file = self.git_dir + "/index"
        self.index_parsed_file = self.index_file + ".parsed"
        self.index_json_file = self.index_file + ".json"
        self.url_file = self.dir_name + "/url.git"
        self.options = {
            "dir_name": self.dir_name,
            "git_url": self.git_url,
            "git_obj_url": self.git_url + "/objects",
            "git_dir": self.git_dir,
            "git_obj_dir": self.git_dir + "/objects"
        }
        if self.check_index():
            try:
                self.download_index()
            except ValueError:
                raise
        if self.check_tree():
            self.save_index()
        self.load_index()

    def check_index(self):
        return not os.path.exists(self.index_file) or self.reload is True

    def check_tree(self):
        return not os.path.exists(self.tree_file)

    def download_index(self):
        self.show("Downloading index file ({0}) ...".format(self.url))
        if self.interactive is True:
            r = get_url(self.url, "index", not self.interactive, self.raw_cmd)
            if r is False:
                raise ValueError
        else:
            r = get_url(self.url, "index", not self.raw_cmd, self.raw_cmd)
        if r["error"] is 1:
            try:
                self.show(r["response"], True)
            except ValueError:
                raise
        else:
            r = r["response"]
        ensure_dir(self.git_dir)
        with open(self.url_file, "w", encoding="utf-8") as uf:
            uf.write(self.git_url)
            uf.close()
        with open(self.index_file, "wb") as indexf:
            indexf.write(r.read())
            indexf.close()

    def show(self, message, error=False):
        if self.raw_cmd:
            if type(message) is not str:
                message = repr(message)
            self.message += message + "\n"
            if error:
                raise ValueError(message)
        else:
            print(message)

    def save_index(self):
        index_parsed_data, self.index_data = gin_file(self.index_file)
        with open(self.index_parsed_file, "w", encoding="utf-8") as ipf:
            ipf.write(index_parsed_data)
            ipf.close()
        with open(self.index_json_file, "w", encoding="utf-8") as ijf:
            ijf.write(json.dumps(self.index_data, sort_keys=True, indent=2))
            ijf.close()
        self.files = build_nested(list(self.index_data.keys()))
        with open(self.tree_file, "w", encoding="utf-8") as tf:
            tf.write(json.dumps(self.files))
            tf.close()

    def load_index(self):
        if not self.index_data:
            self.index_data = json.load(open(self.index_json_file))
        if not self.files:
            self.files = json.load(open(self.tree_file))

    def run(self):
        completer = ListCompleter(self.files)
        readline.set_completer_delims(" ")
        readline.set_completer(completer.complete)
        readline.parse_and_bind('tab: complete')
        executor = RunCommand(self.index_data, self.files, self.options)
        while True:
            commands = input("{0} > ".format(self.git_url))
            if commands in ["exit", "quit", "q", "e"]:
                if self.interactive is True:
                    break
                else:
                    sys.exit(0)
            command = commands.split(" ")
            if hasattr(executor, command[0]):
                getattr(executor, command[0])(command[1:])
            else:
                print("Command '{0}' not found".format(command[0]))

    def exec(self, cmd):
        executor = RunCommand(self.index_data, self.files, self.options, self.raw_cmd)
        command = cmd["cmd"]
        if command == "exit" or command == "quit" or command == "q":
            sys.exit(0)
        if hasattr(executor, command):
            self.show(getattr(executor, command)(cmd["args"]))
        else:
            self.show("Command '{0}' not found".format(command), True)
        return self.message


class Interactive:

    def __init__(self):
        self.data_dir = "data/"
        self.cmd_list = ["ls", "help", "use"]
        while True:
            command = input("> ")
            if command in ["exit", "quit", "e", "q"]:
                print("Goodbye, master!")
                sys.exit(0)
            else:
                cmd = command.split(" ")
                if cmd[0] not in self.cmd_list:
                    print("command '{0}' not recognized".format(cmd[0]))
                    continue
                else:
                    getattr(self, cmd[0])(cmd[1:])

    def help(self, args):
        print("Command list:\n"
              "exit|quit|e|q       exit from program\n"
              "help                show this message\n"
              "ls                  show working repositories\n"
              "use <url>           run parser on url for working. ex.: use snoopdogg.com")

    def ls(self, args):
        print("\n".join(next(os.walk(self.data_dir))[1]))

    def use(self, args):
        repo = "".join(args)
        try:
            new = GitManager(repo, interactive=True)
            new.run()
        except ValueError:
            pass
