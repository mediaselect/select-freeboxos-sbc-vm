#!/bin/bash

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

user=${SUDO_USER:-$USER}
HOME_DIR=$(getent passwd "$user" | cut -d: -f6)
if [ -z "$HOME_DIR" ]; then
  echo "ERROR: unable to determine home directory for user '$user'" >&2
  exit 1
fi

# Installation des librairies:

echo -e "Installation des librairies nécessaires\n"

if [ $(id -u) != 0 ] ; then
  echo "Les droits Superuser (root) sont nécessaires pour installer select-freeboxos"
  echo "Lancez 'sudo $0' pour obtenir les droits Superuser."
  exit 1
fi

step_1_upgrade() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 1 - install"
  apt update
  apt upgrade -y
  echo "Step 1 - Install done"
}

step_2_mainpackage() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 2 - packages"
  apt install curl -y
  apt install virtualenv -y
  apt install unzip -y
  apt install cron -y
  apt install jq -y
  hostname=$(uname -n)
  codename=$(grep 'VERSION_CODENAME=' /etc/os-release | cut -d'=' -f2)
  if [ $hostname = "nanopineo" ]
  then
    add-apt-repository -y ppa:mozillateam/ppa
    apt update
    apt install firefox-esr -y
  # elif [ $hostname = "lepotato" -a $codename = "bookworm" ]
  # then
  #   echo "Purge firefox-esr already installed on Le potato cards with \
  #   Armbian bookworm."
  #   apt -y purge firefox-esr
  #   echo "Install snapd and Firefox with Snap"
  #   apt -y install snapd
  #   systemctl start snapd
  #   systemctl enable snapd
  #   snap install firefox
  elif [ $codename = "bookworm" ]
  then
    apt install firefox-esr -y
  elif [ $codename = "noble" ]
  then
    # snap remove firefox
    add-apt-repository -y ppa:mozillateam/ppa
    apt update
    apt install firefox-esr -y
  elif [ $hostname = "raspbian-bullseye-aml-s905x-cc" -o $hostname = "NanoPi-NEO" ]
  then
    apt install software-properties-common -y
    add-apt-repository -y ppa:mozillateam/ppa
    apt update
    apt install firefox-esr -y
  else
    apt install firefox -y
  fi
  echo "step 2 - packages done"
}

step_3_freeboxos_download() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 3 - freeboxos download"
  cd "$HOME_DIR" && curl https://github.com/mediaselect/select-freeboxos-sbc-vm/archive/refs/tags/v2.0.0.zip -L -o select_freebox.zip
  if [ -d "$HOME_DIR/select-freeboxos" ]; then
      rm -rf "$HOME_DIR/select-freeboxos"
  fi
  unzip select_freebox.zip && mv select-freeboxos-sbc-vm-2.0.0 select-freeboxos && rm select_freebox.zip
  chown -R "$SUDO_USER:$SUDO_USER" "$HOME_DIR/select-freeboxos"
  echo "Step 3 - freeboxos download done"
}

step_4_create_select_freeboxos_directories() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 4 - Creating .local/share/select_freeboxos"
  if [ ! -d "$HOME_DIR/.local" ]; then
    sudo -u "$user" mkdir "$HOME_DIR/.local"
    sudo -u "$user" chmod 700 "$HOME_DIR/.local"
  fi
  if [ ! -d "$HOME_DIR/.local/share" ]; then
    sudo -u "$user" mkdir "$HOME_DIR/.local/share"
    sudo -u "$user" chmod 700 "$HOME_DIR/.local/share"
  fi
  if [ ! -d "$HOME_DIR/.config" ]; then
    sudo -u "$user" mkdir "$HOME_DIR/.config"
    sudo -u "$user" chmod 700 "$HOME_DIR/.config"
  fi
  sudo -u "$user" mkdir -p "$HOME_DIR/.local/share/select_freeboxos/logs"
  sudo -u "$user" chmod -R 740 "$HOME_DIR/.local/share/select_freeboxos"
  sudo -u "$user" mkdir -p "$HOME_DIR/.config/select_freeboxos"
  sudo -u "$user" chmod -R 740 "$HOME_DIR/.config/select_freeboxos"
  echo "Step 4 - select_freeboxos directories created"
}

info_not_arm=false

step_5_geckodriver_download() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 5 - geckodriver download"
  cd "$HOME_DIR/.local/share/select_freeboxos"

  case "$(uname -m)" in
    aarch64|arm64)
      wget https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux-aarch64.tar.gz
      GECKODRIVER_SHA256="91d1e446646d8ee85830970e4480652b725f19e7ecbefa3ffd3947bc7be23a47"
      FILE="geckodriver-v0.35.0-linux-aarch64.tar.gz"
      ;;
    armv7l)
      wget https://github.com/jamesmortensen/geckodriver-arm-binaries/releases/download/v0.34.0/geckodriver-v0.34.0-linux-armv7l.tar.gz
      GECKODRIVER_SHA256="381732e6d7abecfee36bc2f59f4324cfb913f4b08cd611a38148baf130f44e40"
      FILE="geckodriver-v0.34.0-linux-armv7l.tar.gz"
      ;;
    *)
      info_not_arm=true
      echo "INFO: architecture $(uname -m) is not ARM, skipping geckodriver install"
      echo "Step 5 - geckodriver download done"
      return 0
      ;;
  esac

  if ! echo "$GECKODRIVER_SHA256 $FILE" | sha256sum -c -; then
    echo "ERROR: Checksum verification failed for $FILE!" >&2
    exit 1
  fi

  sudo -u "$user" tar xzvf "$FILE"
  echo "Step 5 - geckodriver download done"
}

step_6_install_gpg_key() {
  echo "---------------------------------------------------------------------"
  echo "Step 6 - Installing GPG public key"

  SRC_KEY="$HOME_DIR/select-freeboxos/.gpg/public.key"
  DEST_DIR="$HOME_DIR/.config/select_freeboxos"
  DEST_KEY="$DEST_DIR/public.key"

  if [ ! -f "$SRC_KEY" ]; then
    echo "ERROR: GPG public key not found at $SRC_KEY"
    exit 1
  fi

  sudo -u "$user" mkdir -p "$DEST_DIR"
  sudo -u "$user" cp "$SRC_KEY" "$DEST_KEY"
  sudo -u "$user" chmod 640 "$DEST_KEY"

  echo "Step 6 - GPG public key installed"
}


STEP=0

case ${STEP} in
  0)
  echo "Starting installation ..."
  step_1_upgrade
  step_2_mainpackage
  step_3_freeboxos_download
  step_4_create_select_freeboxos_directories
  step_5_geckodriver_download
  step_6_install_gpg_key
  ;;
esac

if $info_not_arm
then
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  echo "Geckodriver n'a pas pu être téléchargé car votre architecture \
CPU est différente de ARM. Le programme ne peut pas \
fonctionner sans geckodriver. Contactez TV-select pour obtenir le \
geckodriver qui correspond à votre architecture CPU."
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
fi
