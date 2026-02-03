import getpass
import json
import keyring
import logging
import os
import random
import readline
import requests
import shutil

from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException

from subprocess import Popen, PIPE, run, CalledProcessError

from module_freeboxos import get_website_title, is_snap_installed, is_firefox_snap, is_firefox_esr_installed

def get_gpg_keys():
    """Lists GPG keys with cryptographic method and key strength."""
    cmd = ["gpg", "--list-keys", "--with-colons"]

    try:
        output = run(cmd, capture_output=True, text=True, check=True).stdout
    except CalledProcessError:
        print("Error retrieving GPG keys.")
        return []

    keys = []
    for line in output.splitlines():
        parts = line.split(":")
        if parts[0] == "pub":  # Public key entry
            key_type = parts[3]  # Algorithm type (1=RSA, 16=ElGamal, 17=DSA, 18=ECDSA, 19=Ed25519, 22=Curve25519)
            key_size = int(parts[2])  # Key length in bits
            key_id = parts[4][-8:]  # Last 8 digits of the key fingerprint

            # Determine key type and strength
            if key_type == "1":
                algo = "RSA"
                secure = key_size >= 4096
            elif key_type == "16":
                algo = "ElGamal"
                secure = False  # Not recommended for password storage
            elif key_type == "17":
                algo = "DSA"
                secure = False  # Deprecated
            elif key_type == "18":
                algo = "ECDSA"
                secure = key_size >= 256  # At least 256 bits
            elif key_type == "19":
                algo = "Ed25519"
                secure = True  # Secure by design
            elif key_type == "22":
                algo = "Curve25519"
                secure = True  # Secure by design
            else:
                algo = f"Unknown ({key_type})"
                secure = False

            if secure:
                keys.append((key_id, algo, key_size))

    return keys


user = os.getenv("USER")

logging.basicConfig(
    filename=f"/home/{user}/.local/share/select_freeboxos/logs/select_freeboxos.log",
    format="%(asctime)s %(levelname)s: %(message)s",
    level=logging.INFO,
)

answers = ["oui", "non"]
opciones = ["1", "2", "3"]
opcion = 5
https = False

print("\nBienvenu dans le programme d'installation pour enregistrer "
      "automatiquement les vidéos qui vous correspondent dans votre "
      "Freebox.\n"
      )

cmd = ["ip", "route", "show", "default"]
ip_ad = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
stdout, stderr = ip_ad.communicate()
FREEBOX_SERVER_IP = stdout.split()[2]

print("\nLe programme a détecté que votre routeur "
        f"a l'adresse IP {FREEBOX_SERVER_IP}\n\nLe programme va "
        "maintenant vérifier si celui-ci est celui de la Freebox server\n")

url = "http://" + FREEBOX_SERVER_IP

title = get_website_title(url)

option = 5
repeat = False
out_prog = "nose"

while title != "Freebox OS":
    print("\nLa connexion à la Freebox Server a échoué.\n\nMerci de vérifier "
            "que vous êtes bien connecté au réseau local de votre Freebox "
            "(cable ethernet ou wifi).")
    if repeat:
        print("\nLe programme a détecté une nouvelle fois que le routeur "
                "est différent de celui de la Freebox server.\n")
    if title is not None:
        print("\nLe programme a détecté comme nom possible de votre "
                "routeur la valeur suivante: " + title + "\n")
    else:
        print("\nLe programme n'a pas détecté le nom de votre routeur.\n")
    if repeat:
        while out_prog.lower() not in answers:
            out_prog = input("Voulez-vous continuer de tenter de vous "
                            "connecter? (repondre par oui ou non): ")
    if out_prog.lower() == "non":
        print('\nSortie du programme.\n')
        exit()

    print("Merci de vérifier que vous êtes bien connecté au réseau local "
            "de votre Freebox serveur. \n")
    while option not in opciones:
        option = input(
            "Après avoir fait vérifier la connexion, vous pouvez choisir une "
            "de ces 3 options pour continuer:\n\n1) Vous n'étiez pas "
            "connecté au réseau local de votre Freebox serveur "
            "précédemment et vous voulez tenter de nouveau de vous "
            "connecter\n\n2) Vous êtiez sûr d'être connecté au réseau "
            "local de votre Freebox serveur. Vous avez vérifié l'adresse "
            "ip de la Freebox server dans la fenêtre 'Paramètres de la "
            "Freebox' après avoir clické sur 'Mode réseau' et celle-ci "
            "est différente de celle découverte par le programme.\n\n3) "
            "Vous voulez utiliser le nom d'hôte mafreebox.freebox.fr qui "
            "fonctionnera sans avoir besoin de vérifier l'adresse IP de "
            "la freebox server. Il faudra cependant veiller à ne pas "
            "utiliser de VPN avec votre box MEDIA-select pour pouvoir vous "
            "connecter.\n\nChoisissez entre 1 et 3: "
        )
    if option == "1":
        cmd = ["ip", "route", "show", "default"]
        ip_ad = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        stdout, stderr = ip_ad.communicate()
        FREEBOX_SERVER_IP = stdout.split()[2]

        print("\nLe programme a détecté que votre routeur "
            f"a l'adresse IP {FREEBOX_SERVER_IP}\n\nLe programme va "
            "maitenant vérifier si celui-ci est celui de la Freebox server\n")
    elif option == "2":
        FREEBOX_SERVER_IP = input(
            "\nVeuillez saisir l'adresse IP de votre Freebox: "
        )
    else:
        FREEBOX_SERVER_IP = "mafreebox.freebox.fr"

    option = "5"

    print("\nNouvelle tentative de connexion à la Freebox:\n\nVeuillez patienter.")
    print("\n---------------------------------------------------------------\n")

    url = "http://" + FREEBOX_SERVER_IP
    title = get_website_title(url)

    repeat = True
    out_prog = "nose"

