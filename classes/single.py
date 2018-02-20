# -*- coding: utf-8 -*-

import json
import os
import shlex
import subprocess
import sys
import redis
sys.path.insert(0, '../')
import time
import datetime
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebView, QWebPage
from PyQt5.QtWidgets import QApplication

from config import *
import common

import util
import classes.sports
from lookup.sports import *


class LiveEvent(QWebPage):

	_frame = None
	_onlineEvents = None
	_timer = None
	_refresh = QTimer()
	_refresh.setSingleShot(True)
	_interval = 60000  # 1min
	_bet = 0
	_page_hash = None
	_deadline = None
	_cursor_position = None
	# define signal
	newChanges = pyqtSignal(dict)

	def __init__(self, parent=None, hash=None, sport=None):
		super(LiveEvent, self).__init__(parent)

		self._parent = parent
		self.debug = None

		#todo: single debug
		self.debug = None

		self._url = QUrl(common.live_link)
		self._req = QNetworkRequest(self._url)

		self._req.setRawHeader(b"Accept-Language", b"en-US,en;q=0.8")
		self._req.setRawHeader(b"Cache-Control", b"no-cache")
		self._req.setRawHeader(b"Connection", b"keep-alive")
		self._req.setRawHeader(b"Host", b"www.tipbet.com")
		self._req.setRawHeader(b"User-Agent", common.uAgent)
		self._req.setRawHeader(b"Origin", b"https://www.tipbet.com")
		self._req.setRawHeader(b"Referer", b"https://www.tipbet.com")
		self._req.setRawHeader(b"Upgrade-Insecure-Requests", b"1")
		self._req.setRawHeader(b"Pragma", b"no-cache")
		self._req.setRawHeader(b"X-Requested-With", b"XMLHttpRequest")
		self._req.setRawHeader(b"Cookie", util.generate_cookie())

		self._frame = self.currentFrame()
		self._frame.load(self._req)

		self.settings().setAttribute(QWebSettings.AutoLoadImages, False)
		self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
		self.settings().setAttribute(QWebSettings.DnsPrefetchEnabled, True)
		self.settings().setAttribute(QWebSettings.JavaEnabled, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanAccessClipboard, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanCloseWindows, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanOpenWindows, True)
		self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, True)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)
		self.settings().setAttribute(QWebSettings.LocalStorageDatabaseEnabled, True)
		self.settings().setAttribute(QWebSettings.LocalStorageEnabled, True)
		self.settings().setAttribute(QWebSettings.OfflineStorageDatabaseEnabled, True)
		self.settings().setAttribute(QWebSettings.OfflineWebApplicationCacheEnabled, True)
		self.settings().setAttribute(QWebSettings.PluginsEnabled, True)
		self.settings().setAttribute(QWebSettings.XSSAuditingEnabled, True)
		self.settings().setAttribute(QWebSettings.ZoomTextOnly, True)

		self.settings().setMaximumPagesInCache(0)
		self.settings().setObjectCacheCapacities(0, 0, 0)
		self.settings().setOfflineStorageDefaultQuota(0)
		self.settings().setOfflineWebApplicationCacheQuota(0)

		self._timer = QTimer()
		self.parseevent = QTimer()
		self.open_sport = QTimer()
		self._deadline = time.time()
		self._refresh.setInterval(self._interval)
		self._parent.setMouseTracking(True)
		self._cursor_position = QCursor.pos()

		self._event_sport = normalized_sport[sport]
		self._event_hash = hash
		self._check_hash_counter = 0
		self._action = None
		self._initial_load = True
		self.first_time_parse = True
		self._predicted_ft_data = {}
		self._ft_emmited = None

		master_host = redis_master_host
		if util.check_local_dev():
			master_host = 'localhost'

		self.redis = redis.StrictRedis(host=master_host, port=redis_master_port, decode_responses=True, password=redis_pass)
		self.ae_r_key = "{}@{}".format(common.redis_channels['available_events'], str(sports[self._event_sport]))
		self.fe_r_key = "{}@{}".format(common.redis_channels['finished_events'], str(sports[self._event_sport]))
		self.se_r_key = "{}@{}".format(common.redis_channels['selected_events'], str(sports[self._event_sport]))
		if not util.check_local_dev():
			for node in nodes:
				if node['id'] == hostname:
					util.set_curr_node_channels(rdb=self.redis, node=node, ev_hash=hash)
					break
		else:
			util.set_curr_node_channels(rdb=self.redis, node=nodes[0], ev_hash=hash)

		node_selected_evs_slug = util.get_curr_node_channels(rdb=self.redis, ev_hash=hash, key='selected_events')
		self.single_se_r_key = "{}@{}".format(node_selected_evs_slug, str(sports[self._event_sport]))

		self.EVENT = None
		self.parse = 0
		self.statistics_cd = 2
		self.quota_hash_set = None
		self.old_quota_hash_set = None
		self.quota_hash_set_flag = 0
		self.removed_match = 0

		self._temp_removed_match = {
			'number_of_tries': 0,
		}

		self._statistics_availability = 0
		self._statistics_availability_hash = 0
		self._predicted_ft = None
		self._predicted_ft_counter = 0
		# connect signals and slots
		self.loadFinished.connect(self.read_page)

		self.volleyboll_predict = False

		self.log = util.parserLog('/var/log/sbp/flashscores/single_{}.log'.format(hash), 'bet356live-single')
		self.delay_kickoff_log = False

		if self.debug:
			self.log.info("Bet365 referent quota parser started")
			self.log.info("With headers:")
			for hd in self._req.rawHeaderList():
				self.log.info("{} : {}".format(hd, self._req.rawHeader(hd)))

	@pyqtSlot()
	def read_page(self):
		"""
		:description:   povezan je na signal otvaranja stranice, kada se stranica otvori izvrsava se metod,
						kao u js-u window.load
		:return:
		"""

		self.redis.set("time_checker_{}".format(self._event_hash), 0)

		self.log.critical("Inicijalni load.")
		self._action = 'open_sport'
		self._timer.start(common.liveReloadInterval)
		self._timer.timeout.connect(self.process_page)

		self.log.info('Web page successfully loaded, processing attached.')
		self.log.info("current: {}".format(self._url.toString()))

		self._initial_load = False
		if not util.redis_exists(self.redis, self.se_r_key, self._event_hash) and not util.redis_exists(self.redis, self.fe_r_key, self._event_hash):
			self.redis.incr(util.get_curr_node_channels(rdb=self.redis, ev_hash=self._event_hash, key='event_count'))

		util.redis_add_to_collection(self.redis, self.se_r_key, self._event_hash)
		util.redis_add_to_collection(self.redis, self.single_se_r_key, self._event_hash)


	def reload_single_page(self):

		self.log.critical("\nRadi se reload strane iz reload_single_page funkcije\n".format(ev_hash))
		screenshot_file_path = self.take_screenshot()
		diff_logger = util.parserLog('/var/log/sbp/flashscores/diff_logger.log', 'bet356live-data-differ')
		diff_logger.info('Single reloaded, file location: {}'.format(screenshot_file_path))
		if hasattr(self, 'EVENT'):
			if hasattr(self.EVENT, 'cache'):
				if hasattr(self.EVENT.cache, 'odds'):
					old_odds = self.EVENT.cache['odds']
					reseted_odds = {}
					for key in list(old_odds.keys()):
						reseted_odds[key] = 0
					setattr(self.EVENT, 'odds', reseted_odds)
					data = util.redis_emmit(self.redis, self._event_hash, self.EVENT)
					self.log.info('Single emmit: {}'.format(data))

		print("\n--*-- Restartovan [{} - {}] - {}".format(self._event_hash, self._event_sport, datetime.datetime.now().time()))
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if self._event_hash in proces_name and 'tail' not in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "xvfb-run -a python3 {}".format(proces_name[10:-2])  #

					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue

	@pyqtSlot()
	def process_page(self):

		# print("PROCESS PAGE")
		# print(self._action)
		"""
		:desc:      ruter aplikacije koji definise sta program treba da radi na osnovu toga koja je akcija
		:return:
		"""

		if self._action == 'open_sport':
			try:
				self.open_sport_group()
			except Exception as e:
				f = '*' * 50
				self.log.critical('ERROR [2]: \n{}\n{}'.format(e, f))

		elif self._action == 'open_event':
			try:
				self.open_event()
			except Exception as e:
				f = '*' * 50
				self.log.critical('ERROR [3]: \n{}\n{}'.format(e, f))

		elif self._action == 'parse_event':
			self.parse_event()

		else:
			pass
			self.log.critical('ERROR [5]: \n Undefined action.')

	def open_sport_group(self):
		self._action = None
		print("OPEN SPORT")
		"""
		# :description:   metod za kretanje kroz navigaciju i otvaranje liste dogadjaja za naredni neparsovani sport
		# :return:
		# """
		main = self._frame.findFirstElement("body")

		nav_sports_div = self._frame.findFirstElement("#live-match-filter")
		nav_sports = nav_sports_div.findAll("ul li")

		# main.findAll(".navbar").at(0).removeAllChildren()
		main.findAll(".header").at(0).removeAllChildren()
		main.findAll(".sub-menu").at(0).removeAllChildren()
		main.findAll(".message.marquee-wrapper").at(0).removeAllChildren()
		main.findAll(".live-text-header").at(0).removeAllChildren()
		main.findAll("#sidebar").at(0).removeAllChildren()
		main.findAll(".footer").at(0).removeAllChildren()

		nav_sport_collection = []
		if len(nav_sports) > 0:

			for x in range(len(nav_sports)):
				nav_sport = nav_sports.at(x).attribute('title')
				if nav_sport in normalized_sport.keys():
					nav_sport = normalized_sport[nav_sport]
				nav_sport_collection.append(nav_sport)
				if nav_sport == self._event_sport:
					if nav_sports.at(x).hasClass('active'):
						self.tipbet_sport_id = nav_sports.at(x).findAll('a').at(0).attribute('data-sport')
						self._action = 'open_event'
						# self.open_event()

				# print(self.tipbet_sport_id)
