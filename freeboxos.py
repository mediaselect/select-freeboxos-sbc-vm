import json
import keyring
import logging
import os
import shutil
import sentry_sdk
import sys
import tempfile
import re

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from time import sleep
from logging.handlers import RotatingFileHandler
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    WebDriverException,
    ElementNotInteractableException,
    ElementClickInterceptedException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from sentry_sdk.integrations.logging import LoggingIntegration

from channels_free import CHANNELS_FREE
from module_freeboxos import is_snap_installed, is_firefox_snap, is_firefox_esr_installed
from security_sanitizer import global_sanitizer, scrub_event

def get_validated_user():
    """Securely get and validate the USER environment variable."""
    user = os.getenv("USER")
    if not user:
        raise ValueError("USER environment variable is not set")

    if not re.match(r'^[a-zA-Z0-9_-]+$', user):
        raise ValueError(f"Invalid USER environment variable: contains unsafe characters")

    home_path = Path.home()
    expected_home = Path(f"/home/{user}")

    if home_path != expected_home:
        user = home_path.name
        if not re.match(r'^[a-zA-Z0-9_-]+$', user):
            raise ValueError("Home directory name contains unsafe characters")

    return user

try:
    user = get_validated_user()
except ValueError as e:
    print(f"SECURITY ERROR: {e}", file=sys.stderr)
    sys.exit(1)

BASE_DIR = Path.home() / ".local" / "share" / "select_freeboxos"
LOG_FILE = BASE_DIR / "logs" / "select_freeboxos.log"
INFO_PROGS_FILE = BASE_DIR / "info_progs.json"
INFO_PROGS_LAST_FILE = BASE_DIR / "info_progs_last.json"
GECKODRIVER_PATH = BASE_DIR / "geckodriver"

def validate_path_safety(path, base_dir):
    """Ensure path doesn't escape base directory via traversal attacks."""
    try:
        resolved_path = path.resolve()
        resolved_base = base_dir.resolve()
        resolved_path.relative_to(resolved_base)
        return resolved_path
    except (ValueError, RuntimeError):
        raise ValueError(f"Path {path} attempts to escape base directory {base_dir}")

try:
    validate_path_safety(BASE_DIR, Path.home())
    validate_path_safety(LOG_FILE, BASE_DIR)
except ValueError as e:
    print(f"SECURITY ERROR: {e}", file=sys.stderr)
    sys.exit(1)

CONFIG_PATH = Path.home() / ".config" / "select_freeboxos" / "config.json"

try:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    print("ERROR: config.json not found", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"ERROR: invalid config.json: {e}", file=sys.stderr)
    sys.exit(1)

try:
    ADMIN_PASSWORD = config["ADMIN_PASSWORD"]
    FREEBOX_SERVER_IP = config["FREEBOX_SERVER_IP"]
    MEDIA_SELECT_TITLES = bool(config["MEDIA_SELECT_TITLES"])
    MAX_SIM_RECORDINGS = int(config["MAX_SIM_RECORDINGS"])
    SENTRY_MONITORING_SDK = bool(config["SENTRY_MONITORING_SDK"])
    CRYPTED_CREDENTIALS = bool(config.get("CRYPTED_CREDENTIALS", False))
    CURL_HOUR = int(config["CURL_HOUR"])
    CURL_MINUTE = int(config["CURL_MINUTE"])
except KeyError as e:
    print(f"ERROR: missing config key: {e}", file=sys.stderr)
    sys.exit(1)

month_names_fr = {
    '01': 'Jan',
    '02': 'Fév',
    '03': 'Mar',
    '04': 'Avr',
    '05': 'Mai',
    '06': 'Juin',
    '07': 'Juil',
    '08': 'Août',
    '09': 'Sept',
    '10': 'Oct',
    '11': 'Nov',
    '12': 'Déc'
}

def translate_month(month_num):
    if month_num in month_names_fr:
        return month_names_fr[month_num]
    else:
        return "Mois invalide"

def cancel_record(driver):
    text_to_click = "Annuler"
    xpath = f"//span[text()='{text_to_click}']"
    cancel = driver.find_element(By.XPATH, xpath)
    cancel.click()
    sleep(5)

def find_element_with_retries(driver, by, value, retries=3, delay=1):
    """Try to find an element with retries."""
    for attempt in range(retries):
        try:
            return driver.find_element(by, value)
        except NoSuchElementException:
            logger.error(
                f"Attempt {attempt + 1}/{retries}: Le bouton programmer un enregistrement n'a pas été trouvé."
            )
            sleep(delay)
    logger.error(
        "Impossible de trouver le bouton programmer un enregistrement après plusieurs tentatives."
    )
    driver.quit()
    exit()