print("Le programme peut atteindre la page de login de Freebox OS. Il "
    "va maintenant tenter de se connecter à Freebox OS avec votre "
    " mot de passe:")

if is_snap_installed() and is_firefox_snap():
    service = Service(executable_path="/snap/bin/firefox.geckodriver")
else:
    service = Service(executable_path=f"/home/{user}/.local/share/select_freeboxos/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("start-maximized")
options.add_argument("--headless")

if is_firefox_esr_installed():
    options.binary_location = "/usr/bin/firefox-esr"

print("Veuillez patienter\n")

try:
    driver = webdriver.Firefox(service=service, options=options)
except SessionNotCreatedException as e:
    print("A SessionNotCreatedException occured. Exit programme.")
    logging.error(
        "A SessionNotCreatedException occured. Exit programme."
    )
    exit()

try:
    if https:
        driver.get(f"https://{FREEBOX_SERVER_IP}/login.php")
    else:
        driver.get(f"http://{FREEBOX_SERVER_IP}/login.php")
except WebDriverException as e:
    if 'net::ERR_ADDRESS_UNREACHABLE' in e.msg:
        print(f"The programme cannot reach the address {FREEBOX_SERVER_IP} . Exit programme.")
        logging.error(
            f"The programme cannot reach the address {FREEBOX_SERVER_IP} . Exit programme."
        )
        driver.quit()
        exit()
    else:
        print("A WebDriverException occured. Exit programme.")
        logging.error(
            "A WebDriverException occured. Exit programme."
        )
        driver.quit()
        exit()


print("Connexion à la Freebox:\n")

go_on = True
not_connected = True
answer_hide = "maybe"
n = 0

while not_connected:
    if answer_hide.lower() == "oui":
        freebox_os_password = input(
            "\nVeuillez saisir votre mot de passe admin de la Freebox: "
        )
    else:
        freebox_os_password = getpass.getpass(
            "\nVeuillez saisir votre mot de passe admin de la Freebox: "
        )
    print(
        "\nVeuillez patienter pendant la tentative de connexion à "
        "Freebox OS avec votre mot de passe.\n"
    )
    sleep(4)
    login = driver.find_element("id", "fbx-password")
    sleep(1)
    login.clear()
    sleep(1)
    login.click()
    sleep(1)
    login.send_keys(freebox_os_password)
    sleep(1)
    login.send_keys(Keys.RETURN)
    sleep(6)

    try:
        login = driver.find_element("id", "fbx-password")
        try_again = input(
            "\nLe programme install.py n'a pas pu se connecter à Freebox OS car "
            "le mot de passe ne correspond pas à celui enregistré dans "
            "la Freebox.\nVoulez-vous essayer de nouveau?(oui ou non): "
        )
        if try_again.lower() == "oui":
            if answer_hide.lower() != "oui":
                while answer_hide.lower() not in answers:
                    answer_hide = input(
                        "\nVoulez-vous afficher le mot de passe que vous saisissez "
                        "pour que cela soit plus facile? (répondre par oui ou non): "
                    )
            n += 1
            if n > 6:
                print(
                    "\nImpossible de se connecter à Freebox OS avec ce mot de passe. "
                    "Veuillez vérifier votre mot de passe de connexion admin en vous "
                    "connectant à l'adresse http://mafreebox.freebox.fr/login.php puis "
                    "relancez le programme install.py. "
                )
                driver.quit()
                go_on = False
                break
        else:
            driver.quit()
            go_on = False
            break
    except:
        print("Le mot de passe correspond bien à votre compte admin Freebox OS")
        not_connected = False
        sleep(2)
        driver.quit()

max_sim_recordings = 0
title_answer = "no_se"
change_max_rec = "no_se"
record_logs = "no_se"
auto_update = "no_se"

if go_on:
    while title_answer.lower() not in answers:
        title_answer = input(
            "\nVoulez-vous utiliser le nommage de TV-select "
            "pour nommer les titres des programmes? Si vous répondez oui, alors "
            "les titres seront composés du titre du programme, de son numéro "
            "d'idendification dans MEDIA-select puis de la recherche "
            "correspondante. Si vous répondez non, le nommage de Freebox OS "
            "sera utilisé (dans ce cas des erreurs peuvent apparaitre si la "
            "différence de temps (marge avant le début du film) est trop "
            "grande): "
        )
    print("\n\nLe nombre maximum de flux simultanés autorisé par Free est "
          "limité à 2 selon l'assistance de Free:\n"
          "https://assistance.free.fr/articles/gerer-et-visionner-mes-enregistrements-72\n"
          "Cependant, cette limite semble venir du faible débit de l'ADSL et il "
          "est possible d'enregistrer un plus grand nombre de vidéos "
          "simultanément si vous avez la fibre optique.\n")
    while change_max_rec.lower() not in answers:
        change_max_rec = input("Voulez-vous augmenter le nombre maximum "
                        "d'enregistrements simultanés autorisés par "
                        "le programme? (répondre par oui ou non): ")

    if change_max_rec.lower() == "oui":
        while max_sim_recordings <= 0:
            max_sim_recordings = input(
                "\nVeuillez saisir le nombre de vidéos simultanément enregistrées "
                "autorisé par le programme: "
            )
            try:
                max_sim_recordings = int(max_sim_recordings)
            except ValueError:
                max_sim_recordings = 0
                print(
                    "\nVeuillez saisir un nombre entier supérieur à 0 pour le "
                    "nombre de vidéos simultanément enregistrées par le "
                    "programme."
                )
    else:
        max_sim_recordings = 2

    while record_logs.lower() not in answers:
        record_logs = input(
            "\n\nAutorisez-vous l'application à collecter et envoyer des journaux "
            "d'erreurs anonymisés pour améliorer les performances et corriger les "
            "bugs? (répondre par oui ou non) : ").strip().lower()

    while auto_update.lower() not in answers:
        auto_update = input(
            "\n\nAutorisez-vous l'application à se mettre à jour automatiquement? "
            "Si vous répondez 'non', vous devrez mettre à jour l'application par "
            "vous-même. (répondre par oui ou non) : ").strip().lower()

    config_path = os.path.join("/home", user, ".config/select_freeboxos/config.json")
    template_path = os.path.join("/home", user, "select-freeboxos/config_template.json")

    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        shutil.copy(template_path, config_path)
        os.chmod(config_path, 0o640)

    print("\nConfiguration des tâches cron du programme MEDIA-select:\n")

    response = requests.head("https://media-select.fr")
    http_response = response.status_code

    if http_response != 200:
        print(
            "\nLa box MEDIA-select n'est pas connectée à internet. Veuillez "
            "vérifier votre connection internet et relancer le programme "
            "d'installation.\n\n"
        )
        go_on = False

if go_on:
    crypted = "no_se"

    while crypted.lower() not in answers:
        crypted = input("\nVoulez vous chiffrer les identifiants de connection à "
                        "l'application web MEDIA-select.fr ainsi que le mot de passe "
                        "admin à Freebox OS? Si vous répondez oui, "
                        "il faudra penser à débloquer gnome-keyring (ou tout "
                        "autre backend disponible sur votre système) à chaque "
                        "nouvelle session afin de permettre l'accès aux "
                        "identifiants par l'application MEDIA-select-fr. "
                        "(répondre par oui ou non) : ").strip().lower()

    hdmi_screen = "no_se"

    if crypted.lower() == "oui":
        ssh_connection = os.environ.get("SSH_CONNECTION")
        display_available = os.environ.get("DISPLAY")
        if ssh_connection is not None or not display_available:
            while hdmi_screen.lower() not in answers:
                hdmi_screen = input("\nVous êtes connecté en SSH à votre machine ou votre système pourrait ne "
                    "pas avoir d'interface graphique. Avez-vous accès à une interface graphique? "
                    "Répondez 'oui' si vous pouvez connecter un écran et visualiser les applications, "
                    "ou 'non' si vous ne pouvez vous connecter que via SSH ou si aucune interface graphique "
                    "n'est disponible (exemple: VM, carte Nanopi-NEO, server, OS sans interface "
                    "graphique): ").strip().lower()
        else:
            hdmi_screen = "oui"
        if hdmi_screen == "non":
            gpg_keys = get_gpg_keys()
            if not gpg_keys:
                print(
                    "Aucune clé GPG suffisament sécurisé n'est détectée dans votre système. Vous pouvez ajouter une clé GPG "
                    "à votre trousseau de clés pour chiffrer vos identifiants en utilisant "
                    "la commande suivante pour générer une nouvelle clé GPG: "
                    "\n\ngpg --full-generate-key\nVous pouvez suivre le tutoriel suivant pour ajouter "
                    "la clé GPG sécurisé: https://media-select.fr/advice-gpg-freeboxos puis relancez le programme d'installation."
                )
                exit()
            else:
                print("Voici la liste de vos clés GPG qui sont assez sécurisées pour chiffrer vos identifiants de connexion:")
                for index, (key_id, algo, key_size) in enumerate(gpg_keys, start=1):
                    print(f"{index}) Key ID: {key_id}, Algorithm: {algo}, Size: {key_size} bits")
                if len(gpg_keys) > 1:
                    selected_key = 0
                    while not (1 <= selected_key <= len(gpg_keys)):
                        try:
                            selected_key = int(input(f"Merci de choisir un nombre entre 1 et {len(gpg_keys)} "
                                                    "pour sélectionner la clé de chiffrement GPG à utiliser: "))
                        except ValueError:
                            print("Veuillez entrer un nombre valide.")
                else:
                    selected_key = 1
                process = run(["pass", "init", gpg_keys[selected_key - 1][0]],
                                            stdout=PIPE, stderr=PIPE, text=True)


    heure = random.randint(6, 23)
    minute = random.randint(0, 58)

    config = {}

    config["CRYPTED_CREDENTIALS"] = crypted.lower() == "oui"

    if config["CRYPTED_CREDENTIALS"]:
        config["ADMIN_PASSWORD"] = "XXXXXXX"
        config["FREEBOX_SERVER_IP"] = "XXXXXXX"
    else:
        config["ADMIN_PASSWORD"] = freebox_os_password
        config["FREEBOX_SERVER_IP"] = FREEBOX_SERVER_IP

    config["MEDIA_SELECT_TITLES"] = title_answer.lower() == "oui"
    config["MAX_SIM_RECORDINGS"] = int(max_sim_recordings)
    config["SENTRY_MONITORING_SDK"] = record_logs.lower() == "oui"
    config["CURL_HOUR"] = int(heure)
    config["CURL_MINUTE"] = int(minute)

    config_path = f"/home/{user}/.config/select_freeboxos/config.json"

    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    os.chmod(config_path, 0o640)

    http_status = 403

    if hdmi_screen == "non":
        sleep(1)
        print("Veuillez saisir l'email de votre compte à MEDIA-select.fr. L'email "
            "ne sera pas visible par mesure de sécurité et devra être répété "
            "une 2ème fois pour s'assurer d'avoir saisi l'email correctement. S'"
            "il vous est posé la question 'An entry already exists for "
            "media-select/email. Overwrite it? [y/N] y', répondez y")
        insert_email = run(["pass", "insert", "media-select/email"])
        sleep(1)
        print("Veuillez saisir le mot de passe de votre compte à MEDIA-select.fr. "
            "Le mot de passe ne sera pas visible par mesure de sécurité et "
            "devra être répété une 2ème fois pour s'assurer d'avoir saisi "
            "l'email correctement. S'il vous est posé la question 'An entry already exists for "
            "media-select/password. Overwrite it? [y/N] y', répondez y")
        insert_password = run(["pass", "insert", "media-select/password"])
    else:
        username_mediaselect = input(
            "Veuillez saisir votre identifiant de connexion (adresse "
            "email) sur MEDIA-select.fr: "
        )
        password_mediaselect = getpass.getpass(
            "Veuillez saisir votre mot de passe sur MEDIA-select.fr: "
        )

    while http_status != 200:

        if hdmi_screen == "non":
            pass_email = run(["pass", "media-select/email"], stdout=PIPE, stderr=PIPE)
            username_mediaselect = pass_email.stdout.strip()
            pass_password = run(["pass", "media-select/password"], stdout=PIPE, stderr=PIPE)
            password_mediaselect = pass_password.stdout.strip()

        response = requests.head("https://www.media-select.fr/api/v1/prog", auth=(username_mediaselect, password_mediaselect))
        http_status = response.status_code

        if http_status != 200:
            try_again = input(
                "Le couple identifiant de connexion et mot de passe "
                "est incorrect.\nVoulez-vous essayer de nouveau?(oui ou non): "
            )
            answer_hide = "maybe"
            if try_again.lower() == "oui":
                if hdmi_screen == "oui":
                    username_mediaselect = input(
                        "Veuillez saisir de nouveau votre identifiant de connexion (adresse email) sur MEDIA-select.fr: "
                    )
                    while answer_hide.lower() not in answers:
                        answer_hide = input(
                            "Voulez-vous afficher le mot de passe que vous saisissez "
                            "pour que cela soit plus facile? (répondre par oui ou non): "
                        )
                    if answer_hide.lower() == "oui":
                        password_mediaselect = input(
                            "Veuillez saisir de nouveau votre mot de passe sur MEDIA-select.fr: "
                        )
                    else:
                        password_mediaselect = getpass.getpass(
                            "Veuillez saisir de nouveau votre mot de passe sur MEDIA-select.fr: "
                        )
                else:
                    print("Veuillez saisir l'email de votre compte à MEDIA-select.fr. L'email "
                        "ne sera pas visible par mesure de sécurité et devra être répété "
                        "une 2ème fois pour s'assurer d'avoir saisi l'email correctement.")
                    insert_email = run(["pass", "insert", "media-select/email"])
                    sleep(1)
                    print("Veuillez saisir le mot de passe de votre compte à MEDIA-select.fr. "
                        "Le mot de passe ne sera pas visible par mesure de sécurité et "
                        "devra être répété une 2ème fois pour s'assurer d'avoir saisi l'email correctement.")
                    insert_password = run(["pass", "insert", "media-select/password"])
                    sleep(1)
            else:
                go_on = False
                break

if go_on:
    if crypted.lower() == "non" and go_on:
        netrc_path = os.path.expanduser("~/.netrc")
        if not os.path.exists(netrc_path):
            run(["touch", netrc_path], check=True)
            os.chmod(netrc_path, 0o600)

        with open(f"/home/{user}/.netrc", "r", encoding='utf-8') as file:
            lines = file.read().splitlines()

        try:
            position = lines.index("machine www.media-select.fr")
            lines[position + 1] = f"  login {username_mediaselect}"
            lines[position + 2] = f"  password {password_mediaselect}"
        except ValueError:
            lines.append("machine www.media-select.fr")
            lines.append(f"  login {username_mediaselect}")
            lines.append(f"  password {password_mediaselect}")

        with open(f"/home/{user}/.netrc", "w", encoding='utf-8') as file:
            for line in lines:
                file.write(line + "\n")

    if crypted.lower() == "oui" and go_on:
        if hdmi_screen == "oui":
            print("\nSi votre système d'exploitation ne déverrouille pas automatiquement le trousseau de clés "
                "comme sur Raspberry OS, une fenêtre du gestionnaire du trousseau s'est ouverte et il vous "
                "faudra la débloquer en saisissant votre mot de passe. Si c'est la première ouverture "
                "de votre trousseau de clé, il vous sera demandé de créer un mot de passe qu'il faudra renseigner à chaque "
                "nouvelle session afin de permettre l'accès des identifiants chiffrés au programme mediaselect-fr.\n")

            keyring.set_password("media-select", "username", username_mediaselect)
            keyring.set_password("media-select", "password", password_mediaselect)
            keyring.set_password("freeboxos", "username", FREEBOX_SERVER_IP)
            keyring.set_password("freeboxos", "password", freebox_os_password)
        else:
            process = run(["pass", "insert", "--multiline", "--force", "freeboxos/username"],
                input=FREEBOX_SERVER_IP.encode(),
                stdout=PIPE,
                stderr=PIPE
            )
            if process.returncode == 0:
                print("\nL'adresse IP de Freebox OS a été chiffré avec pass.")
            else:
                print(f"Error: {process.stderr.decode()}")
                exit()

            process = run(["pass", "insert", "--multiline", "--force", "freeboxos/password"],
                input=freebox_os_password.encode(),
                stdout=PIPE,
                stderr=PIPE
            )
            if process.returncode == 0:
                print("\nLe mot de passe de Freebox OS a été chiffré avec pass.")
            else:
                print(f"Error: {process.stderr.decode()}")
                exit()


    if go_on:
        minute_2 = minute + 1
        heure_auto_update = heure - 1
        minute_auto_update = random.randint(0, 59)

        answer_cron = "maybe"

        while answer_cron.lower() not in answers:
            answer_cron = input(
                "\nLe programme va maintenant ajouter une tâche cron à "
                "votre crontab. Une sauvegarde de votre crontab sera "
                "réalisée dans ce ficher: ~/.crontab_backup . "
                "Voulez-vous continuer? (répondre par oui ou non): "
            )

        if answer_cron.lower() == "non":
            print('\nSortie du programme.\n')
            exit()

        backup_file = os.path.join(os.path.expanduser("~"), ".crontab_backup")
        with open(backup_file, "w", encoding='utf-8') as f:
            try:
                result = run(["crontab", "-l"], check=True, stdout=f, stderr=PIPE, universal_newlines=True, user=user)
            except CalledProcessError as e:
                if "no crontab for" in e.stderr:
                    print(f"Il n'y a pas de crontab paramétré pour {user}."
                            " Aucun backup n'a été effectué.")
                else:
                    raise

        cron_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "cron_tasks.sh")
        with open(cron_file, "w", encoding='utf-8') as f:
            try:
                result = run(["crontab", "-l"], check=True, stdout=f, stderr=PIPE, universal_newlines=True, user=user)
            except CalledProcessError as e:
                if "no crontab for" in e.stderr:
                    print(f"No crontab set for {user}")
                else:
                    raise
        os.chmod(cron_file, 0o700)
        with open(
            f"/home/{user}/.local/share/select_freeboxos/cron_tasks.sh", "r", encoding='utf-8'
        ) as crontab_file:
            cron_lines = crontab_file.readlines()

        curl = (
            f"{minute} {heure} * * * env DBUS_SESSION_BUS_ADDRESS=unix:path=/run"
            "/user/$(id -u)/bus /bin/bash $HOME/select-freeboxos/curl_"
            "mediaselect.sh\n"
        )

        cron_launch = (
            f"{minute_2} {heure} * * * cd $HOME/select-freeboxos && env "
            "DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus "
            f"USER='{user}' bash cron_freeboxos_app.sh\n"
        )

        cron_auto_update = (
            f'{minute_auto_update} {heure_auto_update} * * * /bin/bash -c "$HOME'
            '/select-freeboxos/auto_update.sh >> $HOME/.local/share'
            '/select_freeboxos/logs/auto_update.log 2>&1"\n'
        )

        if hdmi_screen != "non":
            cron_lines = [
                curl if "freeboxos/curl_mediaselect.sh" in cron else
                cron_launch if "select-freeboxos &&" in cron else cron
                for cron in cron_lines
            ]
        else:
            cron_lines = [
                cron for cron in cron_lines
                if "freeboxos/curl_mediaselect.sh" not in cron and
                "select-freeboxos &&" not in cron
            ]


        if auto_update.lower() == "oui":
            cron_lines = [
                cron_auto_update if "freeboxos/auto_update" in cron else cron
                for cron in cron_lines
            ]
        else:
            cron_lines = [
                cron for cron in cron_lines if "freeboxos/auto_update" not in cron
            ]

        cron_lines_join = "".join(cron_lines)

        if hdmi_screen != "non" and "freeboxos/curl_mediaselect.sh" not in cron_lines_join:
            cron_lines.append(curl)
        if hdmi_screen != "non" and "cd $HOME/select-freeboxos &&" not in cron_lines_join:
            cron_lines.append(cron_launch)

        if auto_update.lower() == "oui" and "freeboxos/auto_update" not in cron_lines_join:
            cron_lines.append(cron_auto_update)

        with open(
            f"/home/{user}/.local/share/select_freeboxos/cron_tasks.sh", "w", encoding='utf-8'
        ) as crontab_file:
            for cron_task in cron_lines:
                crontab_file.write(cron_task)

        cron_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "cron_tasks.sh")
        run(["crontab", cron_file], check=True, user=user)

        cron_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "cron_tasks.sh")
        run(["rm", cron_file], check=True)

        print(
            "\nLes tâches cron de votre box MEDIA-select sont maintenant configurés!\n"
        )
