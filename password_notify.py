#!/usr/bin/env python3
import os
import json
import smtplib
import ldap3
import datetime
import sys
import logging
import pytz
from email.mime.text import MIMEText

log_directory = "/var/log/password_notify"
os.makedirs(log_directory, exist_ok=True)

logging.basicConfig(
    filename=f"{log_directory}/password_notify.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

CONFIG_PATH = "/etc/password_notify/config.json"
LAST_NOTIFIED_FILE = "/var/log/password_notify/last_notified.json"
DAYS_BEFORE_EXPIRATION = 7

logging.info("[INFO] Загружаем конфиг...")
try:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    logging.info("[INFO] Конфигурация загружена успешно")
except FileNotFoundError:
    logging.error(f"[ERROR] Не найден конфиг: {CONFIG_PATH}")
    sys.exit(1)

LDAP_SERVER = config["ldap_server"]
LDAP_USER = config["ldap_user"]
LDAP_PASSWORD = config["ldap_password"]
BASE_DN = config["base_dn"]
EMAIL_SERVER = config["email_server"]
EMAIL_SENDER = config["email_sender"]
LDAP_CA_CERT = config.get("ldap_ca_cert", None)

def windows_time_to_datetime(windows_time):
    return datetime.datetime(1601, 1, 1) + datetime.timedelta(seconds=windows_time / 10000000)

def load_last_notified():
    if os.path.exists(LAST_NOTIFIED_FILE):
        with open(LAST_NOTIFIED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_last_notified(data):
    with open(LAST_NOTIFIED_FILE, 'w') as f:
        json.dump(data, f)

logging.info("[INFO] Подключение к LDAPS...")
try:
    server = ldap3.Server(
        LDAP_SERVER,
        use_ssl=True,
        tls=ldap3.Tls(ca_certs_file=LDAP_CA_CERT) if LDAP_CA_CERT else None
    )
    conn = ldap3.Connection(server, user=LDAP_USER, password=LDAP_PASSWORD, auto_bind=True)
    logging.info("[OK] Подключение к LDAP успешно.")
except Exception as e:
    logging.error(f"[ERROR] Ошибка подключения к LDAPS: {e}")
    sys.exit(1)

logging.info("[INFO] Проверяем сроки действия паролей...")
try:
    conn.search(BASE_DN, "(objectClass=user)", attributes=['sAMAccountName', 'pwdLastSet', 'mail', 'givenName', 'sn'])
except Exception as e:
    logging.error(f"[ERROR] Ошибка поиска: {e}")
    sys.exit(1)

now = datetime.datetime.now(pytz.utc)
last_notified = load_last_notified()

for entry in conn.entries:
    try:
        user_id = entry.sAMAccountName.value
        pwd_last_set = entry.pwdLastSet.value
        if not isinstance(pwd_last_set, datetime.datetime):
            pwd_last_set = windows_time_to_datetime(int(pwd_last_set))
        if pwd_last_set.tzinfo is None:
            pwd_last_set = pytz.utc.localize(pwd_last_set)

        password_expiry = pwd_last_set + datetime.timedelta(days=90)
        days_left = (password_expiry - now).days
        logging.info(f"[INFO] Пароль пользователя {user_id} истечет через {days_left} дней.")

        if days_left <= DAYS_BEFORE_EXPIRATION:
            first_name = entry.givenName.value if hasattr(entry, 'givenName') else 'Пользователь'
            last_name = entry.sn.value if hasattr(entry, 'sn') else ''
            full_name = f"{first_name} {last_name}".strip()

            if hasattr(entry, 'mail') and entry.mail:
                email_to = entry.mail.value
                if user_id not in last_notified or last_notified[user_id] != now.date().isoformat():
                    msg = MIMEText(
                        f"Уважаемый {full_name},\n\nВаш пароль истечет через {days_left} дней. "
                        f"Пожалуйста, обновите его своевременно."
                    )
                    msg['From'] = EMAIL_SENDER
                    msg['To'] = email_to
                    msg['Subject'] = 'Уведомление об истечении пароля'

                    try:
                        with smtplib.SMTP(EMAIL_SERVER) as server:
                            server.sendmail(EMAIL_SENDER, email_to, msg.as_string())
                            logging.info(f"[INFO] Уведомление отправлено {full_name} <{email_to}>.")
                        last_notified[user_id] = now.date().isoformat()
                    except Exception as e:
                        logging.error(f"[ERROR] Ошибка отправки письма: {e}")
                else:
                    logging.info(f"[INFO] Уже отправлено уведомление {user_id} сегодня.")
            else:
                logging.warning(f"[WARNING] У пользователя {user_id} нет email.")
        else:
            logging.info(f"[INFO] До истечения пароля пользователя {user_id} > {DAYS_BEFORE_EXPIRATION} дней.")
    except Exception as e:
        logging.error(f"[ERROR] Ошибка обработки {entry}: {e}")

save_last_notified(last_notified)
logging.info("[INFO] Обработка завершена.")
