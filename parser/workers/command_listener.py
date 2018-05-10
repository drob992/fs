#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import redis
import time
import sys

sys.path.insert(0, '../')
import util
from config import *
import common
import classes.controller as controller
from lookup.sports import rev

def command_time_span(rdb, command):
	last_cmd_ts = None
	new_ts = int(time.time())

	if command == "start":
		last_cmd_ts = rdb.get("sys_cmd_start_ts")
		if last_cmd_ts is None or new_ts - int(last_cmd_ts) > 12:
			rdb.set("sys_cmd_start_ts", new_ts)
			print("\nSTART {} {}\n".format(new_ts, last_cmd_ts))
			return True

	elif command == "forced":
		last_cmd_ts = rdb.get("sys_cmd_forced_ts")
		if last_cmd_ts is None or new_ts - int(last_cmd_ts) > 9:
			rdb.set("sys_cmd_forced_ts", new_ts)
			print("\nFORCED {} {}\n".format(new_ts, last_cmd_ts))
			return True

	elif command == "resend":
		last_cmd_ts = rdb.get("sys_cmd_resend_ts")
		if last_cmd_ts is None or new_ts - int(last_cmd_ts) > 6:
			rdb.set("sys_cmd_resend_ts", new_ts)
			print("\nRESEND {} {}\n".format(new_ts, last_cmd_ts))
			return True

	print("\nSlanje komande '{}' nije proslo, zato sto je command_time_span nije dozvolio. Stara komanda: {}, nova komanda: {}\n".format(command, last_cmd_ts, new_ts))

	return False

