# 📺 select-freeboxos-sbc-vm v3.0.1

> 📡 Turn your Freebox into an automated recording system
> 🤖 Automatically schedule TV recordings via Freebox OS (dedicated machine)

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Linux-green)
![Environment](https://img.shields.io/badge/Env-SBC%20%7C%20VM-blue)
![Architecture](https://img.shields.io/badge/ARM%20%7C%20x86-orange)
![Status](https://img.shields.io/badge/Status-Active-success)
![Self-hosted](https://img.shields.io/badge/Self--Hosted-Yes-blueviolet)
![Dependency](https://img.shields.io/badge/Requires-Freebox%20OS-lightgrey)

---

## 🍿 How TV Select works

TV Select turns TV into a **personal discovery engine**.

You define what you care about:

* a documentary about wine 🍷
* a history episode 🏛️
* a space report 🚀
* that rare movie you couldn’t find anywhere 🎬
* a tennis documentary your son will love 🎾

Then the system works for you:

1. 🔍 Your searches are analyzed
2. 🧠 TV programs are continuously scanned
3. 🎯 When a match is found:

   * 📧 You receive a notification
   * 📼 A recording is triggered automatically

👉 No manual searching. No scheduling.

---

## 📖 TV Select Ecosystem

This project is part of the **TV Select ecosystem**.

👉 Overview & setup guide:

[![TV Select Ecosystem](https://img.shields.io/badge/TV%20Select-Ecosystem-blue)](https://github.com/tv-select)

## 📡 About select-freeboxos-sbc-vm

select-freeboxos-sbc-vm automatically **schedules recordings in Freebox OS**.

👉 Unlike `select-freeboxos`:

- Runs on a **dedicated machine (SBC / VM)**
- Ensures continuous execution
- Avoids missing recordings

👉 The Freebox handles the actual recording.

---

## ⚡ Key features

- 📡 Automatic recording scheduling via Freebox OS
- 💾 Record directly on Freebox internal or USB storage
- 🤖 Browser automation (Selenium)
- 🔄 Continuous execution (no manual runs required)
- ⚙️ Fully automated via cron jobs

---

## 🧩 How it works

Search → Match → Schedule (Freebox OS) → Record → Watch

---

## 🏠 Freebox OS integration

This application uses the **recording feature of Freebox OS**.

- Recordings are stored on the Freebox
- No local video storage required
- Works with a dedicated always-on machine

💡 Ideal setup:

- SBC (Raspberry Pi, ARM board)
- Virtual Machine (Freebox Delta / Ultra)

---

## 📁 Output

Videos are stored directly on your Freebox.

Accessible via:

- Freebox OS interface
- Network shares (SMB)
- Connected devices (TV, media players)

---

## ⚡ Installation

### Requirements

- Linux (Debian/Ubuntu recommended)
- Python 3.9+
- Firefox (installed automatically)
- Freebox OS (version ≥ 4.7)
- Account on https://www.media-select.fr

---

### Install dependencies

sudo apt update && sudo apt install wget unzip pass

---

### Download

cd ~
wget https://github.com/mediaselect/select-freeboxos-sbc-vm/archive/refs/tags/i3.0.0.zip -O install_freebox.zip

unzip install_freebox.zip
rm -rf install-select-freeboxos-sbc-vm-3.0.0
mv select-freeboxos-sbc-vm-i3.0.0 install-select-freeboxos-sbc-vm-3.0.0
rm install_freebox.zip

---

### Install

cd install-select-freeboxos-sbc-vm-3.0.0
sudo ./install.sh

---

### Setup environment

cd ~/.local/share/select_freeboxos

virtualenv -p python3 .venv
source .venv/bin/activate
pip install -r ~/select-freeboxos/requirements.txt

---

### Install and start

cd ~/select-freeboxos
source ~/.local/share/select_freeboxos/.venv/bin/activate
python3 install.py

---

## 🔐 Configuration

During setup:

- Enter your Freebox OS admin password
- Enter your MEDIA-select credentials

👉 Credentials are only used locally to interact with your Freebox.

---

## 🔐 Security

This application interacts with **Freebox OS using your admin credentials**.

### 🟢 Local usage (required)

- The SBC (Raspberry Pi, ARM board) or Virtual Machine must be connected to the **same local network (LAN)** as the Freebox
- The application connects to the Freebox using local addresses (e.g. `192.168.1.254` or `mafreebox.freebox.fr`)
- This is the **intended and safe usage**

### 🔴 Remote usage (unsupported and unsafe)

- This application does **not support HTTPS connections**
- It relies on **local network access only**, and will not work correctly from outside the LAN
- If forced to run remotely, credentials may be exposed over HTTP

⚠️ Remote usage is **unsupported and strongly discouraged**.

---

💡 For best security and reliability, run this application on a device that stays on your home network (24/7 recommended).

## ⏳ What to expect

- ❌ No immediate results
- ⏳ Wait for matches
- 🎯 Recordings are scheduled automatically
- 📼 Videos are recorded by the Freebox

---

## 🤔 When should you use select-freeboxos-sbc-vm?

Use this version if:

- you have a Freebox
- you run a dedicated machine (SBC / VM)
- you want a fully automated setup (no manual execution)
- you want to avoid missing recordings

---

## ⚠️ Limitations

- Requires Freebox OS
- Relies on browser automation (Selenium)
- Requires a continuously running machine
- Depends on Firefox + geckodriver compatibility

---

## ⭐ Support

If you like this project:

- ⭐ Star it
- 🔁 Share it
- 🧠 Use it

---

## ⚠️ Disclaimer

For personal use only.
