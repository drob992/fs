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
