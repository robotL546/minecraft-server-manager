# Minecraft Server GUI

A lightweight desktop application to create and manage Minecraft servers with a clean modern interface.  
Built with **Python + PyQt6**, it allows you to easily create new server instances, start/stop them, and view logs in real time.

---

## ✨ Features
- Create and manage multiple Minecraft servers
- Start and stop servers with one click
- Real-time console log viewer
- Send commands directly to the server console
- Modern, lightweight PyQt6 interface
- Simple setup — only Python and Java required

---

## 🚀 Getting Started

### Requirements
- [Python 3.10+](https://www.python.org/downloads/)
- [Java 17+](https://adoptium.net/) (required by modern Minecraft servers)
- Pip packages (see `requirements.txt`)

---

### 🔧 Installation
Clone the repository and install dependencies:

git clone https://github.com/robotL546/minecraft-server-manager.git
cd minecraft-server-manager
pip install -r requirements.txt

---

## 📦 Compiling

You can build the application into a distributable package for **Windows** or **Linux**.

### 🪟 Windows (EXE)
To compile into a standalone `.exe` file:

pip install auto-py-to-exe
auto-py-to-exe

Follow the prompts in the UI to package your script into an `.exe`.

---

### 🐧 Linux (DEB)
To build a `.deb` package on Linux:

pip install py2deb
sudo apt-get install dpkg-dev fakeroot
py2deb myscript.py

This will create a `.deb` file that can be installed on Debian-based systems.

---

## ⚖️ License
This project is licensed under the **MIT License**.  
See the [LICENSE](LICENSE) file for details.

> **Note:** This project is an independent Minecraft server management tool.  
> It is not affiliated with or endorsed by Mojang Studios or Microsoft.
