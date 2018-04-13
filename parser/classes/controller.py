import redis
import sys
import subprocess
import shlex
import time
import os

sys.path.insert(0, '../')
from lookup.sports import *
from config import *
import common

import util
import psutil


class MasterController(object):
	"""bet 365 master command controller"""

	def __init__(self, log=None, host=None):

		if not host:
			host = 'localhost'

		self.redis = redis.StrictRedis(host=host, port=redis_master_port, decode_responses=True, password=redis_pass)
		self.cached_commands = []
		self.current_node = None
		self.message = None
		self.current_node_event_count = None
		self.logger = log
		self.process_checker_counter = 0

	def get_status(self, ev_property=None, ev_hash=None, ev_sport=None):
		""" uzimanje statusa node-ova, vraca spisak nodova i broj evenata na njima """

		if ev_property:

			if ev_property == 'count':
				total_event_count = 0
				for node in nodes:
					node_event_count = self.redis.get(node['r_channels']['event_count'])
					if not node_event_count:
						node_event_count = 0
					else:
						node_event_count = int(node_event_count)
					total_event_count += node_event_count
				if total_event_count < common.max_opened_events:
					return True
				else:
					msg = "Dostignut je maksimalni broj otvorenih dogadjaja, get_status({}), ev_hash={}.".format(ev_property, ev_hash)
					self.logger.critical(msg)

			elif ev_property == 'opened' or ev_property == 'not_finished':

				redis_key = None
				if ev_property == 'opened':
					redis_key = "{}@{}".format(common.redis_channels['selected_events'], ev_sport)
					log_error_msg = "Event {} je vec otvoren, get_status({}).".format(ev_hash, ev_property)
				else:
					redis_key = "{}@{}".format(common.redis_channels['finished_events'], ev_sport)
					log_error_msg = "Event {} je vec zavrsen, get_status({})".format(ev_hash, ev_property)

				if not self.redis.smembers(redis_key):
					return True

				hashes = list(self.redis.smembers(redis_key))
				if hashes:
					if ev_hash not in hashes:
						return True

				self.logger.critical(log_error_msg)

			elif ev_property == 'available':

				ae_r_key = "{}@{}".format(common.redis_channels['available_events'], ev_sport)
				if self.redis.smembers(ae_r_key):
					curr_sport_hashes = list(self.redis.smembers(ae_r_key))
					if ev_hash in curr_sport_hashes:
						return True

				msg = "Event {} se ne nalazi u listi dostupnih, get_status({}).".format(ev_hash, ev_property)
				self.logger.critical(msg)

	@staticmethod
	def get_event_hash(command):

		if "," in command.split("|")[1].split(":")[1]:
			event_hash_and_sport = list(map(str, command.split("|")[1].split(":")[1].split(",")))
			if isinstance(event_hash_and_sport, list):
				if len(event_hash_and_sport) == 2:
					event_hash_and_sport[0] = str(sports[event_hash_and_sport[0]])
					return event_hash_and_sport
		else:
			return [None, str(command.split("|")[1].split(":")[1])]

		return None

	def get_event_node(self, ev_hash):
		""" vraca node na kojem se nalazi event """
		self.current_node = None
		for node in nodes:
			if self.redis.keys("{}*".format(node['r_channels']['selected_events'])):
				se_r_keys = list(self.redis.keys("{}*".format(node['r_channels']['selected_events'])))
				for se_r_key in se_r_keys:
					all_selected_on_node_sport = self.redis.smembers(se_r_key)
					if all_selected_on_node_sport:
						if ev_hash in all_selected_on_node_sport:
							self.current_node = node
							return str(se_r_key.split("@")[1])

		self.logger.critical("Doslo je do greske pri vracanju noda: {}".format(ev_hash))

	def get_balanced_node(self):

		self.current_node = None
		nodes_count = []
		for node in nodes:
			node_event_count = self.redis.get(node['r_channels']['event_count'])
			if not node_event_count:
				node_event_count = 0
			else:
				node_event_count = int(node_event_count)
			nodes_count.append([node_event_count, node])

		reversed_nodes_count = sorted(nodes_count, key=lambda x: x[0], reverse=False)
		self.current_node = reversed_nodes_count[0][1]
		self.current_node_event_count = reversed_nodes_count[0][0]

	def prepare_data(self):
		""" pripremanje komande za obavestavanje node-ova """
		pass

	def notify(self, payload):
		""" slanje komande """
		""" slanje poruke na admin """
		""" emitovanje sistemske poruke, nema veze sa mecevima, npr iskljuci node """

		self.message = None
		client_main_channel = self.current_node['r_channels']['commands']
		if self.current_node['type'] == 'node' and payload['command_type'] == 'event':
			self.message = "{}:{}:{}".format(payload['command'], payload['sport'], payload['hash'])
		elif self.current_node['type'] == 'node' and payload['command_type'] == 'system' and payload['command'] != 'resend':
			self.message = payload['command']
		elif self.current_node['type'] == 'node' and payload['command_type'] == 'tools':
			self.message = "{}_____{}_____{}".format(payload['command'], payload['hash'], payload['master_data'])

		if self.message:
			self.redis.lpush(client_main_channel, self.message)
			if payload['command_type'] != 'tools':
				self.logger.info("Notify node: %{}% - {}".format(self.current_node["id"], self.message))

	def exec_sys_command(self, command):

		if command == 'start':

			self.redis.delete('events_resent')
			self.redis.delete(common.redis_channels['singles_stop'])
			for endpoint_ in endpoint_rdb_ch_sets:
				self.redis.ltrim(endpoint_rdb_ch_sets[endpoint_]['publish_ch'], 0, 0)

			cmd_proc = "python3 {}parser/stop.py".format(project_root_path)
			subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
			time.sleep(1)
			cmd_proc = "python3 {}starter.py".format(project_root_path)
			subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
		elif command == 'forced':

			self.redis.set(common.redis_channels['singles_stop'], True)
			for endpoint_ in endpoint_rdb_ch_sets:
				self.redis.ltrim(endpoint_rdb_ch_sets[endpoint_]['publish_ch'], 0, 0)

			print("2. setovani hash-evi za slanje nula, spavam 4 sekunde")
			for node in nodes:
				ae_r_keys = self.redis.keys("{}*".format(node['r_channels']['selected_events']))
				for ar_r_key in ae_r_keys:
					all_selected_on_node_sport = self.redis.smembers(ar_r_key)
					if all_selected_on_node_sport:
						for ev_hash in list(all_selected_on_node_sport):
							if not len(self.redis.keys("single_removed_flag_*{}".format(ev_hash))):
								self.redis.sadd("events_for_reset", ev_hash)
							else:
								print("ovaj je u removed: {}".format(ev_hash))

			time.sleep(5)
			cmd_proc = "python3 {}parser/stop.py".format(project_root_path)
			subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
			self.redis.delete('events_resent')
			self.redis.delete(common.redis_channels['singles_stop'])
			return

		elif command == 'resend':
			# for endpoint_ in endpoint_rdb_ch_sets:
				# self.redis.ltrim(endpoint_rdb_ch_sets[endpoint_]['publish_ch'], 0, 0)
			self.set_events_for_data_flush()

	def force_open_on_reload_btn(self, ev_sport=None, ev_hash=None):
		if ev_sport and ev_hash:
			self.get_balanced_node()
			data = {
				'sport': ev_sport,
				'hash': ev_hash,
				'command': 'open',
				'command_type': 'event'
			}
			self.notify(data)
		else:
			self.logger.info("Pokusao da otvorim event: {}, sport: {}.".format(ev_hash, ev_sport))

	def set_events_for_data_flush(self, ev_hash=None):
		""" ovde izdajem komandu da se izbrise prethodno sve na kvotama, postavi nule """

		if ev_hash:

			self.redis.sadd(common.redis_channels['flush_data'], str(ev_hash))
			self.logger.info("Flush data + reload: {}".format(ev_hash))
		else:

			for node in nodes:
				event_r_keys = list(self.redis.keys("{}*".format(node['r_channels']['selected_events'])))
				for event_r_key in event_r_keys:
					all_selected_on_node_sport = self.redis.smembers(event_r_key)
					if all_selected_on_node_sport:
						for ev_hash in all_selected_on_node_sport:
							self.redis.sadd(common.redis_channels['flush_data'], str(ev_hash))
							# print("dodao za flush sa nodovih izabranih: {}".format(ev_hash))

			for sport in common.tip_bet_allowed_sports:
				util.redis_add_to_collection(self.redis, common.redis_channels['flush_collector_data'], normalized_sport[str(sport)])

			self.restart_emmiter(int(time.time()))
			self.logger.info("Global flush.")

	def restart_emmiter(self, ts):

		# restart collector_emmiter.py
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		try:
			for pid in pids:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if "collector_emmiter" in proces_name and 'tail' not in proces_name and '/bin/sh' not in proces_name:
					kill_cmd = "kill -9 {}".format(pid)
					subprocess.Popen(shlex.split(kill_cmd), stderr=None, stdout=None)
					time.sleep(.5)
					cmd_proc = "python3 {}workers/collector_emmiter.py".format(project_root_path)
					subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
					self.logger.info("Restartovan collector_emmiter.")
					return
		except:
			print("\n\n\nPUKAO RESTART EMMITER\n\n\n")

		# if not self.redis.keys("predicted_ft_*") and not self.redis.keys("remove_single_*"):
		# 	pass
		# restart single_emmiter.py

			# while True:
			# 	if int(time.time()) - ts >= 3:
			# 		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			# 		for pid in pids:
			# 			try:
			# 				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
			# 				if "emmiter" in proces_name and 'tail' not in proces_name and '/bin/sh' not in proces_name:
			# 					kill_cmd = "kill -9 {}".format(pid)
			# 					subprocess.Popen(shlex.split(kill_cmd), stderr=None, stdout=None)
			# 					time.sleep(.5)
			# 					cmd_proc = "python3 {}workers/emmiter.py".format(project_root_path)
			# 					subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
			# 					self.logger.info("Restartovan emmiter.")
			# 					return
			# 			except IOError:
			# 				continue
			# 		return

	def get_overview(self):
		""" dobijanje svih informacija o redis bazi """
		pass

	def reassemble_nodes(self):
		""" prepakivanje meceva po nodovima (na primer u slucaju pada jednog od node-ova) """
		pass

	def backup_system_status(self):
		""" kreiranje snapshot-a redis baze da bi u slucaju pada celog sistema imali poslednje radno stanje,
		razmisliti o ucestalosti """
		pass

	def run_process_checker(self):
		"""startovanje process_checker-a svaki minut  (1min = 120, na posla sekunde ide +1)"""
		self.process_checker_counter += 1
		if self.process_checker_counter == 120:
			cmd = 'python3 {}workers/process_checker.py'.format(project_root_path)
			subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
			self.process_checker_counter = 0
			# logovanje svakog process_checker-a je pretrpavalo log nepotrebno, zakomentarisan log