def validate_video_title(title):
    """Validate video title"""
    # Allow most characters but remove potentially dangerous ones
    sanitized_title = re.sub(r'[<>\'"]', '', title)
    if len(sanitized_title) > 200:
        sanitized_title = sanitized_title[:200]

    return sanitized_title

def atomic_file_copy(src, dst):
    """Perform atomic file copy to prevent corruption."""
    src_path = Path(src)
    dst_path = Path(dst)

    validate_path_safety(src_path, BASE_DIR)
    validate_path_safety(dst_path, BASE_DIR)

    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=dst_path.parent,
        delete=False,
        prefix='.tmp_',
        suffix=dst_path.suffix
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        shutil.copy2(src_path, tmp_path)

        if not tmp_path.exists():
            raise IOError("Temporary file was not created")

        tmp_path.replace(dst_path)
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise e

if SENTRY_MONITORING_SDK:
    sentry_sdk.init(
        dsn="https://085eb844a807c3c997195cf7cd60a5a3@o4508778574381056.ingest.de.sentry.io/4508778965106768",
        traces_sample_rate=0,
        send_default_pii=False,
        include_local_variables=False,
        before_send=scrub_event,
    )
    if sentry_sdk.Hub.current.client and sentry_sdk.Hub.current.client.options.get("traces_sample_rate", 0) > 0:
        sentry_sdk.profiler.start_profiler()

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

max_bytes = 10 * 1024 * 1024  # 10 MB
backup_count = 5

log_handler = RotatingFileHandler(str(LOG_FILE), maxBytes=max_bytes, backupCount=backup_count)
log_format = '%(asctime)s %(levelname)s %(message)s'
log_datefmt = '%d-%m-%Y %H:%M:%S'
formatter = logging.Formatter(log_format, log_datefmt)

log_handler.setFormatter(formatter)

logger = logging.getLogger("module_freeboxos")
logger.addHandler(log_handler)

sentry_handler = logging.StreamHandler()
sentry_handler.setLevel(logging.WARNING)

sensitive_filter = global_sanitizer
log_handler.addFilter(sensitive_filter)
sentry_handler.addFilter(sensitive_filter)

sensitive_filter.update_patterns({
    "admin_password": ADMIN_PASSWORD,
    "freebox_ip": FREEBOX_SERVER_IP,
})

logger.addHandler(sentry_handler)
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO,
                    format=log_format,
                    datefmt=log_datefmt,
                    handlers=[log_handler, sentry_handler])

try:
    with open(
        f"/home/{user}/.local/share/select_freeboxos/info_progs.json", "r", encoding='utf-8'
    ) as jsonfile:
        data = json.load(jsonfile)
except FileNotFoundError:
    logger.error(
        "No info_progs.json file. Need to check curl command or "
        "internet connection. Exit programme."
    )
    exit()
except json.JSONDecodeError:
    logger.error(
        "Invalid JSON data in info_progs.json file. The file may be empty or corrupted."
    )
    exit()

if len(data) == 0:
    atomic_file_copy(INFO_PROGS_FILE, INFO_PROGS_LAST_FILE)
    logger.info("No data to record programmes. Exit programme.")
    exit()

if is_snap_installed() and is_firefox_snap():
    service = Service(executable_path="/snap/bin/firefox.geckodriver")
else:
    service = Service(executable_path=f"/home/{user}/.local/share/select_freeboxos/geckodriver")

options = webdriver.FirefoxOptions()
options.add_argument("start-maximized")
options.add_argument("--headless")

if is_firefox_esr_installed():
    options.binary_location = "/usr/bin/firefox-esr"

if CRYPTED_CREDENTIALS:
    try:
        FREEBOX_SERVER_IP = keyring.get_password("freeboxos", "username")
        ADMIN_PASSWORD = keyring.get_password("freeboxos", "password")
        if FREEBOX_SERVER_IP is None:
            logger.error("Failed to retrieve 'username' from keyring for 'freeboxos'.")
            exit(1)
        if ADMIN_PASSWORD is None:
            logger.error("Failed to retrieve 'password' from keyring for 'freeboxos'.")
            exit(1)

        sensitive_filter.update_patterns({
            "admin_password": ADMIN_PASSWORD,
            "freebox_ip": FREEBOX_SERVER_IP,
        })

    except Exception as e:
        logger.exception("An error occurred while retrieving credentials from keyring.")
        exit(1)

