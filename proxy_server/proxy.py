import base64, copy, thread, socket, sys, os, datetime, time, json, threading, email.utils as eut, shutil

debug = False
debug_flag = True
MAX_CACHE_BUFFER = 3
NO_OF_OCC_FOR_CACHE = 3
CACHE_TIME = datetime.timedelta(minutes=5)


if not (len(sys.argv) == 2):
    print "Usage: python %s <PORT_NUM>" % sys.argv[0]
    if debug and debug_flag:
        print sys.argv[0]
    raise SystemExit

try:
    proxy_port = int(sys.argv[1])
except Exception as err:
    print err
    print "Bad Port Number"
    raise SystemExit

if os.path.isdir("./cache"):
    shutil.rmtree("./cache") 
os.makedirs("./cache")

blocked = []
f = open("blacklist.txt", "rb")
data = ""
part = f.read()
while True:
    if not len(part):
        break
    else:
        data = data + part
        part = f.read()
f.close()
blocked = data.splitlines()

admins = []
f = open("username_password.txt", "rb")
data = ""
part = f.read()
while True:
    if not len(part):
        break
    else:
        data = data + part
        part = f.read()
f.close()
data = data.splitlines()
for d in data:
    admins.append(base64.b64encode(d))


def acquire_lock(fileurl):
    if fileurl in locks:
        if debug and debug_flag:
            print fileurl
        lock = locks[fileurl]
    else:
        if debug and debug_flag:
            print fileurl
        lock = threading.Lock()
        locks[fileurl] = lock
    lock.acquire()


def logging(fileurl, client_addr):
    if debug and debug_flag:
        print fileurl
    fileurl = fileurl.replace("/", "__")
    if debug and debug_flag:
        print fileurl
    if not fileurl in logs:
        logs[fileurl] = []
    logs[fileurl].append({"datetime": time.strptime(
        time.ctime(), "%a %b %d %H:%M:%S %Y"), "client": json.dumps(client_addr), })
    if debug and debug_flag:
        print logs[fileurl]


def caching_required(fileurl):
    fileurl = fileurl.replace("/", "__")
    if debug and debug_flag:
        print fileurl

    try:
        log_arr = logs[fileurl]
        if len(log_arr) < NO_OF_OCC_FOR_CACHE:
            return False
        last_third = datetime.datetime.fromtimestamp(time.mktime(
            log_arr[len(log_arr)-NO_OF_OCC_FOR_CACHE]["datetime"]))

        if debug and debug_flag:
            print(datetime.datetime.now() - last_third)

        if not (datetime.datetime.now() - last_third <= CACHE_TIME):
            return False
        else:
            return True

    except Exception as err:
        print err
        return False


def release_lock(fileurl):
    if debug and debug_flag:
        print fileurl
    if fileurl in locks:
        lock = locks[fileurl]
        lock.release()
    else:
        print "Error acquiring lock"
        sys.exit()


def access_cache(client_addr, details):
    if debug and debug_flag:
        print "checking cache"

    fileurl = details["total_url"]

    acquire_lock(fileurl)
    logging(fileurl, client_addr)
    do_cache = caching_required(fileurl)
    details["do_cache"] = do_cache
    if fileurl[0] == "/":
        fileurl[0] = ""

    cache_path = "./cache/"
    cache_path = cache_path + fileurl.replace("/", "__")
    details["cache_path"] = cache_path

    if os.path.isfile(cache_path):
        last_mtime = time.strptime(time.ctime(
            os.path.getmtime(cache_path)), "%a %b %d %H:%M:%S %Y")
    else:
        last_mtime = None
    details["last_mtime"] = last_mtime
    release_lock(fileurl)

    return details


def remove_from_cache(fileurl):
    cache_files = os.listdir("./cache")
    if len(cache_files) < MAX_CACHE_BUFFER:
        return
    for file in cache_files:
        acquire_lock(file)
    last_mtime = logs[cache_files[0]][-1]["datetime"]
    for file in cache_files:
        last_mtime = min(last_mtime, logs[file][-1]["datetime"])
    for file in cache_files:
        if logs[file][-1]["datetime"] == last_mtime:
            file_to_del = file
    os.remove("./cache/" + file_to_del)
    for file in cache_files:
        release_lock(file)


def parse_details(client_addr, client_data):
    try:
        # http:://127.0.0.1:20001/1.txt

        lines = client_data.splitlines()
        l = len(lines)
        while True:
            if lines[l-1] != '':
                break
            else:
                lines.remove('')
                l = len(lines)

        try:
            first_line_tokens = lines[0].split()
            url = first_line_tokens[1]
            url_pos = url.find("://")
        except Exception as err:
            print err
            print "Data insufficient"

        if url_pos == -1:
            protocol = "http"
        else:
            protocol = url[:url_pos]

        url_pos = url_pos + 3
        url = url[(url_pos):]

        port_pos = url.find(":")

        if debug and debug_flag:
            print port_pos

        path_pos = url.find("/")
        if path_pos == -1:
            path_pos = len(url)

        if debug and debug_flag:
            print path_pos

        if port_pos == -1:
            server_url = url[:path_pos]
            if debug and debug_flag:
                print "err"
            server_port = 80
        elif path_pos < port_pos:
            server_url = url[:path_pos]
            if debug and debug_flag:
                print "err"
            server_port = 80
        else:
            server_url = url[:port_pos]
            server_port_det = url[(port_pos+1):path_pos]
            server_port = int(server_port_det)

        first_line_tokens[1] = url[path_pos:]
        lines[0] = ' '.join(first_line_tokens)

        auth_line = [line for line in lines if "Authorization" in line]
        l = len(auth_line)
        if not l:
            auth_b64 = None
        else:
            if debug and debug_flag:
                print auth_line[0].split()[2]
            auth_b64 = auth_line[0].split()[2]

        client_data = "\r\n".join(lines) + '\r\n\r\n'

        return {
            "auth_b64": auth_b64,
            "protocol": protocol,
            "method": first_line_tokens[0],
            "server_port": server_port,
            "server_url": server_url,
            "total_url": url,
            "client_data": client_data,
        }

    except Exception as err:
        print "Wrong url"
        print err
        return None


