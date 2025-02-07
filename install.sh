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
  apt -y upgrade
  echo "Step 1 - Install done"
}

step_2_mainpackage() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 2 - packages"
  apt -y install curl
  apt -y install virtualenv
  apt -y install unzip
  apt -y install cron
  apt -y install jq
  hostname=$(uname -n)
  codename=$(grep 'VERSION_CODENAME=' /etc/os-release | cut -d'=' -f2)
  if [ $hostname = "nanopineo" ]
  then
    add-apt-repository -y ppa:mozillateam/ppa
    apt update
    apt -y install firefox-esr
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
    apt -y install firefox-esr
  elif [ $codename = "noble" ]
  then
    # snap remove firefox
    add-apt-repository -y ppa:mozillateam/ppa
    apt update
    apt -y install firefox-esr
  elif [ $hostname = "raspbian-bullseye-aml-s905x-cc" -o $hostname = "NanoPi-NEO" ]
  then
    apt -y install software-properties-common
    add-apt-repository -y ppa:mozillateam/ppa
    apt update
    apt -y install firefox-esr
  else
    apt -y install firefox
  fi
  echo "step 2 - packages done"
}

step_3_freeboxos_download() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 3 - freeboxos download"
  HOME_DIR=$(eval echo ~$SUDO_USER)
  cd "$HOME_DIR" && curl https://github.com/mediaselect/select-freeboxos-sbc-vm/archive/refs/tags/v1.0.0.zip -L -o select_freebox.zip
  selectos=$(ls "$HOME_DIR" | grep select-freeboxos)
  pretty=$(grep 'PRETTY_NAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
  if [ -n "$selectos" ]
  then
    rm -rf "$HOME_DIR"/select-freeboxos
  fi
  unzip select_freebox.zip && mv select-freeboxos-sbc-vm-1.0.0 select-freeboxos && rm select_freebox.zip
  # if [ $hostname = "lepotato" ]
  # then
  #   echo "Use geckodriver of Firefox installed from snap"
  #   sed -i -e 's/\.\/geckodriver/\/snap\/bin\/firefox.geckodriver/g' "$HOME_DIR"/select-freeboxos/install.py "$HOME_DIR"/select-freeboxos/freeboxos.py
  # elif [ "$pretty" = "Ubuntu 22.04.4 LTS" ]
  # then
  #   echo "Use geckodriver of Firefox installed from snap"
  #   sed -i -e 's/\.\/geckodriver/\/snap\/bin\/geckodriver/g' "$HOME_DIR"/select-freeboxos/install.py "$HOME_DIR"/select-freeboxos/freeboxos.py
  # fi
  echo "Step 3 - freeboxos download done"
}

arch32=("AArch32" "arm" "ARMv1" "ARMv2" "ARMv3" "ARMv4" "ARMv5" "ARMv6" "ARMv7")

arch64=("AArch64" "arm64" "ARMv8" "ARMv9")

info_not_arm=false

step_4_geckodriver_download() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 4 - geckodriver download"
  cd "$HOME_DIR"/select-freeboxos
  cpu=$(lscpu | grep Architecture | awk {'print $2'})
  cpu_lower=$(echo "$cpu" | tr '[:upper:]' '[:lower:]')
  cpu_five_chars="${cpu_lower:0:5}"

  if echo "${arch64[@],,}" | grep -q "$cpu_five_chars"
  then
    wget https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux-aarch64.tar.gz
    tar xzvf geckodriver-v0.34.0-linux-aarch64.tar.gz
  elif echo "${arch32[@],,}" | grep -q "$cpu_five_chars"
  then
    wget https://github.com/jamesmortensen/geckodriver-arm-binaries/releases/download/v0.34.0/geckodriver-v0.34.0-linux-armv7l.tar.gz
    tar xzvf geckodriver-v0.34.0-linux-armv7l.tar.gz
  else
    info_not_arm=true
  echo "Step 4 - geckodriver download done"
  fi
}

step_5_virtual_environment() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 5 - Virtual env + requirements install"
  virtualenv -p python3 .venv
  source .venv/bin/activate && pip install -r requirements.txt
  chown -R "$SUDO_USER:$SUDO_USER" "$HOME_DIR/select-freeboxos"
  echo "Step 5 - Virtual env created and requirements installed"
}

step_6_create_select_freeboxos_directories() {
  echo "---------------------------------------------------------------------"
  echo "Starting step 6 - Creating .local/share/select_freeboxos"
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
  echo "Step 6 - select_freeboxos directories created"
}


STEP=0

case ${STEP} in
  0)
  echo "Starting installation ..."
  step_1_upgrade
  step_2_mainpackage
  step_3_freeboxos_download
  step_4_geckodriver_download
  step_5_virtual_environment
  step_6_create_select_freeboxos_directories
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
