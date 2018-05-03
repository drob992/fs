import shlex
import os
import subprocess
import sys
sys.path.insert(0, '../')
from config import *
import common
import util
import redis
import time

command_listener_log = util.parserLog('/var/log/sbp/flashscore/command_listener.log', 'bet356live-info')

rdb = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)

def check_statistics_activity():
    num = 0
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    for pid in pids:
        try:
            proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
            if "collector_statistics" in proces_name and '/bin/sh' not in proces_name:
                num += 1
        except IOError:
            continue

    if common.statistics_num - num != 0:
        for i in range(common.statistics_num):
            # cmd = 'python3 {}parser/classes/collector_statistics.py ({})'.format(project_root_path, i)  #
            cmd = 'python3.4 {}parser/classes/collector_statistics.py ({})'.format(project_root_path, i)
            subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)


def check_league_activity():
    active = False
    pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
    for pid in pids:
        try:
            proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
            if "collector_leagues" in proces_name and '/bin/sh' not in proces_name:
                active = True
        except IOError:
            continue

    if (active is False and (not rdb.get("parse_teams") or len(rdb.smembers('team_links')) != 0 or not rdb.get("parse_leagues"))) or rdb.get("leagues_active") == "False":
        # relaunch_cmd = "python3 {}parser/classes/collector_leagues.py".format(project_root_path)
        relaunch_cmd = "python3.4 {}parser/classes/collector_leagues.py".format(project_root_path)
        subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
        time.sleep(1)


if __name__ == '__main__':

    check_statistics_activity()

    check_league_activity()

