import sys
from config import *
import util
import common
import time
import subprocess
import shlex
import os
import signal
import datetime
from lookup.sports import rev

import redis

if __name__ == '__main__':
	if hostname in common.master_servers and not util.check_local_dev():

		command_listener_log = util.parserLog('/var/log/sbp/flashscore/command_listener.log', 'bet356live-info')

		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				tst = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()

				for filename in ['emmiter']:
					if filename in str(tst):
						allready_running = True

			except IOError:  # proc has already terminated
				continue

		# pokretanje enqueuera
		for h_ in list(endpoint_rdb_ch_sets.keys()):
			cmd = 'python3 {}workers/enqueuer.py {} {} {}'.format(project_root_path, h_, endpoint_rdb_ch_sets[h_]['endpoint'], endpoint_rdb_ch_sets[h_]['publish_ch'])
			subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)

		# pokretanje single emitera
		cmd = 'python3 {}workers/single_emmiter.py'.format(project_root_path)
		subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)

		# pokretanje collector emitera
		cmd = 'python3 {}workers/collector_emmiter.py'.format(project_root_path)
		subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)

		# pokretanje kolektora
		for sport in common.tip_bet_allowed_sports:
			# print("\nPokrenut Kolektor[{}] - {}".format(sport, datetime.datetime.now().time()))
			cmd = 'xvfb-run -a python3 {}classes/collector.py {}'.format(project_root_path, sport) #
			r = subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
			time.sleep(.2)

		# pokretanje workera
		# todo: dovrsiti, kad se sredi inactive_single_process odkomentarisati
		# cmd = 'python3 {}workers/inactive_single_process.py'.format(project_root_path)
		# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
	elif hostname in common.node_servers and not util.check_local_dev():

		log_file_loc = '/var/log/sbp/flashscore/command_listener.log'
		command_listener_log = util.parserLog(log_file_loc, 'bet356live-info')

		this_node = None

		for node in nodes:
			if node['id'] == hostname:
				this_node = node
				break

		# pokretanje single_process_checkera
		cmd = 'python3 {}workers/single_process_checker.py'.format(project_root_path)
		subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)

		# pokretanje selektovanih single prozora
		redis = redis.StrictRedis(host=redis_master_host, port=redis_master_port, decode_responses=True, password=redis_pass)
		ae_r_keys = redis.keys("{}*".format(this_node['r_channels']['selected_events']))
		removed_keys = redis.keys("single_removed_*")

		splited_removed_keys = []
		for x in removed_keys:
			key_split = x.split("@")[1]
			splited_removed_keys.append(key_split)

		for ar_r_key in ae_r_keys:
			all_selected_on_node_sport = redis.smembers(ar_r_key)
			if all_selected_on_node_sport:
				for ev_hash in list(all_selected_on_node_sport):
					if ev_hash not in splited_removed_keys:
						ev_sport = rev[int(ar_r_key.split("@")[1])]
						msg = "Single window reopened. [{}-{}]".format(ev_hash, ev_sport)
						util.open_single_event(ev_hash, ev_sport)
						command_listener_log.info(msg)
						time.sleep(1)

	else:
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if "single_emmiter" in proces_name or "collector_emmiter" in proces_name or "enqueuer" in proces_name:
					kill_cmd = "kill -9 {}".format(pid)
					subprocess.Popen(shlex.split(kill_cmd), stderr=None, stdout=None)
					time.sleep(0.2)
			except IOError:  # proc has already terminated
				continue

		time.sleep(.2)

		m_command_listener_log = util.parserLog('/var/log/sbp/flashscore/command_listener.log', 'bet356live-info')

		hostname = socket.gethostname()

		for h_ in list(endpoint_rdb_ch_sets.keys()):
			cmd_enq = 'python3 {}workers/enqueuer.py {} {} {}'.format(project_root_path, h_, endpoint_rdb_ch_sets[h_]['endpoint'], endpoint_rdb_ch_sets[h_]['publish_ch'])
			subprocess.Popen(shlex.split(cmd_enq), stderr=None, stdout=None)

		# pokretanje single emitera
		cmd_si_em = 'python3 {}workers/single_emmiter.py'.format(project_root_path)
		subprocess.Popen(shlex.split(cmd_si_em), stderr=None, stdout=None)

		# pokretanje collector emitera
		cmd_col_em = 'python3 {}workers/collector_emmiter.py'.format(project_root_path)
		subprocess.Popen(shlex.split(cmd_col_em), stderr=None, stdout=None)


		# pokretanje kolektora
		for sport in common.tip_bet_allowed_sports:
			# print("\nPokrenut Kolektor[{}] - {}".format(sport, datetime.datetime.now().time()))
			cmd = 'python3 {}classes/collector_leagues.py {}'.format(project_root_path, sport)#
			allready_running = None
			pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			for pid in pids:
				try:
					tst = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()

					for filename in ["collector.py {}".format(sport)]:
						if filename in str(tst):
							allready_running = True

				except IOError:  # proc has already terminated
					continue

			if not allready_running:
				r = subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
			time.sleep(.2)

		# # pokretanje single_process_checkera
		# cmd = 'python3 {}workers/single_process_checker.py'.format(project_root_path)
		# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
		#
		# # pokretanje workera
		# # todo: dovrsiti, kad se sredi inactive_single_process odkomentarisati
		# #cmd = 'python3 {}workers/inactive_single_process.py'.format(project_root_path)
		# #subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
		#
		# # node
		# log_file_loc = '/var/log/sbp/flashscore/command_listener.log'
		# s_command_listener_log = util.parserLog(log_file_loc, 'bet356live-info')
		#
		# this_node = nodes[0]
		# redis = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)
		#
		# ae_r_keys = redis.keys("{}*".format(this_node['r_channels']['selected_events']))
		# removed_keys = redis.keys("single_removed_*")
		#
		# splited_removed_keys = []
		# for x in removed_keys:
		# 	key_split = x.split("@")[1]
		# 	splited_removed_keys.append(key_split)
		#
		# for ar_r_key in ae_r_keys:
		# 	all_selected_on_node_sport = redis.smembers(ar_r_key)
		# 	if all_selected_on_node_sport:
		# 		for ev_hash in list(all_selected_on_node_sport):
		# 			if ev_hash not in splited_removed_keys:
		# 				ev_sport = rev[int(ar_r_key.split("@")[1])]
		# 				msg = "Single window reopened. [{}-{}]".format(ev_hash, ev_sport)
		# 				print(msg)
		# 				util.open_single_event(ev_hash, ev_sport)
		# 				s_command_listener_log.info(msg)
		# 				time.sleep(1)