class SlaveController(object):
	"""
		bet 365 SLAVE command controller
	"""

	def __init__(self, log=None):
		self.redis = redis.StrictRedis(host=redis_master_host, port=redis_master_port, decode_responses=True, password=redis_pass)
		self.logger = log
		self.logger.info("Controller started.")

	@staticmethod
	def exec_sys_command(command):

		if command == 'start':
			cmd_proc = "python3 {}parser/stop.py".format(project_root_path)
			subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
			time.sleep(1.5)
			cmd_proc = "python3 {}starter.py".format(project_root_path)
			subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)
		elif command == 'forced':

			cmd_proc = "python3 {}parser/stop.py".format(project_root_path)
			subprocess.Popen(shlex.split(cmd_proc), stderr=None, stdout=None)

	def exec_event_command(self, command, ev_hash, ev_sport, single_log):

		if command == "open":

			msg = "Single window opened. [{}-{}]".format(ev_hash, ev_sport)
			util.open_single_event(ev_hash, ev_sport)
			self.logger.info(msg)

		elif command == "reload":

			pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			for pid in pids:
				try:
					proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
					if ev_hash in proces_name and 'tail' not in proces_name and '/bin/sh' not in proces_name:
						kill_cmd = "kill -9 {}".format(pid)
						subprocess.Popen(shlex.split(kill_cmd), stderr=None, stdout=None)
						time.sleep(1)
				except IOError:
					continue
			se_r_key = "{}@{}".format(common.redis_channels['selected_events'], str(sports[ev_sport]))
			selected_events = list(self.redis.smembers(se_r_key))
			if ev_hash in selected_events:
				msg = "Single window RESTARTED. [{} - {}]".format(ev_hash, ev_sport)
				util.open_single_event(ev_hash, ev_sport)
				self.logger.info(msg)
				print(msg)

		elif command == "kill":

			pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			for pid in pids:
				try:
					proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
					if ev_hash in proces_name and 'tail' not in proces_name and '/bin/sh' not in proces_name:
						relaunch_cmd = "kill -9 {}".format(pid)
						subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
						msg = "Single window KILLED. [{}-{}]".format(ev_hash, ev_sport)
						# single_log.info(msg)
						self.logger.info(msg)
						print(msg)
				except IOError:
					continue

	# @staticmethod
	# def exec_tool_command(command, ev_hash):
	#
	# 	return LogParser(cmd=command, ev_hash=ev_hash)

	def node_status(self):

		this_node = None
		command_listener = 0

		for node in nodes:
			if node['id'] == hostname:
				this_node = node

		# print(this_node['id'])
		node_status_num = self.redis.keys("check_node_status_{}".format(this_node['id']))
		if len(node_status_num):
			loadavg = os.getloadavg()
			ram = psutil.virtual_memory()
			cpu = psutil.cpu_times()
			htop = "LOAD AVERAGE: {}\nMEMORY: {}\nCPU: {}\n".format(loadavg, ram, cpu)

			pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
			for pid in pids:
				try:
					proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
					if "command_listener.py" in proces_name and 'tail' not in proces_name and '/bin/sh' not in proces_name:
						command_listener += 1
				except IOError:
					continue

			vpn = subprocess.Popen(["expressvpn", "status"], stdout=subprocess.PIPE).communicate()[0]

			node_status = "{}#{}#{}".format(command_listener, htop, vpn)
			self.redis.set("get_node_status_{}".format(this_node['id']), node_status)
			self.redis.delete("check_node_status_{}".format(this_node['id']))