#
			if self._event_sport in nav_sport_collection:
				for x in range(len(nav_sports)):
					sport = nav_sports.at(x).attribute('title')
					if self._event_sport == normalized_sport[sport]:
						btn = nav_sports.at(x).findAll('a').at(0)
						self.tipbet_sport_id = btn.attribute('data-sport')
						util.simulate_click(btn)
						self._action = 'open_event'

			self.open_sport.stop()
			self.open_sport.start(15000)
			self._timer.timeout.connect(self.open_sport_group)

			del nav_sport_collection
		else:
			print("Ne postoji ni jedan sport u meniju!!!!!!!!!")

	def open_event(self):

		print("OPEN EVENT")
		main = self._frame.findFirstElement("body")
		events = main.findAll('tbody')

		for x in range(len(events)):
			if events.at(x).attribute('data-alive-sport-match') == self.tipbet_sport_id:
				# Pretrazivanje po kolonama uporedjivanjem hasha
				event = events.at(x)

				event.findAll('.col2 .line2').at(0).removeAllChildren()
				event.findAll('.col4 .line2').at(0).removeAllChildren()

				team_1 = event.findAll('.col2').at(0).toPlainText().strip()
				team_2 = event.findAll('.col4').at(0).toPlainText().strip()
				ev_hash = util.generate_event_hash(self._event_sport, team_1, team_2)
				if self._event_hash == str(ev_hash):
					# inicijalizujemo event
					if self._event_sport == 'Football':
						self.EVENT = classes.sports.Football(team1=team_1, team2=team_2, log=self.log)

					elif self._event_sport == 'Tennis':
						self.EVENT = classes.sports.Tennis(team1=team_1, team2=team_2, log=self.log)
						self.competition_name = event.parent().parent().findAll('.ipo-Competition_Name').at(0).toPlainText().strip()
						# print("competition_name: {}".format(competition_name))

					self.EVENT.setSport(self._event_sport)
					self.EVENT.setSource("TipBet")
					self.EVENT.setLeague("********")
					self.EVENT.setLeagueGroup("********")
					self.EVENT.setStartTime('None')

					self.event_id = events.at(x).attribute("id")

					self._action = 'parse_event'

		self.removed_match += 1
		# print(self.removed_match)
		if self.removed_match == 10:

			util.hide_quotas_on_liveboard(event_hash=self._event_hash)
			self.removed_match = 0
			# kolektor ce svaka 2 minuta da otvori prozor i da pokusa opet da nadje event u slucaju da ne uspe na brojac u redisu se dodaje +1.
			# Tako cemo pokusavati da otvorimo single 20 puta, posle cega se brise brojac i dict, i vise se nece pokusavati otvaranje

			self.log.critical("\nposle 2 minuta pokusao da otvori event, nije uspeo pocinje")
			removed_list = list(self.redis.keys("single_removed_flag_{}@*".format(self._event_sport)))

			removed_key = "single_removed_flag_{}@{}".format(self._event_sport, self._event_hash)
			if removed_key not in removed_list:
				# try:
				self.three_time_open_event("set_flag")
				self.log.critical("three_time_open_event('set_flag')")
				self.reload_single_page()
			else:
				self.log.critical("\nposle 2 minuta pokusao da otvori event, nije uspeo, dodajemo 1 na removed_flag")
				removed_key = "single_removed_flag_{}@{}".format(self._event_sport, self._event_hash)
				num_of_attempts = int(self.redis.get(removed_key))
				num_of_attempts += 1
				self.redis.set(removed_key, num_of_attempts)
				self.redis.set("single_removed_{}@{}".format(self._event_sport, self._event_hash), "{}@{}".format(int(time.time()), self._event_sport))
				#brisemo iz aktivnih i pravimo novi single_removed
				self.log.critical('\n\n!!! Napravio single_removed_{}@{}, num_of_attempts = {}. Gasimo prozor !!!!\n\n'.format(self._event_sport, self._event_hash, num_of_attempts))
				sys.exit()

	def parse_event(self):

		self._timer.stop()
		if self.first_time_parse is True:
			self.parseevent.start(1000)
			self.parseevent.timeout.connect(self.parse_event)
			self.first_time_parse = False

		# print(self._event_hash)

		self.removed_match = 0

		main = self._frame.findFirstElement('body')

		all_events = main.findAll("tbody")
		for ev in range(len(all_events)):

			btn_quotas = all_events.at(ev).findAll(".col20").at(0).findAll("span").at(0)
			# print(all_events.at(ev).attribute("id"), self.event_id)
			alltheads = main.findAll("thead")
			for x in range(len(alltheads)):
				alltheads.at(x).removeAllChildren()

			if all_events.at(ev).attribute("id") != self.event_id:
				if all_events.at(ev).hasAttribute("data-alive-sport-match") or all_events.at(ev).hasAttribute("data-live-sport-match"):
					all_events.at(ev).removeAllChildren()
			else:
				event = all_events.at(ev)

				if not btn_quotas.hasClass("selected"):
					util.simulate_click(btn_quotas)

					if event.findAll("tr").at(1).attribute("data-template-var") == "specialline":
						event.findAll("tr").at(1).findAll("td").at(0).removeAllChildren()

				if self._event_sport == 'Football':
					predict_tool = util.predict_tool(self.log, self._event_sport, main, time=None)
					if predict_tool == "restart":
						self.reload_single_page()
					elif predict_tool == "screenshots":
						self.take_screenshot()

					if util.football_time_change_checker(main, event, self.redis, self.EVENT.time, self.log, self._event_hash):
						if util.football_time_jump(event, self.EVENT.time, self.log, self._event_hash, self.redis):
							if util.football_annulled_score(event, self.EVENT.current_score, self.log, self._event_hash, self.EVENT.team1, self.EVENT.team2):
								self.EVENT.setTime(event, self._event_hash, rdb=self.redis)
								self.EVENT.setScore(event)
								self.EVENT.setRedCards(event)
								self.EVENT.setOdds(main)
								self._predicted_ft_data = self.EVENT.predict_finish(event_hash=self._event_hash)
								self.set_predicted_data(self._predicted_ft_data)
							else:
								######## ISKLJUCI KVOTE
								self.take_screenshot()
								self.log.critical("rezultat otisao u nazad {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self._event_hash))
								print("rezultat otisao u nazad {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self._event_hash))
								util.hide_quotas_on_liveboard(event_hash=self._event_hash)
								self.reload_single_page()
						else:
							######## ISKLJUCI KVOTE
							self.log.critical("Vreme je preskocilo {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self._event_hash))
							self.take_screenshot()
							util.hide_quotas_on_liveboard(event_hash=self._event_hash)
							self.reload_single_page()
					else:
						self.log.critical("minut se nije promenio vise od 65 sekundi {} {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self.EVENT.time, self._event_hash))
						print("minut se nije promenio vise od 65 sekundi {} {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self.EVENT.time, self._event_hash))
						self.take_screenshot()
						self.reload_single_page()

				if self._event_sport == 'Tennis':

					if util.tennis_300_sec_reset(event, self.redis, self.EVENT.time, self.log, self._event_hash):
						if util.tennis_time_jump(main, self.EVENT.time, self.log, ev_hash):
							if not hasattr(self.EVENT, 'current_set'):
								self.EVENT.current_set = None

							if util.tennis_score_set_jump(main, self.EVENT.current_set, self.log, ev_hash):
								sets_to_win_match = self.EVENT.get_sets_to_win(self.competition_name)
								self.redis.set("num_of_sets_{}".format(self._event_hash), sets_to_win_match)

								if not hasattr(self.EVENT, 'live_result_details'):
									self.EVENT.live_result_details = None

								if util.check_tennis_detailed_score(main, self.EVENT.live_result_details, self.log, ev_hash):

									if self.EVENT.validate_score(event=event, num_of_sets=sets_to_win_match):
										self.EVENT.setPlayerOnServe(event)
										self.EVENT.setTime(event, self._event_hash)
										self.EVENT.setCurrentSet(event)
										self.EVENT.setScore(event)
										self.EVENT.setOdds(main)
										self.EVENT.setLiveDetails(event, self.redis, self._event_hash,self.EVENT.time, self.EVENT.current_set, self.EVENT.current_score)
										self._predicted_ft_data = self.EVENT.predict_finish(event=event, current_score=self.EVENT.current_score, current_set=self.EVENT.current_set, num_of_sets=sets_to_win_match, event_hash=self._event_hash, rdb=self.redis)
										self.set_predicted_data(self._predicted_ft_data, event)
								else:
									print("Zbir gemova nije isti, ne prolazi {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
									self.log.critical("Zbir gemova nije isti, ne prolazi {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
									self.take_screenshot()
									self.reload_single_page()
							else:
								print("\nCurrent score je preskocio {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
								self.log.critical("\nCurrent score je preskocio {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
								self.take_screenshot()
								self.reload_single_page()
						else:
							print("\nVreme je preskocilo {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
							self.log.critical("\nVreme je preskocilo {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(ev_hash))
							self.take_screenshot()
							self.reload_single_page()

					else:
						self.log.critical("minut se nije promenio vise od 65 sekundi {} {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self.EVENT.time, self._event_hash))
						print("minut se nije promenio vise od 65 sekundi {} {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self.EVENT.time, self._event_hash))
						self.take_screenshot()
						self.reload_single_page()

				emmited_ft_key = 'emmited_ft_{}'.format(self._event_hash)

				data = None

				if self.EVENT.time != 0 and self.EVENT.time != 'FT' and self.EVENT.time != 'removed' and \
					self.EVENT.check_score(self._event_hash, self.redis) and \
					not self.redis.get(emmited_ft_key) and \
					not self.redis.get(common.redis_channels['singles_stop']):
					data = util.redis_emmit(self.redis, self._event_hash, self.EVENT)
					# print(data)

				elif self.redis.get(common.redis_channels['singles_stop']):

					led_key = "ED_{}".format(self._event_hash)
					live_event_data = dict(self.redis.hgetall(led_key))
					e_odds_key = "EOD_{}".format(self._event_hash)
					odd_keys = self.redis.smembers(e_odds_key)
					if odd_keys:
						odd_keys = list(odd_keys)
						live_event_data["odds"] = {}
						for o_key in odd_keys:
							live_event_data["odds"][o_key] = 0

					data = util.redis_emmit(self.redis, self._event_hash, live_event_data)
					self.redis.srem("events_for_reset", ev_hash)

				if data:

					self.log.info('Single emmit: {}'.format(data))
					timestamp = int(str(time.time()).split(".")[0])
					self.redis.set("tipbet_last_emmit-{}".format(self._event_hash), timestamp)

	def take_screenshot(self, msg=None):
		try:
			if msg:
				self.log.info('\n\n!!! {} !!!\n\n'.format(msg))

			frame = self._parent.page().mainFrame()
			image = QImage(self._parent.page().viewportSize(), QImage.Format_ARGB32)
			painter = QPainter(image)
			frame.render(painter)
			painter.end()

			team1_screenshot = self.EVENT.team1.replace("/", "&")
			team2_screenshot = self.EVENT.team2.replace("/", "&")
			screenshots_match = ("/var/log/sbp/flashscores/screenshots/{}/{}/{}:{}-{}".format(datetime.date.today(), self._event_sport, team1_screenshot, team2_screenshot, self._event_hash))
			os.system('mkdir -p "{}"'.format(screenshots_match))
			output_file = "/var/log/sbp/flashscores/screenshots/{}/{}/{}:{}-{}/{}:{}_{}.png".format(datetime.date.today(), self._event_sport, team1_screenshot, team2_screenshot, self._event_hash, team1_screenshot, team2_screenshot, datetime.datetime.now().time())
			print('\nSaving: {} - {}:{} - {}'.format(self._event_hash, team1_screenshot, team2_screenshot, datetime.datetime.now().time()))
			image.save(output_file)
			return output_file
		except Exception as e:
			self.log.info('Neuspesno kreiranje printskrina. {}'.format(e))

	def set_predicted_data(self, predicted=None, event=None):
		predicted_redis_key = "predicted_ft_{}@{}".format(self._event_sport.lower(), self._event_hash)
		predicted_ft_ts_key = "predicted_ft_ts_{}".format(self._event_hash)
		if predicted:
			try:
				self.redis.set(predicted_redis_key, self._predicted_ft_data)
				self.redis.set(predicted_ft_ts_key, int(time.time()))
			except:
				self.log.critical("\n\nPuklo na set predict data\n\n")
		else:
			if self._event_sport == "Tennis":
				util.tennis_remove_predict(self.redis, event, predicted_redis_key, self.log)

	def three_time_open_event(self, flag):
		predict = self.redis.get("predicted_ft_{}@{}".format(self._event_sport.lower(), self._event_hash))
		if flag == "remove_flag":
			self.redis.hdel("three_time_open_event", self._event_hash)
		elif flag == "set_flag" and predict is None:
			nmb_tries = 0
			value = None
			values = self.redis.hget("three_time_open_event", self._event_hash)
			try:
				value = json.loads(values)
				nmb_tries = int(value["three_time_open_event"])
			except:
				pass
			if values is None:
				try:
					self.EVENT.three_time_open_event = 1
					self.redis.hset("three_time_open_event", self._event_hash, json.dumps(self.EVENT.__dict__))
					self.log.critical('\n\n!!! Setovan three time open event !!!\n\n'.format(nmb_tries))
				except:
					# Ako ne uspe da napravi redis three time open event ugasice single, to se desava kada eventa nije ni bilo kada se startovao single(nikad nije usao u event)
					self.log.critical('\n\n!!! MEC NIJE PRONADJEN PRVI PUT KAD SE POKRENUO SINGLE !!!\n\n')
					util.remove_from_liveboard(rdb=self.redis, ev_hash=self._event_hash)
					self.redis.decr(util.get_curr_node_channels(rdb=self.redis, ev_hash=self._event_hash, key='event_count'))
					self.log.critical("Smanjen brojac evenata za 1 !!!!!!!")
					util.redis_remove_from_collection(self.redis, self.se_r_key, self._event_hash)
					self.redis.delete("single_removed_flag_{}@{}".format(self._event_sport, self._event_hash))
					self.redis.delete("single_removed_{}@{}".format(self._event_sport, self._event_hash))
					self.log.info('Single removed - {}'.format(self._event_hash))
					sys.exit()
			else:
				if nmb_tries < 3:
					nmb_tries += 1
					value["three_time_open_event"] = nmb_tries
					self.redis.hset("three_time_open_event", self._event_hash, json.dumps(value))
					self.log.critical('\n\n!!! Pokusao da otvori mec {} put/puta !!!\n\n'.format(nmb_tries))
				elif nmb_tries >= 3:
					self.EVENT = classes.sports.EventBase(team1=value['team1'], team2=value['team2'], log=self.log)
					for key in list(value.keys()):
						setattr(self.EVENT, key, value[key])
					setattr(self.EVENT, "time", "removed")
					data = util.redis_emmit(self.redis, self._event_hash, self.EVENT)
					self.log.critical('\n\n!!! Pokusao da otvori mec 3 puta poslao REMOVED !!!\n\n')
					self.log.info('Single emmit: {}'.format(data))
					# Setujemo single removed
					try:
						self.redis.set("single_removed_{}@{}".format(self._event_sport, self._event_hash), "{}@{}".format(int(time.time()), self._event_sport))
						self.redis.set("single_removed_flag_{}@{}".format(self._event_sport, self._event_hash), 0)
						self.log.critical('\n\n!!! Napravio single_removed_{}@{}!!!\n\n'.format(self._event_sport, self._event_hash))
					except:
						self.log.critical("NIJE NAPRAVIO SIGNLE_REMOVED U THREE TIMES OPEN EVENT")
						print("NIJE NAPRAVIO SIGNLE_REMOVED U THREE TIMES OPEN EVENT")

					# Obrisan three_time_open_event
					self.redis.hdel("three_time_open_event", self._event_hash)

if __name__ == "__main__":

	if len(sys.argv) == 4:
		ev_sport = "{} {}".format(sys.argv[-2], sys.argv[-1])
	else:
		ev_sport = sys.argv[-1]

	ev_hash = sys.argv[1]
	app = QApplication(sys.argv)
	# QNetworkProxy.setApplicationProxy(QNetworkProxy(3, 'us-fl.proxymesh.com', 31280, "reimerp", "bet365"))
	web = QWebView()
	print(ev_hash, ev_sport)
	webpage = LiveEvent(parent=web, hash=ev_hash, sport=ev_sport)
	web.setPage(webpage)
	web.setGeometry(900, 0, 1300, 500)
	web.show()

	try:
		sys.exit(app.exec_())
	except Exception as e:
		single_log = util.parserLog('/var/log/sbp/flashscores/single_event_tmp.log', 'bet356live-single')
		single_log.critical('APP: {}'.format(e))
