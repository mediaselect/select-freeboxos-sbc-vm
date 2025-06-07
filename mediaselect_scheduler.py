import json
import keyring
import shutil
import sentry_sdk
import sys

import logging
import os
import requests
import subprocess
import tempfile
import time

from datetime import datetime, timedelta
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

user = os.getenv("USER")

sys.path.append(f"/home/{user}/.config/select_freeboxos")

from config import (
    MEDIA_SELECT_TITLES,
    MAX_SIM_RECORDINGS,
    SENTRY_MONITORING_SDK,
)

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


def cancel_record():
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
            logging.error(
                f"Attempt {attempt + 1}/{retries}: Le bouton programmer un enregistrement n'a pas été trouvé."
            )
            sleep(delay)
    logging.error(
        "Impossible de trouver le bouton programmer un enregistrement après plusieurs tentatives."
    )
    driver.quit()
    return "to_continue"

if SENTRY_MONITORING_SDK:
    sentry_sdk.init(
        dsn="https://085eb844a807c3c997195cf7cd60a5a3@o4508778574381056.ingest.de.sentry.io/4508778965106768",
        traces_sample_rate=0,
    )
    if sentry_sdk.Hub.current.client and sentry_sdk.Hub.current.client.options.get("traces_sample_rate", 0) > 0:
        sentry_sdk.profiler.start_profiler()


log_file = f"/home/{user}/.local/share/select_freeboxos/logs/select_freeboxos.log"
max_bytes = 10 * 1024 * 1024  # 10 MB
backup_count = 5

log_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
log_format = '%(asctime)s %(levelname)s %(message)s'
log_datefmt = '%d-%m-%Y %H:%M:%S'
formatter = logging.Formatter(log_format, log_datefmt)

log_handler.setFormatter(formatter)

logger = logging.getLogger("module_freeboxos")
logger.addHandler(log_handler)

sentry_handler = logging.StreamHandler()
sentry_handler.setLevel(logging.WARNING)

logger.addHandler(sentry_handler)
logger.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO,
                    format=log_format,
                    datefmt=log_datefmt,
                    handlers=[log_handler, sentry_handler])

OUTPUT_FILE = os.path.expanduser("~/.local/share/select_freeboxos/info_progs.json")
API_URL = "https://www.media-select.fr/api/v1/progfree"
CONFIG_PY_FILE = os.path.expanduser("~/.config/select_freeboxos/config.py")


