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
		self.proccespage = QTimer()
		self.parseevent = QTimer()
		self._deadline = time.time()
		self._refresh.setInterval(self._interval)
		self._parent.setMouseTracking(True)
		self._cursor_position = QCursor.pos()

		self._event_sport = normalized_sport[sport]
		self._event_hash = hash
		self._check_hash_counter = 0
		self._action = None
		self._content_hash = None
		self._initial_load = True
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
		self._action = 'select_sport'
		self.proccespage.start(common.liveReloadInterval)
		self.proccespage.timeout.connect(self.process_page)

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
	def stefan(self):
		print(time.time())

	@pyqtSlot()
	def process_page(self):

		print("PROCESS PAGE")
		"""
		:desc:      ruter aplikacije koji definise sta program treba da radi na osnovu toga koja je akcija
		:return:
		"""

		if self._action == 'select_sport':
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

		elif self._action == 'collect_odds':
			self.parseevent.start(1000)
			self.parseevent.timeout.connect(self.parse_event)
			self.proccespage.stop()

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
						self.open_event()
						# self._timer.start(1000)
						# self._timer.timeout.connect(self.open_event)
						return

				# print(self.tipbet_sport_id)
#
			if self._event_sport in nav_sport_collection:
				for x in range(len(nav_sports)):
					sport = nav_sports.at(x).attribute('title')
					if self._event_sport == normalized_sport[sport]:
						btn = nav_sports.at(x).findAll('a').at(0)
						self.tipbet_sport_id = btn.attribute('data-sport')
						print(self.tipbet_sport_id)
						util.simulate_click(btn)
						self.open_sport_group()
						return

			self.open_sport.stop()
			self.open_sport.start(15000)

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

					print(team_1, team_2)
					#####     PROVERA I UPIS U ALL_EVENTS.TXT    #####
					try:
						all_events_txt = ("/var/log/sbp/flashscores/all_events_{}.txt".format(datetime.date.today()))
						if not os.path.exists(all_events_txt):
							open(all_events_txt, 'w+')
						all_events_txt = ("/var/log/sbp/flashscores/all_events_{}.txt".format(datetime.date.today()))
						all_events = open(all_events_txt, 'r')
						numblines = 1
						for line in open(all_events_txt): numblines += 1
						event_list = all_events.readlines()
						all_events.close()
						found = False
						for line in event_list:
							if str(self._event_hash) in line:
								found = True
						if not found:
							all_events = open(all_events_txt, 'a')
							all_events.write(str('{} - {} - {}:{} - {} - {} - less /var/log/sbp/flashscores/single_{}.log - python3 {}workers/single_diffs_parser.py {}\n'.format( numblines, self._event_sport, team_1, team_2, self._event_hash, datetime.datetime.now().time(), self._event_hash, project_root_path, self._event_hash)))
							all_events.close()
					except:
						print("\nSingle nije upisan u all_events\n")
					####################################################
					# inicijalizujemo event
					if self._event_sport == 'Football':
						self.EVENT = classes.sports.Football(team1=team_1, team2=team_2, log=self.log)

					elif self._event_sport == 'Basketball':
						self.EVENT = classes.sports.Basketball(team1=team_1, team2=team_2, log=self.log)

					elif self._event_sport == 'Tennis':
						self.EVENT = classes.sports.Tennis(team1=team_1, team2=team_2, log=self.log)
						self.competition_name = event.parent().parent().findAll('.ipo-Competition_Name').at(0).toPlainText().strip()
						# print("competition_name: {}".format(competition_name))

					elif self._event_sport == 'Volleyball':
						self.EVENT = classes.sports.Volleyball(team1=team_1, team2=team_2, log=self.log)

					elif self._event_sport == 'Handball':
						self.EVENT = classes.sports.Handball(team1=team_1, team2=team_2, log=self.log)

					elif self._event_sport == 'Hockey':
						self.EVENT = classes.sports.Hockey(team1=team_1, team2=team_2, log=self.log)


					self.EVENT.setSport(self._event_sport)
					self.EVENT.setSource("TipBet")
					self.EVENT.setLeague("********")
					self.EVENT.setLeagueGroup("********")
					self.EVENT.setStartTime('None')

					self.event_id = events.at(x).attribute("id")

					self._action = 'collect_odds'

					# self._timer.stop()

			# #U slucaju da eventa nema brojac se uvecava, kad dodje do 5, aktivira se funkcija three_time_open_event, koja u redisu setuje dict sa removed i brojac
			# self._temp_removed_match['number_of_tries'] += 1
			#
			# print("55555555555555555555555555555555555555555555555555555555")
			# if self._temp_removed_match['number_of_tries'] == 5:
			# 	self.take_screenshot()
			#
			# 	# kolektor ce svaka 2 minuta da otvori prozor i da pokusa opet da nadje event u slucaju da ne uspe na brojac u redisu se dodaje +1.
			# 	# Tako cemo pokusavati da otvorimo single 20 puta, posle cega se brise brojac i dict, i vise se nece pokusavati otvaranje
			#
			# 	self.log.critical("\nposle 2 minuta pokusao da otvori event, nije uspeo pocinje")
			# 	removed_list = list(self.redis.keys("single_removed_flag_{}@*".format(self._event_sport)))
			#
			# 	removed_key = "single_removed_flag_{}@{}".format(self._event_sport, self._event_hash)
			# 	if removed_key not in removed_list:
			# 		# try:
			# 		self.three_time_open_event("set_flag")
			# 		self.log.critical("three_time_open_event('set_flag')")
			# 		self.reload_single_page()
			# 	else:
			# 		self.log.critical("\nposle 2 minuta pokusao da otvori event, nije uspeo, dodajemo 1 na removed_flag")
			# 		removed_key = "single_removed_flag_{}@{}".format(self._event_sport, self._event_hash)
			# 		num_of_attempts = int(self.redis.get(removed_key))
			# 		num_of_attempts += 1
			# 		self.redis.set(removed_key, num_of_attempts)
			# 		self.redis.set("single_removed_{}@{}".format(self._event_sport, self._event_hash), "{}@{}".format(int(time.time()), self._event_sport))
			# 		#brisemo iz aktivnih i pravimo novi single_removed
			# 		self.log.critical('\n\n!!! Napravio single_removed_{}@{}, num_of_attempts = {}. Gasimo prozor !!!!\n\n'.format(self._event_sport, self._event_hash, num_of_attempts))
			# 		sys.exit()

	def parse_event(self):
		# self._timer.stop()
		print(self._event_hash)

		main = self._frame.findFirstElement('body')

		all_events = main.findAll("tbody")
		for ev in range(len(all_events)):

			btn_quotas = all_events.at(ev).findAll(".col20").at(0).findAll("span").at(0)
			# print(all_events.at(ev).attribute("id"), self.event_id)
			if all_events.at(ev).attribute("id") != self.event_id:
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

					if util.football_time_change_checker(event, self.redis, self.EVENT.time, self.log, self._event_hash):
						if util.football_time_jump(event, self.EVENT.time, self.log, self._event_hash, self.redis):
							if util.football_annulled_score(event, self.EVENT.current_score, self.log, self._event_hash, self.EVENT.team1, self.EVENT.team2):
								self.EVENT.setTime(event, self._event_hash, rdb=self.redis)
								self.EVENT.setScore(event)
								self.EVENT.setRedCards(event)
								self.EVENT.setOdds(event)
								# self._predicted_ft_data = self.EVENT.predict_finish(event_hash=self._event_hash)
								# self.set_predicted_data(self._predicted_ft_data)
							else:
								######## ISKLJUCI KVOTE
								self.take_screenshot()
								self.log.critical("rezultat otisao u nazad {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self._event_hash))
								print("rezultat otisao u nazad {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self._event_hash))
								util.hide_quotas_on_liveboard(event_hash=self._event_hash)
								self.reload_single_page()
						else:
							self.log.critical("Vreme je preskocilo {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self._event_hash))
							self.take_screenshot()
							self.reload_single_page()
					else:
						######## ISKLJUCI KVOTE
						self.log.critical("minut se nije promenio vise od 120 sekundi {} {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self.EVENT.time, self._event_hash))
						print("minut se nije promenio vise od 120 sekundi {} {}!!!!!!!!!!!!!!!!!!!!!!!!!!\n".format(self.EVENT.time, self._event_hash))
						util.hide_quotas_on_liveboard(event_hash=self._event_hash)
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

	def statistics_availability(self):

		main = self._frame.findFirstElement("#Main")
		info_message = None

		if self._event_sport == "NFL":

			nfl_time = main.findAll('.IPTableHeader').at(0).toPlainText().strip()[:2]
			nfl_q = main.findAll('#cpClock').at(0).toPlainText().strip()

			if nfl_q in ['', ' ', '&nbsp;'] or nfl_time in ['', ' ', '&nbsp;']:
				info_message = "Statistika je nevalidna, ne valja Q ili minutaza"

			return True

		try:
			f = '*' * 50

			# provera da li postoji statistika (info o event-u)
			if self._event_sport == 'Baseball':
				sidebar_score = main.findAll("#scoreboard").at(0)
				sidebar_stat = main.findAll("#statBarContainer").at(0)
				if sidebar_score.isNull() or sidebar_stat.isNull():
					info_message = "Nema statistike na strani. {}".format(self._event_hash)
			elif self._event_sport == "Cricket":
				sidebar_score = main.findAll("#teamWrapper").at(0)
				sidebar_stat = main.findAll("#scoreboards").at(0)
				if sidebar_score.isNull() or sidebar_stat.isNull():
					info_message = "Nema statistike na strani. {}".format(self._event_hash)
			else:
				html_selector = util.get_html_selector(sport=self._event_sport, element="statistic")
				sidebar_stat = main.findAll(html_selector).at(0)
				if sidebar_stat.isNull():
					info_message = "Nema statistike na strani. {}".format(self._event_hash)


			# provera da li je ucitana statistika eventa koji se prati
			hidden_element = main.findAll('#LiveMatchAlertHeader').at(0)

			m_sport = {
				"Football": ["Soccer", "ml1", "Score"],
				"Basketball": ["Basketball", "ml18", "Score"],
				"Tennis": ["Tennis", "ml13", "Point"],
				"Handball": ["Handball", "ml78", "Score"],
				"Volleyball": ["Volleyball", "ml91", "Point"],
				"Hockey": ["IceHockey", "ml17", "Score"],
				"Waterpolo": ["WaterPolo", "ml110", "Score"],
			    "RugbyUnion": ["RugbUnion", "ml8", "Score"],
			    "NFL": ["AmericanFootball", "ml12", "Score"],
			}

			if self._event_sport == "NFL":
				main.findAll(".currentServer").at(0).removeAllChildren()
				main.findAll(".currentServer").at(1).removeAllChildren()

				team1_statistic = main.findAll(".nameContainer").at(0).toPlainText().strip()
				team2_statistic = main.findAll(".nameContainer").at(1).toPlainText().strip()

			else:
				team1_statistic = main.findAll(".{}-{}Header_TruncateName".format(m_sport[self._event_sport][1], m_sport[self._event_sport][2])).at(0).toPlainText().strip()
				team2_statistic = main.findAll(".{}-{}Header_TruncateName".format(m_sport[self._event_sport][1], m_sport[self._event_sport][2])).at(1).toPlainText().strip()


			#POSEBNA PROVERA NAZIVA KOJI SU U DETALJNIJOJ SCORE STATISTICI
			if self._event_sport in ["Tennis, Basketball", "Handball", "Volleyball", "Hockey"]:
				m_sport = {
					"Basketball": ["Basketball", "ml18", "ScoreboardParticipantCell_TeamName"],
					"Tennis": ["Tennis", "ml13", "ScoreBoard_HeaderText"],
					"Handball": ["Handball", "ml78", "ScoreboardParticipantCell_TeamName"],
					"Volleyball": ["Volleyball", "ml91", "ScoreBoard_HeaderValue"],
					"Hockey": ["IceHockey", "ml17", "ScoreboardParticipantCell_TeamName"],
				}
				team1_statistic_score_name = main.findAll(".{}-{}".format(m_sport[self._event_sport][1], m_sport[self._event_sport][2])).at(0).toPlainText().strip()
				team2_statistic_score_name = main.findAll(".{}-{}".format(m_sport[self._event_sport][1], m_sport[self._event_sport][2])).at(1).toPlainText().strip()
			else:
				team1_statistic_score_name = self.EVENT.team1
				team2_statistic_score_name = self.EVENT.team2



			if team1_statistic.replace(' ', '') != self.EVENT.team1.replace(' ', '') or team1_statistic_score_name.replace(' ', '') != self.EVENT.team1.replace(' ', ''):
				info_message = "Naziv tima 1 je pogresan -- Statistika ne valja -- [{} = {}] [{} {}] {}".format(team1_statistic, self.EVENT.team1, self._event_hash, self._event_sport, datetime.datetime.now().time())
			elif team2_statistic.replace(' ', '') != self.EVENT.team2.replace(' ', '') or team2_statistic_score_name.replace(' ', '') != self.EVENT.team2.replace(' ', ''):
				info_message = "Naziv tima 2 je pogresan -- Statistika ne valja -- [{} = {}] [{} {}] {}".format(team2_statistic, self.EVENT.team2, self._event_hash, self._event_sport, datetime.datetime.now().time())
			else:
				sportskey = hidden_element.attribute("data-sportskey").split("-")[3]
				fixture_hash = self._frame.findFirstElement('body').findAll('#Hash').at(0).attribute("value").split(";")[1]
				if sportskey not in fixture_hash:
					info_message = "Statistika je nevalidna, hash se razlikuje"

		except Exception as e:
			info_message = "Neuspesna provera statistike. {}".format(self.EVENT.team1)
			self.log.critical('{}\nERROR [Statistika nije dostupna] - {}:\n {}\n{}\n{}'.format(f, self._event_hash, info_message, e, f))

		if info_message:
			f = '*' * 50
			self.statistics_cd = 0
			print("{}\n{}\n{}".format(f, info_message, f))
			self.log.critical('ERROR [Statistika nije dostupna] - {}: {}\n{}'.format(self._event_hash, info_message, f))
			return False

		return True

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

	def set_predicted_data(self, predicted=None):
		main = self._frame.findFirstElement('#Main')
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
				util.tennis_remove_predict(self.redis, main, predicted_redis_key, self.log)

if __name__ == "__main__":

	if len(sys.argv) == 4:
		ev_sport = "{} {}".format(sys.argv[-2], sys.argv[-1])
		# sys.exit("usage: python3 collector.py [SPORTNAME]")
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
