#!/bin/bash

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
  HOME_DIR=$(eval echo ~$SUDO_USER)
  cd "$HOME_DIR" && curl https://github.com/mediaselect/select-freeboxos-sbc-vm/archive/refs/tags/v2.0.0.zip -L -o select_freebox.zip
  selectos=$(ls "$HOME_DIR" | grep select-freeboxos)
  pretty=$(grep 'PRETTY_NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
  if [ -n "$selectos" ]
  then
    rm -rf "$HOME_DIR"/select-freeboxos
  fi
  unzip select_freebox.zip && mv select-freeboxos-sbc-vm-2.0.0 select-freeboxos && rm select_freebox.zip
  chown -R "$SUDO_USER:$SUDO_USER" "$HOME_DIR/select-freeboxos"
  echo "Step 3 - freeboxos download done"
}

arch32=("AArch32" "arm" "ARMv1" "ARMv2" "ARMv3" "ARMv4" "ARMv5" "ARMv6" "ARMv7")

arch64=("AArch64" "arm64" "ARMv8" "ARMv9")

info_not_arm=false

step_4_create_select_freeboxos_directories() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 4 - Creating .local/share/select_freeboxos"
  user=$(who am i | awk '{print $1}')
  if [ ! -d /home/$user/.local ]; then
    sudo -u $user mkdir /home/$user/.local
    sudo -u $user chmod 700 /home/$user/.local
  fi
  if [ ! -d /home/$user/.local/share ]; then
    sudo -u $user mkdir /home/$user/.local/share
    sudo -u $user chmod 700 /home/$user/.local/share
  fi
  if [ ! -d /home/$user/.config ]; then
    sudo -u $user mkdir /home/$user/.config
    sudo -u $user chmod 700 /home/$user/.config
  fi
  sudo -u $user mkdir -p /home/$user/.local/share/select_freeboxos/logs
  sudo -u $user chmod -R 740 /home/$user/.local/share/select_freeboxos
  sudo -u $user mkdir -p /home/$user/.config/select_freeboxos
  sudo -u $user chmod -R 740 /home/$user/.config/select_freeboxos
  echo "Step 4 - select_freeboxos directories created"
}

step_5_geckodriver_download() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 5 - geckodriver download"
  cd /home/$user/.local/share/select_freeboxos
  cpu=$(lscpu | grep Architecture | awk {'print $2'})
  cpu_lower=$(echo "$cpu" | tr '[:upper:]' '[:lower:]')
  cpu_five_chars="${cpu_lower:0:5}"

  if echo "${arch64[@],,}" | grep -q "$cpu_five_chars"
  then
    wget https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux-aarch64.tar.gz
    GECKODRIVER_AARCH64_SHA256="91d1e446646d8ee85830970e4480652b725f19e7ecbefa3ffd3947bc7be23a47"
    if ! echo "$GECKODRIVER_AARCH64_SHA256 geckodriver-v0.35.0-linux-aarch64.tar.gz" | sha256sum -c -; then
        echo "ERROR: Checksum verification failed for geckodriver v0.35.0 aarch64!"
        exit 1
    fi
    sudo -u $user bash -c "tar xzvf geckodriver-v0.35.0-linux-aarch64.tar.gz"
  elif echo "${arch32[@],,}" | grep -q "$cpu_five_chars"
  then
    wget https://github.com/jamesmortensen/geckodriver-arm-binaries/releases/download/v0.34.0/geckodriver-v0.34.0-linux-armv7l.tar.gz
    GECKODRIVER_ARM_SHA256="381732e6d7abecfee36bc2f59f4324cfb913f4b08cd611a38148baf130f44e40"
    if ! echo "$GECKODRIVER_ARM_SHA256 geckodriver-v0.34.0-linux-armv7l.tar.gz" | sha256sum -c -; then
        echo "ERROR: Checksum verification failed for geckodriver v0.34.0 armv7l!"
        exit 1
    fi
    sudo -u $user bash -c "tar xzvf geckodriver-v0.34.0-linux-armv7l.tar.gz"
  else
    info_not_arm=true
  echo "Step 5 - geckodriver download done"
  fi
}


step_6_virtual_environment() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 6 - Virtual env + requirements install"
  sudo -u $user bash -c "virtualenv -p python3 .venv"
  sudo -u $user bash -c "source .venv/bin/activate && pip install -r /home/$user/select-freeboxos/requirements.txt"
  echo "Step 6 - Virtual env created and requirements installed"
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
  step_6_virtual_environment
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
