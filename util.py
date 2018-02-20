import subprocess
import shlex
import hashlib
import random
import logging
import os.path
import re
import redis
import json
import time
from random import choice

import sys
from PyQt5.QtNetwork import *
from logging.handlers import TimedRotatingFileHandler

# import config

import config
import common
import datetime
import collections
import functools

from tornado import httpclient
import urllib
import urllib.parse


def memoize(obj):
	"""
	From Python Decorator Library
	"""
	cache = obj.cache = {}

	@functools.wraps(obj)
	def memoizer(*args, **kwargs):
		key = str(args) + str(kwargs)
		if key not in cache:
			cache[key] = obj(*args, **kwargs)
		return cache[key]
	return memoizer


def simulate_click(btn):
	tmp_js = "this.click();"
	# btn.setAttribute('onclick', tmp_js)
	btn.evaluateJavaScript(tmp_js)


def check_suspended(quota):
	if not quota.parent().hasClass("ipe-Participant_Suspended"):
		return quota.toPlainText().strip()
	else:
		return '0'


def handicap_round_detect(handicaps_parsed, step=0):
	"""
	:description:  metod za vracanje sufix-a za svaku iteraciju hendikepa ili slicne igre
	:param handicaps_parsed:
	:return:
	"""
	#todo, impl steping
	if step == 1:
		alphabet_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
		# alphabet_list = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"]
	else:
		alphabet_list = ["", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
		# alphabet_list = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"]

	roundCharacter = alphabet_list[len(handicaps_parsed) - 1]
	return str(roundCharacter)


def handicap_round_detect_number(handicaps_parsed, step=0):
	"""
	:description:  metod za vracanje sufix-a za svaku iteraciju hendikepa ili slicne igre
	:param handicaps_parsed:
	:return:
	"""
	#todo, impl steping
	if step == 1:
		# alphabet_list = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
		number_list = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"]
	else:
		# alphabet_list = ["", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
		number_list = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26"]

	roundCharacter = number_list[len(handicaps_parsed) - 1]
	return str(roundCharacter)


@memoize
def create_group_regex(team, prefix, sufix):
	return r"{}".format(prefix) + re.escape(team) + r"{}".format(sufix)


def hash(string_to_hash):
	hasher = hashlib.sha1()
	hasher.update(string_to_hash.encode('utf-8'))
	return str(int(hasher.hexdigest()[:15], 16))


def generate_event_hash(sport, team1, team2):

	sport = sport.replace(' ', '_')
	team1 = team1.replace(' ', '_')
	team2 = team2.replace(' ', '_')
	str_to_hash = "TIPBET{}{}{}".format(sport, team1, team2)
	return hash(str_to_hash)


def parserLog(file_path, file_name, debug=False):
	logHandler = TimedRotatingFileHandler(file_path, when="midnight")
	logFormatter = logging.Formatter() if debug else logging.Formatter('%(asctime)-6s %(name)s %(module)s %(funcName)s %(lineno)d - %(levelname)s %(message)s')
	logHandler.setFormatter(logFormatter)

	log = logging.getLogger(file_name)
	log.propagate = False
	log.addHandler(logHandler)
	log.setLevel(logging.DEBUG)

	return log


def generate_cookie():
	chars = ['A', 'B', 'C', 'D', 'E', 'F', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
	pstk = ""
	for i in range(32):
		pstk += str(random.choice(chars))
	pstk += '000003'
	cookie = bytearray("pstk={}; session=processform=0; aps03=lng=1&tzi=1&ct=240&cst=0&cg=0&oty=1".format(pstk), 'utf-8')
	return cookie


def is_chinese(teams):

	for team in teams:
		for ch in team:
			if 0x9fff > ord(ch) > 0x4e00:
				return True


class Request(object):
	def __init__(self, base_uri):
		self.base_uri = base_uri

	def post(self, data):
		http_client = httpclient.HTTPClient()
		#** todo: postavljen timeout na 1s kako bi se debagovalo kasnjenje podataka sa parsera
		httprqst = httpclient.HTTPRequest(self.base_uri, method='POST', body=urllib.parse.urlencode({'data': data}), request_timeout=7)
		response = http_client.fetch(httprqst)
		return response.body


def open_single_event(ev_hash, ev_sport):
	print("\n-*-*-*- Pokrenut [{} - {}] - {}".format(ev_hash, ev_sport, datetime.datetime.now().time()))
	cmd = 'xvfb-run -a python3 {}classes/single.py {} {}'.format(config.project_root_path, str(ev_hash), str(ev_sport)) #
	print(cmd, "\n\n")
	subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)


def sync(endpoint=None, redis_ch=None, endpoint_name=None):
	logger = parserLog('/var/log/sbp/flashscores/enqueuer_{}.log'.format(endpoint_name), 'enq-logger-{}'.format(endpoint_name))
	check_for_emmits_interval = .1
	r_server = redis.StrictRedis(host='localhost', port=config.redis_master_port, decode_responses=True, password=config.redis_pass)

	while True:
		feed = None

		try:
			feed = r_server.brpop(redis_ch, timeout=1)
			# print(datetime.datetime.now().time())
			# print(feed)
			if not feed:
				continue

			feed = json.loads(feed[1])

			pending_emmits = r_server.lrange(redis_ch, 0, 1000)

			if len(pending_emmits) > 35:
				r_server.ltrim(redis_ch, 0, 0)

			# if len(pending_emmits) == 0:
			# 	check_for_emmits_interval = .1
			# else:
			# 	check_for_emmits_interval = .1

			try:
				print("Q:S = {}:{} -> {}".format(len(pending_emmits), len(feed), endpoint_name))
				Request(endpoint).post(json.dumps(feed))
			except Exception as err3:
				print("A.request - {}     *****     {}".format(endpoint_name, datetime.datetime.now().time()))
				logger.critical("A.request - {}:\n{}".format(endpoint_name, err3))
				r_server.ltrim(redis_ch, 0, 0)
			logger.critical(json.dumps(feed))

		except Exception as e:
			print('error: {}, {}  --  {}'.format(e, endpoint, datetime.datetime.now().time()))
			logger.critical(e)
			logger.critical(json.dumps(feed))
			for hash_ in feed:
				if "time" in feed[hash_] and feed[hash_]["time"] in ["removed", "FT"] or "toggle_state" in feed[hash_]:
					Request(endpoint).post(json.dumps({hash_: feed[hash_]}))

		time.sleep(check_for_emmits_interval)


def validate_live_event_prop(prop, val):

	if prop == 'time':

		valid = False
		# print(val)
		try:
			if re.search(r'^[0-9]{0,2}\'$', val):
				valid = True
			elif re.search(r'^[0-9]{0,2}\'\+?[0-9]{1,2}$', val):
				valid = True
			elif re.search(r'^[1-9]{1}[a-z]{2}$', val):
				valid = True
			elif val in ['FT', 'HT', 'removed']:
				valid = True
		except Exception as e:
			print('EEEEE: \n{}'.format(e))

		return valid

	elif prop == 'current_score':
		if not re.search(r'^[0-9]{1,3}:+[0-9]{1,3}$', val):
			return False
	elif prop == 'redcards':
		if not re.search(r'^.*[0-9]{1,2}.*$', val):
			return False
	elif prop == 'yellowcards':
		if not re.search(r'^.*[0-9]{1,2}.*$', val):
			return False
	else:
		if len(str(val)) == 0:
			return False

	return True


# ==================================================================================================================== #


def redis_exists(rdb, r_key, ev_hash=False):
	if rdb.smembers(r_key):
		if not ev_hash:
			return True
		else:
			if ev_hash in list(rdb.smembers(r_key)):
				return True


def redis_add_to_collection(rdb, r_key, ev_hash):
	rdb.sadd(r_key, ev_hash)


def redis_remove_from_collection(rdb, r_key, ev_hash):
	rdb.srem(r_key, ev_hash)


def redis_emmit(rdb, event_hash, event, collector=None):
	if not isinstance(event, dict):
		event = event.__dict__

	keys_to_remove = ['cache', 'timejump', 'three_time_open_event', 'node', 'packed_score']
	for x in keys_to_remove:
		if x in list(event.keys()):
			del event[x]

	for key in list(event.keys()):
		# rdb.sadd('rle@main_obj_keys', key)
		if key != 'odds':
			if not validate_live_event_prop(key, str(event[key])):
				print("\nne emitujem: {}    {}:{}    {}: -{}-      {}\n".format(event['sport'], event['team1'], event['team2'], key, str(event[key]), event_hash))
				return

	data = json.dumps({event_hash: event})
	if collector:
		redis_key = 'coll_emmit_{}'.format(event_hash)
	else:
		redis_key = 'single_emmit_{}'.format(event_hash)
		led_key = "ED_{}".format(event_hash)
		e_odds_key = "EOD_{}".format(event_hash)
		for key in event:
			if key == "odds":
				for o_key in event[key]:
					rdb.sadd(e_odds_key, o_key)
			else:
				rdb.hset(led_key, key, event[key])

	rdb.set(redis_key, data)
	expire_key(rdb=rdb, key=redis_key, time=50)

	timestamp = int(str(time.time()).split(".")[0])
	rdb.set("tipbet_last_emmit-{}".format(event_hash), timestamp)
	return data


def redis_get_event_node_and_sport(rdb, event_hash):

	nodes = config.nodes
	for node in nodes:
		event_r_keys = list(rdb.keys("{}*".format(node['r_channels']['selected_events'])))
		for event_r_key in event_r_keys:
			sport_key = str(event_r_key.split("@")[1])
			all_selected_on_node_sport = rdb.smembers(event_r_key)
			if all_selected_on_node_sport:
				if event_hash in all_selected_on_node_sport:
					return [sport_key, node]


def redis_get_collection(rdb, r_key):
	return rdb.smembers(r_key)


def node_kill_event(redis, sport, hash):
	#redis komanda za ubijanje singla
	node_kill_e_message = "kill:{}:{}".format(sport, hash)
	node_cmd_ch = get_curr_node_channels(rdb=redis, ev_hash=hash, key='commands')
	redis.lpush(node_cmd_ch, node_kill_e_message)


def node_open_event(redis, sport, hash):
	#redis komanda za otvaranje singla
	# todo: handle this !!!
	try:
		node_open_e_message = "open:{}:{}".format(sport, hash)
		node_cmd_ch = get_curr_node_channels(rdb=redis, ev_hash=hash, key='commands')
		redis.lpush(node_cmd_ch, node_open_e_message)
	except Exception as e:
		logger_filepath = '/var/log/sbp/flashscores/catched_errors.log'
		error_logger = parserLog(logger_filepath, 'tipbet-live-errors')
		error_logger.critical(e)


def rem_local_dev(rdb):
	rdb.delete('1_server_dev')


def set_local_dev(rdb):
	rdb.set('1_server_dev', True)


def check_local_dev():
	rdb = redis.StrictRedis(host=config.redis_master_host, port=config.redis_master_port, decode_responses=True, password=config.redis_pass)
	if rdb.get('1_server_dev'):
		return True
	return None


def remove_from_liveboard(rdb=None, ev_hash=None):
	rm_dict = {
		'time': 'removed',
		"starttime": "None",
	}
	for h_ in list(config.endpoint_rdb_ch_sets.keys()):
		data = json.dumps({ev_hash: rm_dict})
		rdb.lpush(config.endpoint_rdb_ch_sets[h_]['publish_ch'], data)


def set_curr_node_channels(rdb=None, node=None, ev_hash=None):

	node_host_r_key = "event_node_info_{}".format(ev_hash)
	curr_node_channels = rdb.hgetall(node_host_r_key)
	if not curr_node_channels:
		for key in node["r_channels"]:
			rdb.hset(node_host_r_key, key, node["r_channels"][key])


def get_curr_node_channels(rdb=None, ev_hash=None, key=None):

	node_host_r_key = "event_node_info_{}".format(ev_hash)
	return rdb.hget(node_host_r_key, key)


def hide_quotas_on_liveboard(event_hash=None, enable=None):
	try:
		hide_quotas_dict = {
			"event_hash": event_hash,
			"enabled": None,
			"toggle_state": "0"
		}
		if enable is True:
			hide_quotas_dict["toggle_state"] = "1"

		data = json.dumps(hide_quotas_dict)
		for h_ in list(config.endpoint_rdb_ch_sets.keys()):
			Request(config.endpoint_rdb_ch_sets[h_]['hide_quotas_api']).post(data)
	except Exception as e:
		print("\n\n SAKRIVANJE KVOTA NIJE USPELO: {}\n{}\n".format(event_hash, e))


def expire_key(rdb=None, key=None, time=None):

	if not time:
		time = 25

	rdb.expire(key, time)




def predict_tool(log, sport, main, time):
	#sluzi za slikanje i resetovanje singlova u odredjenim trenutcima
	try:
		if sport == "Football":
			summary = main.findAll(".ml1-TabController_Tab-Summary").at(0)
			if not summary.hasClass("ml1-TabController_TabActive"):
				simulate_click(summary)

			time_full = main.findAll(".ml1-TimelineBar_Time").at(0).toPlainText().strip()
			time_split = time_full.split(":")
			time_minutes = time_split[0]
			time_seconds = time_split[1]

			if int(time_minutes) == 89 and time_seconds == "00":# and (int(time_minutes) > 90 and int(time_minutes) % 3 == 0):
				log.critical("\nVreme je {}:{}, radimo restart".format(time_minutes, time_seconds))
				return "restart"
			if int(time_minutes) > 90 and (time_seconds == "00" or time_seconds == "20" or time_seconds == "40") or time_full in ["90:01", "90:20", "90:40"]:
				log.critical("\nVreme je {}:{}, radimo screenshot".format(time_minutes, time_seconds))
				return "screenshots"

		elif sport == "Basketball":
			quarter = main.findAll(".ml18-ScoreHeader_AdditionalText").at(0).toPlainText().strip()
			time_full = main.findAll(".ml18-ScoreHeader_Clock").at(0).toPlainText().strip()
			if quarter == "Q4" and time_full in ["00:10", "00:00"]:
				log.critical("\nVreme je {}:{}, radimo screenshot".format(quarter, time_full))
				return "screenshots"
			elif quarter == "Q4" and time_full == "00:45":
				log.critical("\nVreme je {}:{}, radimo restart".format(quarter, time_full))
				return "restart"

		elif sport == "Handball":
			time_full = main.findAll(".ml78-ScoreHeader_Clock").at(0).toPlainText().strip()
			if time == "2nd" and time_full in ["60:00", "59:59", "59:30", "59:45"]:
				log.critical("\nVreme je {}:{}, radimo screenshot".format(time, time_full))
				return "screenshots"
			elif time == "1st" and time_full in ["29:59"]:
				log.critical("\nVreme je {}:{}, radimo restart".format(time, time_full))
				return "restart"

		elif sport == "Hockey":
			time_full = main.findAll(".ml17-ScoreHeader_Clock").at(0).toPlainText().strip()
			if time == "3rd" and time_full in ["00:1", "00:15", "00:10", "00:01", "19:50", "19:59", "19:45", "19:59"]:
				log.critical("\nVreme je {}:{}, radimo screenshot".format(time, time_full))
				return "screenshots"
			elif time == "2nd" and time_full in ["00:01", "19:59"] or time == "3rd" and time_full in ["00:40", "19:20"] :
				log.critical("\nVreme je {}:{}, radimo restart".format(time, time_full))
				return "restart"

		elif sport == "NFL":
			time_full = main.findAll(".ml17-ScoreHeader_Clock").at(0).toPlainText().strip()
			if time == "4th" and time_full in ["00:15", "00:10", "00:01"]:
				log.critical("\nVreme je {}:{}, radimo screenshot".format(time, time_full))
				return "screenshots"
			elif time == "2nd" and time_full in ["00:01"]:
				log.critical("\nVreme je {}:{}, radimo restart".format(time, time_full))
				return "restart"

		elif sport == "Waterpolo":
			time_full = main.findAll(".ml110-ScoreHeader_Clock").at(0).toPlainText().strip()
			if time_full in ["00:10", "00:00"]:
				log.critical("\nVreme je {}, radimo screenshot".format(time_full))
				return "screenshots"
			elif time_full == "00:40":
				log.critical("\nVreme je {}, radimo restart".format(time_full))
				return "restart"


	except Exception as e:
		pass

	return False

def football_ft_remove_time_jump(rdb, ot, event_hash, sport, available_event_hashes_timer, available_event_hashes, old_available_event_hashes_timer, log):
	# Kada fudbal ode u produzetke, koristimo ovu funkciju zajedno sa onom na kolektoru da setujemo redis i zavrsimo mec
	if ot not in ["", "half", "end"] and ":" not in ot:
		if "+" in ot:
			ot = ot.split("+")
			ot = int(ot[0].replace(".", "")) + int(ot[1])
		else:
			ot = ot.split(".")[0]

		available_event_hashes_timer[event_hash] = int(ot)

		football_ft_remove_time = rdb.hgetall("football_ft_remove_time_{}".format(event_hash))
		if football_ft_remove_time:
			try:
				ft_remove_time1 = football_ft_remove_time['1']
				ft_remove_time2 = football_ft_remove_time['2']
				rdb.delete("football_ft_remove_time_{}".format(event_hash))
				print("Obrisao football_ft_remove_time_{}".format(event_hash))
				return available_event_hashes
			except:
				if available_event_hashes_timer[event_hash] < old_available_event_hashes_timer and available_event_hashes_timer[event_hash] == 90 and old_available_event_hashes_timer > 90:
					rdb.hset("football_ft_remove_time_{}".format(event_hash), "2", True)
					log.critical("Vreme se vratilo na 90 na kolektoru, setujemo redis za brisanje, {} - {}".format(event_hash, datetime.datetime.now().time()))
					print("Vreme se vratilo na 90 na kolektoru, setujemo redis za brisanje, {} - {}".format(event_hash, datetime.datetime.now().time()))
					available_event_hashes.append(event_hash)
				else:
					available_event_hashes.append(event_hash)
		else:
			if available_event_hashes_timer[event_hash] < old_available_event_hashes_timer and available_event_hashes_timer[event_hash] == 90 and old_available_event_hashes_timer > 90:
				rdb.hset("football_ft_remove_time_{}".format(event_hash), "2", True)
				log.critical("Vreme se vratilo na 90 na kolektoru, setujemo redis za brisanje, {} - {}".format(event_hash, datetime.datetime.now().time()))
				print("Vreme se vratilo na 90 na kolektoru, setujemo redis za brisanje, {} - {}".format(event_hash, datetime.datetime.now().time()))
				available_event_hashes.append(event_hash)
			else:
				available_event_hashes.append(event_hash)
	else:
		available_event_hashes.append(event_hash)

	return available_event_hashes



def football_time_change_checker(main, event, redis, ev_time, log, ev_hash):
	check = True

	if ev_time is None:
		return check

	time_checker_redis = "time_checker_{}".format(ev_hash)

	if ev_time is not None and ev_time not in ["HT", "FT"]:
		try:

			ev_time = ev_time.replace("'", "")
			if "+" in ev_time:
				ev_time_split = ev_time.replace(".", "").split("+")
				ev_time = int(ev_time_split[0]) + int(ev_time_split[1])

			new_time = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip()
			if new_time.lower() in ["half", "end"]:
				new_time = 0
			elif "+" in new_time:
				new_time_split = new_time.replace(".", "").split("+")
				new_time = int(new_time_split[0]) + int(new_time_split[1])
			else:
				new_time = new_time.split(".")[0]

			time_checker_count = redis.get(time_checker_redis)
			if not time_checker_count:
				redis.set(time_checker_redis, 0)
				time_checker_count = 0


			time_checker_count = int(time_checker_count)
			# print("OVDE GLEDAMO VREME ZA PROMENU MINUTA", ev_hash, "********** ", time_checker_count, " -------------- ",new_time, ev_time)

			if ev_time != new_time:
				time_checker_count = 0
			elif ev_time in ["45", "90"] and ev_time == new_time and time_checker_count > 270:
				check = False
			elif ev_time == new_time and time_checker_count == 50:
				nav = main.findAll(".filter-match ul").at(0)
				last_btn = nav.findAll("li").at(len(nav.findAll("li")) - 1).findAll("a").at(0)
				simulate_click(last_btn)
				time_checker_count += 1
			elif ev_time == new_time and time_checker_count > 64:
				check = False
			else:
				time_checker_count += 1

			redis.set(time_checker_redis, time_checker_count)
		except Exception as e:
			check = False
			log.critical("\n\nPuklo minut se nije promenio vise od 65 sekundi {}\n{}\n".format(ev_time, e))
			print("\n\nPuklo minut se nije promenio vise od 65 sekundi {}\n{}\n".format(ev_time, e))

	elif ev_time is not None and ev_time == "HT":
		try:
			time_checker_count = redis.get(time_checker_redis)
			if not time_checker_count:
				redis.set(time_checker_redis, 0)
				time_checker_count = 0

			# print("OVDE GLEDAMO VREME ZA PROMENU MINUTA POLUVREME", ev_hash, "********** ", time_checker_count, " -------------- ", ev_time)
			time_checker_count = int(time_checker_count)
			if time_checker_count > 320:
				check = False
			else:
				time_checker_count += 1

			redis.set(time_checker_redis, time_checker_count)
		except Exception as e:
			check = False
			log.critical("\n\nPuklo minut se nije promenio vise od 300 sekundi {}\n{}\n".format(ev_time, e))
			print("\n\nPuklo minut se nije promenio vise od 300 sekundi {}\n{}\n".format(ev_time, e))

	return check

def football_time_jump(event, ev_time, log, ev_hash, redis):
	# ako vreme skoci za vise od 2 minuta, vracamo False, slikamo i resetujemo prozor
	check = True

	new_time = None
	ht_flag = False

	if ev_time is not None and ev_time not in ["HT", "FT"]:
		try:
			ev_time = ev_time.replace("'", "")
			if "+" in ev_time:
				ev_time = ev_time.split("+")[0]

			ev_time =int(ev_time)
			new_time = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip()

			if new_time.lower() not in ["half", "end"]:
				new_time = int(new_time.split(".")[0])
			else:
				return True

			if ev_time < 90 and ht_flag is not True:
				if (new_time - ev_time) >= 2 or (new_time - ev_time) <= -1:
					check = False
					log.critical("\n\n1Doslo je do anomalije u vremenu vreme je skocilo sa {} na {}  -- {} \n Pravimo screenshot i restartujemo prozor\n\n".format(ev_time, new_time, ev_hash))
					print("\n\n1Doslo je do anomalije u vremenu vreme je skocilo sa {} na {}. -- {}\n Pravimo screenshot i restartujemo prozor\n\n".format(ev_time, new_time, ev_hash))
		except Exception as e:
			check = False
			log.critical(
				"\n\n2Doslo je do anomalije u vremenu {}, novo vreme {}. \n Pravimo screenshot i restartujemo prozor\n  {}\n{}  \n".format(
					ev_time, new_time, ev_hash, e))
			print(
				"\n\n2Doslo je do anomalije u vremenu {}, novo vreme {}. \n Pravimo screenshot i restartujemo prozor\n  {}\{}  \n".format(
					ev_time, new_time, ev_hash, e))

	elif ev_time == "HT":
		new_time = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip()
		if new_time.lower() not in ["half", "end"]:

			new_time = int(new_time.split(".")[0])
			if new_time > 48:
				check = False
				log.critical(
					"\n\n3Doslo je do anomalije u vremenu vreme je skocilo sa {} na {}. -- {} \n Pravimo screenshot i restartujemo prozor\n\n".format(
						ev_time, new_time, ev_hash))
				print(
					"\n\n3Doslo je do anomalije u vremenu vreme je skocilo sa {} na {}. -- {} \n Pravimo screenshot i restartujemo prozor\n\n".format(
						ev_time, new_time, ev_hash))

	return check

def football_annulled_score(event, ev_score, log, ev_hash, team1, team2):
	# ako se rezultat vrati, saljemo False, slikamo i resetujemo prozor i blokiramo kvote
	check = True

	if ev_score is not None:

		ev_score_split = ev_score.split(":")
		ev_score1 = int(ev_score_split[0])
		ev_score2 = int(ev_score_split[1])

		new_score = event.findAll('.col3').at(0).toPlainText().strip().split(":")

		new_ev_score1 = int(new_score[0])
		new_ev_score2 = int(new_score[1])

		if new_ev_score1 < ev_score1 or new_ev_score2 < ev_score2:
			check = False
			log.critical("\n\nDoslo je do anomalije u rezulatu (fudbal) {} {}:{}\n Rezultat se smanjio sa {}:{} na {}:{} Pravimo screenshot i restartujemo prozor\n\n".format(ev_hash, team1, team2, ev_score1, ev_score2, new_ev_score1, new_ev_score2))
			print("\n\nDoslo je do anomalije u rezulatu (fudbal) {} {}:{}\n Rezultat se smanjio sa {}:{} na {}:{} Pravimo screenshot i restartujemo prozor\n\n".format(ev_hash, team1, team2, ev_score1, ev_score2, new_ev_score1, new_ev_score2))

	return check



def tennis_300_sec_reset(event, redis, ev_time, log, ev_hash):
	check = True

	time_checker_redis = "time_checker_{}".format(ev_hash)

	time_checker_count = redis.get(time_checker_redis)
	if not time_checker_count:
		time_checker_count = 0
		redis.set(time_checker_redis, time_checker_count)

	# print(time_checker_count)
	time_checker_count = int(time_checker_count)
	time_checker_count += 1

	if time_checker_count > 300:
		check = False

	redis.set(time_checker_redis, time_checker_count)

	return check


def tennis_time_jump(main, ev_time, log, ev_hash):
	# ako vreme skoci sa 1st na 3rd ili 2nd na 4th ili mozda se vrati nazad, vracamo False, slikamo i resetujemo prozor
	return True

	check = True
	new_time = None
	if ev_time is not None and ev_time not in ["FT"]:
		try:
			sidebar = main.findAll('.ml13-ScoreBoard').at(0)
			score1 = sidebar.findAll('.yellow').at(0).findAll('.ml13-ScoreBoardColumn_Data').at(
				0).toPlainText().strip()
			score2 = sidebar.findAll('.yellow').at(0).findAll('.ml13-ScoreBoardColumn_Data').at(
				1).toPlainText().strip()
			score = int(score1) + int(score2) + 1
			new_time = int(score)

			if ev_time == "1st":
				if new_time not in [1, 2]:
					check = False
			elif ev_time == "2nd":
				if new_time not in [2, 3]:
					check = False
			elif ev_time == "3rd":
				if new_time not in [3, 4]:
					check = False
			elif ev_time == "4th":
				if new_time not in [4, 5]:
					check = False
			elif ev_time == "5th":
				if new_time not in [5, 6]:
					check = False
			elif ev_time == "6th":
				if new_time not in [6]:
					check = False
		except:
			check = False

		if check is False:
			log.critical("\n\nDoslo je do anomalije u vremenu vreme je skocilo sa {} na {} -- {} \n Pravimo screenshot i restartujemo prozor\n".format(ev_time, new_time, ev_hash))
			print("\n\nDoslo je do anomalije u vremenu vreme je skocilo sa {} na {} -- {} \n Pravimo screenshot i restartujemo prozor\n".format(ev_time, new_time, ev_hash))
			return False
		else:
			return True

	return True

def tennis_score_set_jump(main, set_score, log, ev_hash):
	# ako vreme skoci sa 1st na 3rd ili 2nd na 4th ili mozda se vrati nazad, vracamo False, slikamo i resetujemo prozor
	return True
	check = True
	old_home = old_away = None
	new_home = new_away = None

	if set_score is not None:
		try:
			set_score = set_score.split(":")
			old_home = int(set_score[0])
			old_away = int(set_score[1])

			sidebar = main.findAll('.ip-MatchLiveContainer').at(0)
			sidebar_nmb = sidebar.findAll(".ml13-ScoreBoardColumn")
			last_score = len(
				sidebar_nmb) - 2  # izbacujemo poene da dohvatimo trenutni set, oduzimamo 2, a ne 1 zato sto len broji od 1, a nama se posle broji od 0
			sidebar = sidebar.findAll(".ml13-ScoreBoardColumn").at(last_score)
			new_home = int(sidebar.findAll('.ml13-ScoreBoardColumn_Data1').at(0).toPlainText().strip())
			new_away = int(sidebar.findAll(".ml13-ScoreBoardColumn_Data2").at(0).toPlainText().strip())

			if new_home == 0 and old_home != 0 or new_away == 0 and old_away != 0:
				check = True
			elif new_home - old_home > 1 or new_away - old_away > 1:
				check = False
			elif old_home - new_home > 1 or old_away - new_away > 1:
				check = False

		except:
			check = False

		if check is False:
			log.critical("\n\nDoslo je do anomalije u scoru seta. Otisao score sa {}:{} na {}:{} -- {} \n Pravimo screenshot i restartujemo prozor\n".format(old_home, old_away, new_home, new_away, ev_hash))
			print("\n\nDoslo je do anomalije u scoru seta. Otisao score sa {}:{} na {}:{} -- {} \n Pravimo screenshot i restartujemo prozor\n".format(old_home, old_away, new_home, new_away, ev_hash))
			return False
		else:
			return True

	return True


def check_tennis_detailed_score(main, live_result_details, log, ev_hash):

	return True
	if live_result_details is None:
		return True

	try:
		sidebar = main.findAll('.ip-MatchLiveContainer').at(0)
		sidebar_nmb = sidebar.findAll(".ml13-ScoreBoardColumn")
		last_score = len(sidebar_nmb) - 2  # izbacujemo poene da dohvatimo trenutni set, oduzimamo 2, a ne 1 zato sto len broji od 1, a nama se posle broji od 0

		new_live_result_details = []
		new_score_sum = 0
		score_sum = 0

		for set in range(1, last_score + 1):
			sidebar_scores = sidebar.findAll(".ml13-ScoreBoardColumn").at(set)

			home = int(sidebar_scores.findAll('.ml13-ScoreBoardColumn_Data1').at(0).toPlainText().strip())
			away = int(sidebar_scores.findAll(".ml13-ScoreBoardColumn_Data2").at(0).toPlainText().strip())
			score = "{}:{}".format(home, away)

			new_score_sum += home
			new_score_sum += away

			new_live_result_details.append(score)

	except Exception as e:
		print("\nZbir gemova nije isti, puklo {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
		log.critical("\nZbir gemova nije isti, puklo {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
		return False

	rem = "0,'[]]\": "
	for char in rem:
		live_result_details = live_result_details.replace(char, "")

	for x in live_result_details:
		score_sum += int(x)

	if (new_score_sum - score_sum) > 1:
		log.critical("\n\nDoslo je do anomalije u scoru {}, {}".format(new_score_sum, score_sum))
		print("\n\nDoslo je do anomalije u scoru {}, {}".format(new_score_sum, score_sum))
		return False

	return True

def tennis_remove_predict(rdb, event, predicted_redis_key, log):


	score = event.findAll(".col3").at(0).findAll("span").at(0).toPlainText().strip()
	set = event.findAll(".col15").at(0).findAll("span").at(0).toPlainText().strip()

	score_split = score.split(":")
	set_split = set.split(":")

	score_split[0] = int(score_split[0])
	score_split[1] = int(score_split[1])
	set_split[0] = int(set_split[0])
	set_split[1] = int(set_split[1])

	if score_split[0] >= 1 and score_split[1] >= 1:
		if set_split[0] < 5 and set_split[1] < 5:
			rdb.delete(predicted_redis_key)
		elif set_split[0] >= 5 and set_split[0] - set_split[1] <= 1:
			rdb.delete(predicted_redis_key)
		elif set_split[1] >= 5 and set_split[1] - set_split[0] <= 1:
			rdb.delete(predicted_redis_key)

	if score_split[0] >= 1 and score_split[1] == 0:
		if set_split[0] >= 5 and set_split[0] - set_split[1] < 1:
			rdb.delete(predicted_redis_key)
		elif set_split[0] < 5 and set_split[1] < 5:
			rdb.delete(predicted_redis_key)

	if score_split[1] >= 1 and score_split[0] == 0:
		if set_split[1] >= 5 and set_split[1] - set_split[0] < 1:
			rdb.delete(predicted_redis_key)
		elif set_split[0] < 5 and set_split[1] < 5:
			rdb.delete(predicted_redis_key)