def modify_cache(details):
    lines = details["client_data"].splitlines()
    l = len(lines)
    while True:
        if lines[l-1] != '':
            break
        else:
            lines.remove('')
            l = len(lines)

    header = "If-Modified-Since: " + time.strftime("%a %b %d %H:%M:%S %Y", details["last_mtime"])
    lines.append(header)
    details["client_data"] = "\r\n".join(lines) + "\r\n\r\n"
    return details


def is_blocked(client_socket, client_addr, details):
    fileurl = details["server_url"] + ":"
    fileurl = fileurl + str(details["server_port"])
    if debug and debug_flag:
        print fileurl
    if not fileurl in blocked:
        return False

    login = details["auth_b64"] 
    if debug and debug_flag:
        print login   
    if not login:
        return True
    if login in admins:
        return False

    return True


def get_request_handler(client_socket, client_addr, details):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if debug and debug_flag:
            print server_socket

        server_socket.connect((details["server_url"], details["server_port"]))
        server_socket.send(details["client_data"])

        reply = server_socket.recv(4096)
        if debug and debug_flag:
            print len(reply), reply

        if details["last_mtime"] and "304 Not Modified" in reply:
            acquire_lock(details["total_url"])
            f = open(details["cache_path"], 'rb')
            chunk = f.read(4096)
            while True:
                if not chunk:
                    break
                else:
                    client_socket.send(chunk)
                    chunk = f.read(4096)
            f.close()
            release_lock(details["total_url"])
            print "returning cached file %s to %s" % (details["cache_path"], str(client_addr))

        else:
            if details["do_cache"]:
                remove_from_cache(details["total_url"])
                acquire_lock(details["total_url"])
                f = open(details["cache_path"], "w+")
                while True:
                    if not len(reply):
                        break
                    else:
                        client_socket.send(reply)
                        f.write(reply)
                        reply = server_socket.recv(4096)
                    if debug and debug_flag:
                        print len(reply), reply
                f.close()
                release_lock(details["total_url"])
                print "caching file while serving %s to %s" % (details["cache_path"], str(client_addr))
                client_socket.send("\r\n\r\n")
            else:
                while True:
                    if not len(reply):
                        break
                    else:
                        client_socket.send(reply)
                        reply = server_socket.recv(4096)
                        if debug and debug_flag:
                            print len(reply), reply
                print "without caching serving %s to %s" % (details["cache_path"], str(client_addr))
                client_socket.send("\r\n\r\n")

        server_socket.close()
        client_socket.close()
        return

    except Exception as err:
        print err
        server_socket.close()
        client_socket.close()
        return


def post_request_handler(client_socket, client_addr, details):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if debug and debug_flag:
            print server_socket

        server_socket.connect((details["server_url"], details["server_port"]))
        server_socket.send(details["client_data"])

        reply = server_socket.recv(4096)
        while True:
            if not len(reply):
                break
            else:
                client_socket.send(reply)
                reply = server_socket.recv(4096)

        server_socket.close()
        client_socket.close()
        return

    except Exception as err:
        print err
        server_socket.close()
        client_socket.close()
        return


def request_handler(client_socket, client_addr, client_data):
    details = parse_details(client_addr, client_data)

    if not details:
        client_socket.close()
        print "no details given"
        return

    blocked = is_blocked(client_socket, client_addr, details)

    if blocked:
        print "Block status : ", blocked
        client_socket.send("Blacklisted site\r\n")

    if details["method"] == "POST":
        post_request_handler(client_socket, client_addr, details)

    if details["method"] == "GET":
        details = access_cache(client_addr, details)
        if debug and debug_flag:
            print details
        if details["last_mtime"]:
            details = modify_cache(details)
            if debug and debug_flag:
                print details
        get_request_handler(client_socket, client_addr, details)

    print client_addr, "closed"
    print
    client_socket.close()


logs = {}
locks = {}

try:
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if debug and debug_flag:
        print proxy_socket
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind(('', proxy_port))

    print "Proxy server on %s port %s .." % (str(proxy_socket.getsockname()[0]), str(proxy_socket.getsockname()[1]))

    proxy_socket.listen(10)
    print "Maximum number of clients : %s" % str(10)

except Exception as err:
    print "Error in starting proxy server .."
    proxy_socket.close()
    print err
    raise SystemExit


while True:
    try:
        client_socket, client_addr = proxy_socket.accept()
        print
        client_data = client_socket.recv(4096)
        thread.start_new_thread(request_handler, (client_socket, client_addr, client_data))
        print "%s --- [%s] \"%s\"" % (str(client_addr), str(datetime.datetime.now()), client_data.splitlines()[0])

    except KeyboardInterrupt:
        print "\nClosing Proxy server .."
        proxy_socket.close()
        client_socket.close()
        break
