import shlex
import os
import subprocess
import sys
sys.path.insert(0, '../')
from config import *
import common
import util

command_listener_log = util.parserLog('/var/log/sbp/flashscore/command_listener.log', 'bet356live-info')

#ZA SADA POSTOJI SAMO ZA KOLEKTOR

def reload_collector(sport):

    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    # print(sport)
    check_if_open = 0
    for pid in pids:
        try:
            proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
            if sport in proces_name and "collector" in proces_name and '/bin/sh' not in proces_name:
                check_if_open += 1
        except IOError:
            continue

    if check_if_open == 0:
        relaunch_cmd = "xvfb-run -a python3 {}classes/collector.py {}".format(project_root_path, sport)  #
        # print(relaunch_cmd)
        subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
        command_listener_log.info("Procces_checker - open sport {}".format(sport))
    else:
        command_listener_log.info("Procces_checker - All OK")

def check_parser_activity():

    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    activity = False
    for pid in pids:
        try:
            proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
            if "emmiter" in proces_name or "enqueuer" in proces_name:
                activity = True
        except IOError:
            continue

    return activity

if __name__ == '__main__':

    sports = common.tip_bet_allowed_sports
    activity = check_parser_activity()
    if activity is True:
        for sport in sports:
            reload_collector(sport)