if __name__ == '__main__':

	rdb = redis.StrictRedis(host=redis_master_host, port=redis_master_port, decode_responses=True, password=redis_pass)
	rdb.delete('1_server_dev')

	try:
		local_env = sys.argv[1]
	except:
		local_env = input("Local dev on multiple server? [Y/n]\n")

	if local_env == 'Y' or local_env == 'y' or len(local_env) == 0:
		util.rem_local_dev(rdb)
	else:
		util.set_local_dev(rdb)
		time.sleep(1)

	# # todo: provera da li rade redis serveri
	# if hostname in common.master_servers and not util.check_local_dev():
	#
	# 	# todo:
	# 	logger_filepath = '/var/log/sbp/flashscore/m_controller.log'
	# 	controller_logger = util.parserLog(logger_filepath, 'tip_bet-command_listener.py-controller')
	# 	controller = controller.MasterController(log=controller_logger)
	# 	admin_messages = redis.StrictRedis(host=redis_admin_host, port=redis_admin_port, decode_responses=True, password=redis_pass)
	# 	controller_logger.info("Pokrenut kontroler.")
	#
	# 	while True:
	#
	# 		cmd = admin_messages.rpop(admin_redis_ch)
	# 		if cmd:
	#
	# 			command_key = None
	# 			if "|" in cmd:
	# 				command_key = cmd.split("|")[0]
	# 				command = cmd.split("|")[1].split(":")[0]
	# 			else:
	# 				command = cmd
	#
	# 			if command_key in list(common.available_commands.keys()):
	# 				if command in common.available_commands[command_key]:
	# 					if command_key == 'system':
	# 						cmd_time_span = command_time_span(rdb, command)
	# 						if cmd_time_span:
	# 							for node in nodes:
	# 								if node['type'] == 'node':
	# 									controller.current_node = node
	# 									data = {
	# 										'command': command,
	# 										'command_type': command_key
	# 									}
	# 									controller.exec_sys_command(command)
	# 									controller.notify(data)
	#
	# 					elif command_key == 'event':
	#
	# 						ev_sport, ev_hash = controller.get_event_hash(cmd)
	#
	# 						controller.current_node = None
	# 						if command == 'open':
	# 							if controller.get_status('count', None, None) and \
	# 									controller.get_status('opened', ev_hash, ev_sport) and \
	# 									controller.get_status('available', ev_hash, ev_sport) and \
	# 									controller.get_status('not_finished', ev_hash, ev_sport):
	# 								controller.get_balanced_node()
	# 						else:
	# 							controller.get_event_node(ev_hash)
	#
	# 						if controller.current_node and ev_sport and ev_hash:
	# 							data = {
	# 								'sport': ev_sport,
	# 								'hash': ev_hash,
	# 								'command': command,
	# 								'command_type': command_key
	# 							}
	# 							controller.notify(data)
	#
	# 							if command == 'reload':
	# 								controller.set_events_for_data_flush(ev_hash)
	#
	# 						else:
	# 							controller_logger.critical("Nije detektovan node za dalju akciju: {}".format(cmd))
	# 							controller_logger.critical("Sport: {}, hash: {}".format(ev_sport, ev_hash))
	# 							controller.force_open_on_reload_btn(ev_sport=ev_sport, ev_hash=ev_hash)
	# 					else:
	# 						controller_logger.critical("Nije hendlovana komanda: {}".format(cmd))
	# 				else:
	# 					msg = "Poznat kljuc: {}, nepoznata komanda {}".format(command_key, command)
	# 					controller_logger.critical(msg)
	# 			else:
	# 				msg = "nepoznata komanda, loguj: {}".format(cmd)
	# 				controller_logger.critical(msg)
	#
	# 		controller.run_process_checker()
	#
	# 		time.sleep(.1)
	#
	# elif hostname in common.node_servers and not util.check_local_dev():
	#
	# 	this_node = None
	# 	for node in nodes:
	# 		if node['id'] == hostname:
	# 			this_node = node
	# 			break
	#
	# 	logger_filepath = '/var/log/sbp/flashscore/controller_{}.log'.format(this_node['id'])
	# 	controller_logger = util.parserLog(logger_filepath, 'tip_bet-node-controller')
	# 	controller = controller.SlaveController(log=controller_logger)
	# 	commands_ch = this_node['r_channels']['commands']
	#
	# 	while True:
	# 		command_received = controller.redis.rpop(commands_ch)
	# 		if command_received:
	#
	# 			if command_received in common.available_commands['system']:
	#
	# 				cmd = command_received
	# 				msg = 'Parser {}.'.format(cmd.upper())
	# 				controller_logger.info(msg)
	#
	# 				controller.exec_sys_command(cmd)
	#
	# 			else:
	#
	# 				command_split = command_received.split(":")
	# 				cmd = command_split[0]
	#
	# 				if cmd in common.available_commands['event']:
	#
	# 					if command_split[1] not in ["Football", "Tennis", "Basketball", "Hockey", "Volleyball", "Handball", "Waterpolo"]:
	# 						ev_sport = rev[int(command_split[1])]
	# 					else:
	# 						ev_sport = command_split[1]
	# 					ev_hash = command_split[2]
	#
	# 					single_log_loc = '/var/log/sbp/flashscore/single_{}.log'.format(ev_hash)
	# 					single_log = util.parserLog(single_log_loc, 'tip_bet-info')
	#
	# 					controller.exec_event_command(cmd, ev_hash, ev_sport, single_log)
	#
	# 				else:
	#
	# 					command_split = command_received.split("_____")
	# 					cmd = command_split[0]
	# 					ev_hash = command_split[1]
	# 					data = command_split[2]
	#
	# 					if cmd in common.available_commands['tools']:
	#
	# 						log_file_path = "/var/log/sbp/flashscore/single_{}.log".format(ev_hash)
	#
	# 		controller.node_status()
	#
	# 		time.sleep(.1)

	# else:

	print("localhost development")

	# master cmd listener init
	logger_filepath = '/var/log/sbp/flashscore/m_controller.log'
	m_controller_logger = util.parserLog(logger_filepath, 'tip_bet-command_listener.py-controller')
	m_controller = controller.MasterController(log=m_controller_logger)
	admin_messages = redis.StrictRedis(host=redis_admin_host, port=redis_admin_port, decode_responses=True, password=redis_pass)
	m_controller_logger.info("Pokrenut kontroler.")

	# slave cmd listener init
	this_node = nodes[0]
	logger_filepath = '/var/log/sbp/flashscore/controller_{}.log'.format(this_node['id'])
	s_controller_logger = util.parserLog(logger_filepath, 'tip_bet-node-controller')
	s_controller = controller.SlaveController(log=s_controller_logger)
	commands_ch = this_node['r_channels']['commands']

	while True:

		# master cmd listener start
		cmd = admin_messages.rpop(admin_redis_ch)
		# print("master cmd: {}".format(cmd))
		if cmd:

			command_key = None
			if "|" in cmd:
				command_key = cmd.split("|")[0]
				command = cmd.split("|")[1].split(":")[0]
			else:
				command = cmd

			if command_key in list(common.available_commands.keys()):
				if command in common.available_commands[command_key]:

					if command_key == 'system':

						cmd_time_span = command_time_span(rdb, command)
						if cmd_time_span:
							for node in nodes:
								if node['type'] == 'node':
									m_controller.current_node = node
									data = {
										'command': command,
										'command_type': command_key
									}
									m_controller.exec_sys_command(command)
									m_controller.notify(data)

					elif command_key == 'event':

						ev_sport, ev_hash = m_controller.get_event_hash(cmd)

						controller.current_node = None
						if command == 'open':
							if m_controller.get_status('count', None, None) and \
									m_controller.get_status('opened', ev_hash, ev_sport) and \
									m_controller.get_status('available', ev_hash, ev_sport) and \
									m_controller.get_status('not_finished', ev_hash, ev_sport):
								m_controller.get_balanced_node()
						else:
							m_controller.get_event_node(ev_hash)

						if m_controller.current_node and ev_sport and ev_hash:
							data = {
								'sport': ev_sport,
								'hash': ev_hash,
								'command': command,
								'command_type': command_key
							}
							m_controller.notify(data)

							if command == 'reload':
								m_controller.set_events_for_data_flush(ev_hash)

						else:
							m_controller_logger.critical("Nije detektovan node za dalju akciju: {}".format(cmd))
							m_controller_logger.critical("Sport: {}, hash: {}".format(ev_sport, ev_hash))
							m_controller.force_open_on_reload_btn(ev_sport=ev_sport, ev_hash=ev_hash)
					else:
						m_controller_logger.critical("Nije hendlovana komanda: {}".format(cmd))
				else:
					msg = "Poznat kljuc: {}, nepoznata komanda {}".format(command_key, command)
					m_controller_logger.critical(msg)
			else:
				msg = "nepoznata komanda, loguj: {}".format(cmd)
				m_controller_logger.critical(msg)

		m_controller.run_process_checker()
		# slave cmd listener start
		command_received = s_controller.redis.rpop(commands_ch)
		# print("node cmd: {}".format(command_received))
		if command_received:

			if command_received in common.available_commands['system']:

				cmd = command_received
				msg = 'Parser {}.'.format(cmd.upper())
				s_controller_logger.info(msg)

				s_controller.exec_sys_command(cmd)

			else:

				command_split = command_received.split(":")
				cmd = command_split[0]

				if cmd in common.available_commands['event']:

					if command_split[1] not in ["Football", "Tennis", "Basketball"]:
						ev_sport = rev[int(command_split[1])]
					else:
						ev_sport = command_split[1]
					ev_hash = command_split[2]

					single_log_loc = '/var/log/sbp/flashscore/single_{}.log'.format(ev_hash)
					single_log = util.parserLog(single_log_loc, 'tip_bet-info')

					s_controller.exec_event_command(cmd, ev_hash, ev_sport, single_log)
				else:

					command_split = command_received.split("_____")
					cmd = command_split[0]
					ev_hash = command_split[1]
					data = command_split[2]

		time.sleep(.1)
