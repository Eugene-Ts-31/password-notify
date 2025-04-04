# 🔐 Password Expiry Notification Script

This script connects to an LDAP (LDAPS) directory and notifies users via email when their password is about to expire.

## Features

- Secure LDAPS connection
- Password expiry calculation
- Email notifications with customizable thresholds
- JSON-based config
- Integrated with `systemd` + `systemd.timer`

---

## 🛠 Requirements

- Ubuntu Server 20.04+
- Python 3
- Packages: `ldap3`, `pytz`

```bash
sudo apt install python3 python3-pip
pip3 install ldap3 pytz
```

---

## ⚙ Configuration

1. Create `/etc/password_notify/config.json` based on the template:

```bash
cp config.example.json /etc/password_notify/config.json
```

Edit `config.json` and set:

- `ldap_server`, `ldap_user`, `ldap_password`
- `base_dn`, `email_server`, `email_sender`
- `ldap_ca_cert` (or system default)

---

## 🚀 Usage

Run manually:

```bash
sudo /usr/local/bin/password_notify.py
```

View logs:

```bash
tail -n 50 /var/log/password_notify/password_notify.log
```

---

## 🛎️ Automation (systemd)

### password_notify.service

```ini
[Unit]
Description=Password Expiry Notification Service
After=network.target

[Service]
ExecStart=/usr/local/bin/password_notify.py
User=root
Type=simple

[Install]
WantedBy=multi-user.target
```

### password_notify.timer

```ini
[Unit]
Description=Runs password_notify every hour

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

Enable timer:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now password_notify.timer
```

---

## 📁 Directory Structure

- `/usr/local/bin/password_notify.py` — main script
- `/etc/password_notify/config.json` — configuration file
- `/var/log/password_notify/` — logs and state

---

## 🔒 Security

- NEVER commit `config.json` to public repos.
- Use `.gitignore` to exclude secrets.

---

## 📬 License

MIT License — you are free to use, modify, and distribute.

---