def get_pass_entry(entry_name):
    """Retrieve credentials from pass."""
    try:
        result = subprocess.run(["pass", entry_name], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        logging.error(f"Error: Unable to retrieve {entry_name} from pass.")
        return None

def get_time_from_config():
    """Extracts CURL_HOUR and CURL_MINUTE from config.py."""
    if not os.path.isfile(CONFIG_PY_FILE):
        logging.error("Error: Unable to retrieve scheduled hour from config file.")
        return None, None

    with open(CONFIG_PY_FILE, "r") as f:
        config_content = f.read()

    hour = next((line.split("=")[1].strip() for line in config_content.splitlines() if "CURL_HOUR" in line), None)
    minute = next((line.split("=")[1].strip() for line in config_content.splitlines() if "CURL_MINUTE" in line), None)

    if hour and minute:
        return f"{int(hour):02d}", f"{int(minute):02d}"

    logging.error("Error: Could not extract CURL_HOUR or CURL_MINUTE from config.")
    return None, None

def run_scheduled_task(username, password):
    """Run the scheduled API request securely using requests."""
    logging.info("Running scheduled task.")

    try:
        response = requests.get(API_URL, auth=(username, password), headers={"Accept": "application/json; indent=4"})
        response.raise_for_status()  # Raise an error for HTTP failures

        with open(OUTPUT_FILE, "w") as f:
            f.write(response.text)

        logging.info("Task completed successfully.")

    except requests.RequestException as e:
        logging.error(f"API request failed: {e}")

if __name__ == "__main__":
    username = get_pass_entry("media-select/email")
    password = get_pass_entry("media-select/password")

    FREEBOX_SERVER_IP = get_pass_entry("freeboxos/username")
    ADMIN_PASSWORD = get_pass_entry("freeboxos/password")

    if not username or not password or not FREEBOX_SERVER_IP or not ADMIN_PASSWORD:
        logging.error("Error: Missing credentials.")
        exit(1)

    last_config_check = time.time()
    curl_hour, curl_minute = get_time_from_config()

    while True:
        if time.time() - last_config_check >= 3600:
            curl_hour, curl_minute = get_time_from_config()
            last_config_check = time.time()

        current_time = time.strftime("%H:%M")
        if current_time == f"{curl_hour}:{curl_minute}":
            run_scheduled_task(username, password)
            time.sleep(61)

            try:
                with open(
                    "/home/" + user + "/.local/share/select_freeboxos/info_progs.json", "r"
                ) as jsonfile:
                    data = json.load(jsonfile)
            except FileNotFoundError:
                logging.error(
                    "No info_progs.json file. Need to check curl command or "
                    "internet connection. Exit programme."
                )
                continue
            except json.JSONDecodeError:
                logging.error(
                    "Invalid JSON data in info_progs.json file. The file may be empty or corrupted."
                )
                continue

            if len(data) == 0:
                src_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "info_progs.json")
                dst_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "info_progs_last.json")
                shutil.copy(src_file, dst_file)
                logging.info("No data to record programmes. Exit programme.")
                continue

            if is_snap_installed() and is_firefox_snap():
                service = Service(executable_path="/snap/bin/firefox.geckodriver")
            else:
                service = Service(executable_path="/home/" + user + "/.local/share/select_freeboxos/geckodriver")

            options = webdriver.FirefoxOptions()
            options.add_argument("start-maximized")
            options.add_argument("--headless")

            if is_firefox_esr_installed():
                options.binary_location = "/usr/bin/firefox-esr"

            try:
                with webdriver.Firefox(service=service, options=options) as driver:
                    try:
                        driver.get("http://" + FREEBOX_SERVER_IP + "/login.php#Fbx.os.app.pvr.app")
                        sleep(8)
                    except WebDriverException as e:
                        if 'net::ERR_ADDRESS_UNREACHABLE' in e.msg:
                            logging.error(
                                "The programme cannot reach the address " + FREEBOX_SERVER_IP + " . Exit programme."
                            )
                            driver.quit()
                            continue
                        else:
                            logging.error("A WebDriverException occurred. Exiting the program.")
                            logging.error(f"Exception message: {e.msg}")
                            logging.error(f"Exception stack trace: {e.stacktrace}")
                            logging.error(f"Exception screenshot: {e.screen if hasattr(e, 'screen') else 'N/A'}")
                            logging.error(f"Exception log: {e.log if hasattr(e, 'log') else 'N/A'}")
                            driver.quit()
                            continue

                    try:
                        login = driver.find_element("id", "fbx-password")
                    except Exception as e:
                        logging.error(
                            "Cannot connect to Freebox OS. Exit programme.", exc_info=True
                        )
                        driver.quit()
                        continue
                    sleep(1)
                    login.click()
                    sleep(1)
                    login.send_keys(ADMIN_PASSWORD)
                    sleep(1)
                    login.send_keys(Keys.RETURN)
                    sleep(10)

                    try:
                        invalid_password = driver.find_element(
                            By.XPATH, "//div[contains(text(), 'Identifiants invalides')]"
                        )
                        logging.error(
                            "Le mot de passe administrateur de la Freebox est invalide. "
                            "La programmation des enregistrements n'a pas "
                            "pu être réalisée. Merci de vérifier le mot de passe."
                        )
                        driver.quit()
                        continue
                    except NoSuchElementException:
                        pass


                    try:
                        with open(
                            "/home/" + user + "/.local/share/select_freeboxos/info_progs_last.json", "r"
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
                    to_continue = False

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
                            logging.error(
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
                            if programmer_enregistrements == "to_continue":
                                to_continue = True
                                break
                            sleep(1)
                            try:
                                programmer_enregistrements.click()
                            except ElementClickInterceptedException as e:
                                logging.error("A ElementClickInterceptedException occurred.")
                                logging.error(f"Exception message: {e.msg}")
                                logging.error(f"Exception stack trace: {e.stacktrace}")
                                logging.error(
                                    "Impossible de programmer les enregistrements. "
                                    "Une fenêtre d'information empêche probablement "
                                    "de pouvoir clicker sur le bouton programmer un "
                                    "enregistrement."
                                )
                                driver.quit()
                                to_continue = True
                                break
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
                                    logging.error(
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
                                xpath = f"//li[contains(text(), '{text_to_click}')]"
                                day_click = driver.find_element(By.XPATH, xpath)
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
                                        logging.error("Timeout: The input field did not update to the correct time.")

                                    actual_start = start_time.get_attribute("value")

                                    if actual_start == start_hour + ":" + start_minute:
                                        break
                                    loop_counter += 1
                                    if loop_counter > 4:
                                        logging.error(
                                            f"Impossible de saisir l'heure de début pour le programme {video['title']}. Le programme ne sera pas enregistré."
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
                                        logging.error("Timeout: The input field did not update to the correct time.")

                                    actual_end = end_time.get_attribute("value")

                                    if actual_end == end_hour + ":" + end_minute:
                                        break
                                    loop_counter += 1
                                    if loop_counter > 4:
                                        logging.error(
                                            f"Impossible de saisir l'heure de fin pour le programme {video['title']}. Le programme ne sera pas enregistré."
                                        )
                                        to_cancel = True
                                        break
                                if to_cancel:
                                    cancel_record()
                                else:
                                    sleep(1)
                                    end_time.send_keys(Keys.RETURN)
                                    sleep(1)
                                    if MEDIA_SELECT_TITLES:
                                        name_prog = driver.find_element("name", "name")
                                        try:
                                            name_prog.clear()
                                            sleep(1)
                                            name_prog.send_keys(video["title"])
                                            sleep(1)
                                        except ElementNotInteractableException:
                                            logging.error(
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
                                        logging.error(
                                            "Une erreur interne de la Freebox est survenue. "
                                            "La programmation des enregistrements n'a pas "
                                            "pu être réalisée. Merci de vérifier si le disque "
                                            "dur n'est pas plein."
                                        )
                                        break
                                    except NoSuchElementException:
                                        pass
                            else:
                                cancel_record()

                    if to_continue:
                        continue

                    sleep(6)
                    driver.quit()

                    src_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "info_progs.json")
                    dst_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "info_progs_last.json")
                    shutil.copy(src_file, dst_file)
            except Exception as e:
                logging.error("An unexpected error occurred:")
                logging.error("Exception: %s", e)
                logging.error("Stack trace:", exc_info=True)


        time.sleep(30)
