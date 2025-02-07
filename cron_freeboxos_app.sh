echo --- crontab start: $(date) >> /home/$USER/.local/share/select_freeboxos/logs/cron_freeboxos.log
cd /home/$USER/select-freeboxos
. /home/$USER/.local/share/select_freeboxos/.venv/bin/activate
export DISPLAY=:0 && python3 freeboxos.py >> /home/$USER/.local/share/select_freeboxos/logs/cron_freeboxos.log 2>&1
deactivate
echo --- crontab end: $(date) >> /home/$USER/.local/share/select_freeboxos/logs/cron_freeboxos.log
