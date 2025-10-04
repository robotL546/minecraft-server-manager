import sys, os, subprocess, threading, queue, time, glob, shutil, re, requests
from PyQt5 import QtWidgets, QtGui, QtCore

# Constants
BASE_FOLDER = "minecraft_servers"
JAR_URL = "https://fill-data.papermc.io/v1/objects/8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e/paper-1.21.8-60.jar"
JAR_NAME = "paper-1.21.5-103.jar"

# Ensure server base folder exists
os.makedirs(BASE_FOLDER, exist_ok=True)

# Process registry
server_processes = {}   # name -> {proc, thread, queue}

ANSI_RE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
MC_FMT_RE = re.compile(r'§[0-9A-FK-ORa-fk-or]', re.IGNORECASE)


def clean_line(s):
    return MC_FMT_RE.sub('', ANSI_RE.sub('', s))


def find_server_jar_absolute(path):
    pref = os.path.join(path, JAR_NAME)
    if os.path.exists(pref) and os.path.getsize(pref) > 0:
        return os.path.abspath(pref)
    jars = glob.glob(os.path.join(path, "*.jar"))
    if not jars:
        return None
    for j in jars:
        if os.path.basename(j).lower().startswith("paper") and os.path.getsize(j) > 0:
            return os.path.abspath(j)
    return os.path.abspath(jars[0])


def download_jar(dest):
    try:
        tmp = os.path.join(dest, JAR_NAME + ".part")
        out = os.path.join(dest, JAR_NAME)
        r = requests.get(JAR_URL, stream=True, timeout=30)
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for ch in r.iter_content(8192):
                if ch:
                    f.write(ch)
        os.replace(tmp, out)
        return True, "downloaded"
    except Exception as e:
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False, str(e)


def start_server_background(name, log_callback):
    path = os.path.join(BASE_FOLDER, name)
    eula = os.path.join(path, "eula.txt")
    if not os.path.exists(eula):
        return False, "EULA not accepted"
    jar = find_server_jar_absolute(path)
    if not jar:
        return False, "No jar found"
    java_exec = shutil.which("java")
    if not java_exec:
        return False, "Java not installed"
    cmd = [java_exec, "-Xmx1G", "-Xms1G", "-jar", jar, "nogui"]
    try:
        proc = subprocess.Popen(cmd, cwd=path, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
    except Exception as e:
        return False, str(e)

    q = queue.Queue()

    def reader():
        try:
            for ln in proc.stdout:
                cleaned = clean_line(ln)
                q.put(cleaned)
                log_callback(cleaned)
        except Exception as e:
            q.put(f"[ERROR] reader: {e}\n")

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    server_processes[name] = {"proc": proc, "thread": t, "queue": q}
    return True, "started"


def stop_server(name):
    entry = server_processes.get(name)
    if not entry or not entry.get("proc"):
        return False, "Not running"
    proc = entry["proc"]
    try:
        if proc.stdin:
            proc.stdin.write("stop\n")
            proc.stdin.flush()
    except Exception:
        pass
    waited = 0.0
    while proc.poll() is None and waited < 5.0:
        time.sleep(0.2)
        waited += 0.2
    if proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    return True, "stopping"


class ManagerApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Server Manager")
        self.resize(1000, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)

        # Left panel
        left = QtWidgets.QVBoxLayout()
        layout.addLayout(left, 2)

        self.server_list = QtWidgets.QListWidget()
        left.addWidget(self.server_list)

        self.create_btn = QtWidgets.QPushButton("Create Server")
        self.eula_btn = QtWidgets.QPushButton("Accept EULA")
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        left.addWidget(self.create_btn)
        left.addWidget(self.eula_btn)
        left.addWidget(self.start_btn)
        left.addWidget(self.stop_btn)

        left.addStretch(1)

        # Right panel
        right = QtWidgets.QVBoxLayout()
        layout.addLayout(right, 5)

        self.log_view = QtWidgets.QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QtGui.QFont("Consolas", 10))
        self.log_view.setStyleSheet("background:black; color:lime;")
        right.addWidget(self.log_view, 8)

        cmd_layout = QtWidgets.QHBoxLayout()
        self.cmd_input = QtWidgets.QLineEdit()
        self.cmd_send = QtWidgets.QPushButton("Send")
        cmd_layout.addWidget(self.cmd_input, 5)
        cmd_layout.addWidget(self.cmd_send, 1)
        right.addLayout(cmd_layout)

        self.status = self.statusBar()

        # Connections
        self.create_btn.clicked.connect(self.create_server)
        self.eula_btn.clicked.connect(self.accept_eula)
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)
        self.cmd_send.clicked.connect(self.send_command)

        # Ensure base folder exists and load servers
        os.makedirs(BASE_FOLDER, exist_ok=True)
        self.refresh_servers()

    def refresh_servers(self):
        self.server_list.clear()
        try:
            servers = sorted(
                [d for d in os.listdir(BASE_FOLDER)
                 if os.path.isdir(os.path.join(BASE_FOLDER, d)) and d.startswith("server")]
            )
            self.server_list.addItems(servers)
            self.status.showMessage(f"Loaded {len(servers)} servers.")
        except Exception as e:
            self.status.showMessage(f"Error loading servers: {e}")

    def create_server(self):
        try:
            existing = sorted([d for d in os.listdir(BASE_FOLDER) if d.startswith("server")])
            idx = len(existing) + 1
            name = f"server{idx}"
            path = os.path.join(BASE_FOLDER, name)
            os.makedirs(path, exist_ok=True)
            ok, msg = download_jar(path)
            if ok:
                QtWidgets.QMessageBox.information(self, "Created", f"{name} created")
            else:
                QtWidgets.QMessageBox.warning(self, "Error", msg)
            self.refresh_servers()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def accept_eula(self):
        name = self.current_server()
        if not name:
            return
        try:
            with open(os.path.join(BASE_FOLDER, name, "eula.txt"), "w", encoding="utf-8") as f:
                f.write("eula=true\n")
            QtWidgets.QMessageBox.information(self, "EULA", "Accepted for " + name)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def start_server(self):
        name = self.current_server()
        if not name:
            return
        def log_callback(line):
            self.log_view.append(line)
        ok, msg = start_server_background(name, log_callback)
        if ok:
            self.status.showMessage(f"{name} started")
        else:
            QtWidgets.QMessageBox.warning(self, "Start failed", msg)

    def stop_server(self):
        name = self.current_server()
        if not name:
            return
        ok, msg = stop_server(name)
        self.status.showMessage(f"{name}: {msg}")

    def send_command(self):
        name = self.current_server()
        if not name:
            return
        entry = server_processes.get(name)
        if not entry or not entry.get("proc"):
            QtWidgets.QMessageBox.warning(self, "Not running", "Server is not running")
            return
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        try:
            proc = entry["proc"]
            if proc.stdin:
                proc.stdin.write(cmd + "\n")
                proc.stdin.flush()
            self.log_view.append(f"> {cmd}")
            self.cmd_input.clear()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def current_server(self):
        item = self.server_list.currentItem()
        if not item:
            QtWidgets.QMessageBox.warning(self, "Select", "Select a server first")
            return None
        return item.text()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = ManagerApp()
    win.show()
    sys.exit(app.exec_())