try:
    with webdriver.Firefox(service=service, options=options) as driver:
        try:
            driver.get(f"http://{FREEBOX_SERVER_IP}/login.php#Fbx.os.app.pvr.app")
            sleep(8)
        except WebDriverException as e:
            if 'net::ERR_ADDRESS_UNREACHABLE' in e.msg:
                logger.error(
                    f"The programme cannot reach the address {FREEBOX_SERVER_IP} . Exit programme."
                )
                driver.quit()
                exit()
            else:
                logger.error("A WebDriverException occurred. Exiting the program.")
                logger.error(f"Exception type: {type(e).__name__}")
                driver.quit()
                exit()

        try:
            login = driver.find_element("id", "fbx-password")
        except Exception as e:
            logger.error(
                "Cannot connect to Freebox OS. Exit programme.", exc_info=False
            )
            driver.quit()
            exit()
        sleep(1)
        login.click()
        sleep(1)
        login.send_keys(ADMIN_PASSWORD)
        ADMIN_PASSWORD = None
        sleep(1)
        login.send_keys(Keys.RETURN)
        sleep(10)

        try:
            invalid_password = driver.find_element(
                By.XPATH, "//div[contains(text(), 'Identifiants invalides')]"
            )
            logger.error(
                "Le mot de passe administrateur de la Freebox est invalide. "
                "La programmation des enregistrements n'a pas "
                "pu être réalisée. Merci de vérifier le mot de passe."
            )
            driver.quit()
            exit()
        except NoSuchElementException:
            pass


        try:
            with open(
                f"/home/{user}/.local/share/select_freeboxos/info_progs_last.json", "r", encoding='utf-8'
            ) as jsonfile:
                data_last = json.load(jsonfile)
        except FileNotFoundError:
            data_last = []

        starting = []

        for video in data_last:
            start = datetime.strptime(video["start"], "%Y%m%d%H%M").replace(
                tzinfo=ZoneInfo("Europe/Paris")
            )
            end = start + timedelta(seconds=video["duration"])

            starting.append((start, end))

        n = 0
        last_channel = "x/x"
        start_last = None

        for video in data:
            n += 1

            start = datetime.strptime(video["start"], "%Y%m%d%H%M").replace(
                tzinfo=ZoneInfo("Europe/Paris")
            )
            if start_last is not None and start == start_last:
                start += timedelta(minutes=1)

            start_last = start
            start_day = start.strftime("%d")
            start_month = start.strftime("%m")
            start_year = start.strftime("%y")
            start_hour = start.strftime("%H")
            start_minute = start.strftime("%M")

            end = start + timedelta(seconds=video["duration"])
            end_hour = end.strftime("%H")
            end_minute = end.strftime("%M")

            try:
                channel_number = CHANNELS_FREE[video["channel"]]
            except KeyError:
                logger.error(
                    "La chaine " + video["channel"] + " n'est pas "
                    "présente dans le fichier channels_free.py"
                )
                continue

            if len(starting) < MAX_SIM_RECORDINGS:
                starting.append((start, end))
                to_record = True
            else:
                if starting[-MAX_SIM_RECORDINGS][1] < start:
                    starting.append((start, end))
                    to_record = True
                else:
                    to_record = False

            if to_record:
                text_to_click = "Programmer un enregistrement"
                xpath = f"//span[text()='{text_to_click}']"
                programmer_enregistrements = find_element_with_retries(driver, By.XPATH, xpath)
                sleep(1)
                try:
                    programmer_enregistrements.click()
                except ElementClickInterceptedException as e:
                    logger.error("A ElementClickInterceptedException occurred.")
                    logger.error(
                        "Impossible de programmer les enregistrements. "
                        "Une fenêtre d'information empêche probablement "
                        "de pouvoir clicker sur le bouton programmer un "
                        "enregistrement."
                    )
                    driver.quit()
                    exit()
                sleep(3)
                channel_uuid = driver.find_element("name", "channel_uuid")
                sleep(1)
                n = 0
                follow_record = True
                while channel_uuid.get_attribute("value").split("/")[0] != channel_number:
                    channel_uuid.clear()
                    sleep(1)
                    if last_channel.split("/")[0] != channel_number:
                        channel_uuid.send_keys(channel_number)
                    else:
                        channel_uuid.click()
                        sleep(1)
                        channel_uuid.clear()
                        sleep(3)
                        channel_uuid.send_keys(last_channel)
                        sleep(1)
                        channel_uuid.click()
                    sleep(1)
                    channel_uuid.send_keys(Keys.RETURN)
                    sleep(1)
                    last_channel = channel_uuid.get_attribute("value")
                    n += 1
                    if n > 10:
                        logger.error(
                            "Impossible de sélectionner la chaîne. Merci de "
                            "vérifier si la chaine n°" + channel_number + " qui "
                            "correspond à la chaine " + video["channel"] + " "
                            "de MEDIA-select est bien présente dans la liste des "
                            "chaines Freebox. "
                        )
                        follow_record = False
                        break
                if follow_record:
                    date = driver.find_element("name", "date")
                    date.click()
                    sleep(1)
                    text_to_click = start_day + " " + translate_month(start_month)
                    xpath = f"//li[contains(text(), '{text_to_click}') and not(contains(text(), 'TV'))]"
                    try:
                        day_click = driver.find_element(By.XPATH, xpath)
                    except NoSuchElementException as e:
                        logger.error("A NoSuchElementException occurred.")
                        logger.error(
                            "Impossible de trouver la date pour le programme %s. Le "
                            "programme ne sera pas enregistré.",
                            validate_video_title(video['title'])
                        )
                        cancel_record(driver)
                        continue
                    day_click.click()
                    sleep(1)
                    to_cancel = False
                    actual_start = "943463167"
                    loop_counter = 0
                    while True:
                        start_time = driver.find_element("name", "start_time")
                        start_time.clear()
                        sleep(0.5)
                        start_time.send_keys(start_hour + ":" + start_minute)
                        try:
                            WebDriverWait(driver, 10).until(
                                lambda d: start_time.get_attribute("value") == start_hour + ":" + start_minute
                            )
                        except:
                            logger.error("Timeout: The input field did not update to the correct time.")

                        actual_start = start_time.get_attribute("value")

                        if actual_start == start_hour + ":" + start_minute:
                            break
                        loop_counter += 1
                        if loop_counter > 4:
                            logger.error(
                                "Impossible de saisir l'heure de début pour le "
                                "programme %s. Le programme ne sera pas enregistré.",
                                validate_video_title(video['title'])
                            )
                            to_cancel = True
                            break
                    sleep(1)
                    start_time.send_keys(Keys.RETURN)
                    sleep(1)
                    actual_end = "943463167"
                    loop_counter = 0
                    while True:
                        end_time = driver.find_element("name", "end_time")
                        end_time.clear()
                        sleep(0.5)
                        end_time.send_keys(end_hour + ":" + end_minute)
                        try:
                            WebDriverWait(driver, 10).until(
                                lambda d: end_time.get_attribute("value") == end_hour + ":" + end_minute
                            )
                        except:
                            logger.error("Timeout: The input field did not update to the correct time.")

                        actual_end = end_time.get_attribute("value")

                        if actual_end == end_hour + ":" + end_minute:
                            break
                        loop_counter += 1
                        if loop_counter > 4:
                            logger.error(
                                "Impossible de saisir l'heure de fin pour le "
                                "programme %s. Le programme ne sera pas enregistré.",
                                validate_video_title(video['title'])
                            )
                            to_cancel = True
                            break
                    if to_cancel:
                        cancel_record(driver)
                    else:
                        sleep(1)
                        end_time.send_keys(Keys.RETURN)
                        sleep(1)
                        if MEDIA_SELECT_TITLES:
                            name_prog = driver.find_element("name", "name")
                            try:
                                name_prog.clear()
                                sleep(1)
                                name_prog.send_keys(validate_video_title(video["title"]))
                                sleep(1)
                            except ElementNotInteractableException:
                                logger.error(
                                    "Une ElementNotInteractableException est apparue. "
                                    "Le titre de MEDIA select ne sera pas utilisé pour "
                                    "nommer le vidéo."
                                )
                        text_to_click = "Sauvegarder"
                        xpath = f"//span[text()='{text_to_click}']"
                        sauvegarder = driver.find_element(By.XPATH, xpath)
                        sauvegarder.click()
                        sleep(5)
                        try:
                            internal_error = driver.find_element(
                                By.XPATH, "//div[contains(text(), 'Erreur interne')]"
                            )
                            logger.error(
                                "Une erreur interne de la Freebox est survenue. "
                                "La programmation des enregistrements n'a pas "
                                "pu être réalisée. Merci de vérifier si le disque "
                                "dur n'est pas plein."
                            )
                            break
                        except NoSuchElementException:
                            pass
                else:
                    cancel_record(driver)

        sleep(6)
        driver.quit()

        atomic_file_copy(INFO_PROGS_FILE, INFO_PROGS_LAST_FILE)

except Exception as e:
    logger.error("An unexpected error occurred:")
    logger.error("Exception type: %s", type(e).__name__)
    logger.error("Exception message: %s", str(e)[:100])
