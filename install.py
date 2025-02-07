import readline
import random
import getpass
import logging
import os
import shutil
import requests

from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException

from subprocess import Popen, PIPE, run, CalledProcessError

from module_freeboxos import get_website_title, is_snap_installed, is_firefox_snap, is_firefox_esr_installed

user = os.getenv("USER")

logging.basicConfig(
    filename="/home/" + user + "/.local/share/select_freeboxos/logs/select_freeboxos.log",
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
        "a l'adresse IP " + FREEBOX_SERVER_IP + "\n\nLe programme va "
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
            "a l'adresse IP " + FREEBOX_SERVER_IP + "\n\nLe programme va "
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
    service = Service(executable_path="./geckodriver")
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
        driver.get("https://" + FREEBOX_SERVER_IP + "/login.php")
    else:
        driver.get("http://" + FREEBOX_SERVER_IP + "/login.php")
except WebDriverException as e:
    if 'net::ERR_ADDRESS_UNREACHABLE' in e.msg:
        print("The programme cannot reach the address " + FREEBOX_SERVER_IP + " . Exit programme.")
        logging.error(
            "The programme cannot reach the address " + FREEBOX_SERVER_IP + " . Exit programme."
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
            "d'erreurs pour améliorer les performances et corriger les "
            "bugs? (répondre par oui ou non) : ").strip().lower()

    while auto_update.lower() not in answers:
        auto_update = input(
            "\n\nAutorisez-vous l'application à se mettre à jour automatiquement? "
            "Si vous répondez 'non', vous devrez mettre à jour l'application par "
            "vous-même. (répondre par oui ou non) : ").strip().lower()

    config_path = os.path.join("/home", user, ".config/select_freeboxos/config.py")
    template_path = os.path.join("/home", user, "select-freeboxos/config_template.py")

    if not os.path.exists(config_path):
        shutil.copy(template_path, config_path)
        os.chmod(config_path, 0o640)

    params = ["ADMIN_PASSWORD",
              "FREEBOX_SERVER_IP",
              "MEDIA_SELECT_TITLES",
              "MAX_SIM_RECORDINGS",
              "SENTRY_MONITORING_SDK",
              ]

    with open("/home/" + user + "/.config/select_freeboxos/" "config.py", "w") as conf:
        for param in params:
            if "ADMIN_PASSWORD" in param:
                conf.write('ADMIN_PASSWORD = "' + freebox_os_password + '"\n')
            elif "FREEBOX_SERVER_IP" in param:
                conf.write('FREEBOX_SERVER_IP = "' + FREEBOX_SERVER_IP + '"\n')
            elif "MEDIA_SELECT_TITLES" in param:
                if title_answer.lower() == "oui":
                    conf.write("MEDIA_SELECT_TITLES = True\n")
                else:
                    conf.write("MEDIA_SELECT_TITLES = False\n")
            elif "MAX_SIM_RECORDINGS" in param:
                conf.write("MAX_SIM_RECORDINGS = " + str(max_sim_recordings) + "\n")
            elif "SENTRY_MONITORING_SDK" in param:
                if record_logs.lower() == "oui":
                    conf.write("SENTRY_MONITORING_SDK = True\n")
                else:
                    conf.write("SENTRY_MONITORING_SDK = False\n")
            else:
                conf.write(param + "\n")

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
        username = input(
            "Veuillez saisir votre identifiant de connexion (adresse "
            "email) sur MEDIA-select.fr: "
        )
        password_mediarecord = getpass.getpass(
            "Veuillez saisir votre mot de passe sur MEDIA-select.fr: "
        )

        home_dir = os.path.expanduser("~")
        netrc_files = [f for f in os.listdir(home_dir) if f == ".netrc"]
        ls_netrc = netrc_files[0] if netrc_files else ""

        if ls_netrc == "":
            home_dir = os.path.expanduser("~")
            netrc_file = os.path.join(home_dir, ".netrc")
            with open(netrc_file, 'a'):
                os.utime(netrc_file, None)
            home_dir = os.path.expanduser("~")
            netrc_file = os.path.join(home_dir, ".netrc")
            os.chmod(netrc_file, 0o600)

        authprog_response = "403"

        with open("/home/" + user + "/.netrc", "r") as file:
            lines_origin = file.read().splitlines()

        while authprog_response != "200":
            with open("/home/" + user + "/.netrc", "r") as file:
                lines = file.read().splitlines()

            try:
                position = lines.index("machine www.media-select.fr")
                lines[position + 1] = "  login {username}".format(username=username)
                lines[position + 2] = "  password {password_mediarecord}".format(
                    password_mediarecord=password_mediarecord
                )
            except ValueError:
                lines.append("machine www.media-select.fr")
                lines.append("  login {username}".format(username=username))
                lines.append(
                    "  password {password_mediarecord}".format(
                        password_mediarecord=password_mediarecord
                    )
                )

            with open("/home/" + user + "/.netrc", "w") as file:
                for line in lines:
                    file.write(line + "\n")

            cmd = ['curl', '-iSn', 'https://www.media-select.fr/api/v1/progfree']
            authprog = run(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
            authprog_response = authprog.stdout.split('\n')[0].split(' ')[1]

            if authprog_response != "200":
                try_again = input(
                    "Le couple identifiant de connexion et mot de passe "
                    "est incorrect.\nVoulez-vous essayer de nouveau?(oui ou non): "
                )
                answer_hide = "maybe"
                if try_again.lower() == "oui":
                    username = input(
                        "Veuillez saisir de nouveau votre identifiant de connexion (adresse email) sur MEDIA-select.fr: "
                    )
                    while answer_hide.lower() not in answers:
                        answer_hide = input(
                            "Voulez-vous afficher le mot de passe que vous saisissez "
                            "pour que cela soit plus facile? (répondre par oui ou non): "
                        )
                    if answer_hide.lower() == "oui":
                        password_mediarecord = input(
                            "Veuillez saisir de nouveau votre mot de passe sur MEDIA-select.fr: "
                        )
                    else:
                        password_mediarecord = getpass.getpass(
                            "Veuillez saisir de nouveau votre mot de passe sur MEDIA-select.fr: "
                        )
                else:
                    go_on = False
                    with open("/home/" + user + "/.netrc", "w") as file:
                        for line in lines_origin:
                            file.write(line + "\n")
                    break
        if go_on:
            heure = random.randint(6, 23)
            minute = random.randint(0, 58)
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
            with open(backup_file, "w") as f:
                try:
                    result = run(["crontab", "-l"], check=True, stdout=f, stderr=PIPE, universal_newlines=True, user=user)
                except CalledProcessError as e:
                    if "no crontab for" in e.stderr:
                        print(f"Il n'y a pas de crontab paramétré pour {user}."
                              " Aucun backup n'a été effectué.")
                    else:
                        raise

            cron_file = os.path.join(os.path.expanduser("~"), ".local", "share", "select_freeboxos", "cron_tasks.sh")
            with open(cron_file, "w") as f:
                try:
                    result = run(["crontab", "-l"], check=True, stdout=f, stderr=PIPE, universal_newlines=True, user=user)
                except CalledProcessError as e:
                    if "no crontab for" in e.stderr:
                        print(f"No crontab set for {user}")
                    else:
                        raise
            os.chmod(cron_file, 0o700)
            with open(
                "/home/" + user + "/.local/share/select_freeboxos/cron" "_tasks.sh", "r"
            ) as crontab_file:
                cron_lines = crontab_file.readlines()

            curl = (
                "{minute} {heure} * * * curl -H 'Accept: application/json;"
                "indent=4' -n https://www.media-select.fr/api/v1/progfree > "
                "$HOME/.local/share/select_freeboxos/info_progs.json 2>> "
                "$HOME/.local/share/select_freeboxos/logs/cron_curl.log\n".format(
                    minute=minute,
                    heure=heure,
                )
            )

            cron_launch = (
                "{minute_2} {heure} * * * export USER='{user}' && "
                "cd /home/$USER/select-freeboxos && bash cron_freeboxos_app"
                ".sh\n".format(user=user, minute_2=minute_2, heure=heure)
            )

            cron_auto_update = (
                '{minute_auto_update} {heure_auto_update} * * * /bin/bash -c "$HOME'
                '/select-freeboxos/auto_update.sh >> $HOME/.local/share'
                '/select_freeboxos/logs/auto_update.log 2>&1"\n'.format(
                    minute_auto_update=minute_auto_update,
                    heure_auto_update=heure_auto_update)
            )

            cron_lines = [
                curl if "select_freeboxos/info_progs.json" in cron else cron
                for cron in cron_lines
            ]
            cron_lines = [
                cron_launch if "select-freeboxos &&" in cron else cron
                for cron in cron_lines
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

            if "select_freeboxos/info_progs.json" not in cron_lines_join:
                cron_lines.append(curl)
            if "cd /home/$USER/select-freeboxos &&" not in cron_lines_join:
                cron_lines.append(cron_launch)

            if auto_update.lower() == "oui" and "freeboxos/auto_update" not in cron_lines_join:
                cron_lines.append(cron_auto_update)

            with open(
                "/home/" + user + "/.local/share/select_freeboxos" "/cron_tasks.sh", "w"
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
