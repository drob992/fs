# -*- coding: utf-8 -*-
import datetime
import sys
import time
import os
import shlex
import subprocess
import redis
import json
import resource
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebView, QWebPage
from PyQt5.QtWidgets import QApplication


sys.path.insert(0, '../')
import classes
import util
from config import *
import common

import classes.sports
from lookup.sports import *


class LiveCollector(QWebPage):

	_cursor_position = None

	# define signal
	newChanges = pyqtSignal(dict)

	def __init__(self, parent=None, page_link=None, debug=None, logger=None, sport=None):
		super(LiveCollector, self).__init__(parent)

		self._parent = parent
		self.debug = debug
		self.log = logger
		self.finished_logger = util.parserLog('/var/log/sbp/flashscores/zavrseni_mecevi.log', 'tip_bet-single')
		# self.ot_loger = util.parserLog('/var/log/sbp/live_parser/produzetci.log', 'tip_bet-single')
		self.reset_sport = sport
		self.sport = normalized_sport[sport]

		self.EVENT = None

		# available events redis key
		self.redis = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)
		self.ae_r_key = "{}@{}".format(common.redis_channels['available_events'], str(sports[self.sport]))
		self.fe_r_key = "{}@{}".format(common.redis_channels['finished_events'], str(sports[self.sport]))
		self.se_r_key = "{}@{}".format(common.redis_channels['selected_events'], str(sports[self.sport]))

		self._url = QUrl(page_link)
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
		# self.settings().setAttribute(QWebSettings.DnsPrefetchEnabled, True)
		self.settings().setAttribute(QWebSettings.JavaEnabled, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanAccessClipboard, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanCloseWindows, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanOpenWindows, True)
		self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, True)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)
		self.settings().setAttribute(QWebSettings.LocalStorageDatabaseEnabled, False)
		self.settings().setAttribute(QWebSettings.LocalStorageEnabled, False)
		self.settings().setAttribute(QWebSettings.OfflineStorageDatabaseEnabled, False)
		self.settings().setAttribute(QWebSettings.OfflineWebApplicationCacheEnabled, False)
		self.settings().setAttribute(QWebSettings.PluginsEnabled, True)
		self.settings().setAttribute(QWebSettings.XSSAuditingEnabled, True)
		# self.settings().setAttribute(QWebSettings.ZoomTextOnly, True)

		self.tipbet_sport_id = 0

		self._timer = QTimer()
		self.parse_timer = QTimer()
		self._parent.setMouseTracking(True)
		self._cursor_position = QCursor.pos()

		self._check_hash = True
		self._check_hash_counter = 0
		self._action = None
		self._parsed_sports = []
		self.parsed_event_hashes = []

		# connect signals and slots
		self.loadFinished.connect(self.read_page)

		if self.debug:
			self.log.info("Tip bet live quota parser started, with headers: ")
			for hd in self._req.rawHeaderList():
				self.log.info("{} : {}".format(hd, self._req.rawHeader(hd)))

		self.sidebar_match_info = None
		self.click_signal_sent = None
		self.current_event_index = -1
		self._current_sport = None

		self.finisher_action = None
		self.check_redis_interval = 500
		self.finisher_timer = QTimer()

		self._collector_scan = 0
		self.force_finish_hashes = []
		self.open_sport_group_counter = 0

		self.available_event_hashes_timer = {}

	@pyqtSlot()
	def read_page(self):
		"""
		:description:
		:return:
		"""
		self.collector_timer = QTimer()
		self.sidebar_parser_timer = QTimer()

		self.open_sport = QTimer()
		self.open_sport.timeout.connect(self.open_sport_group)
		self.open_sport.start(5000)

		self.event_watcher_timer = QTimer()
		self.event_watcher_timer.timeout.connect(self.event_watcher)

		self.resourse_checker = QTimer()
		self.resourse_checker.timeout.connect(self.resourse_check)
		self.resourse_checker.start(15000)

	def resourse_check(self):

		#Skidamo kvote sa strane kolektora
		main = self._frame.findFirstElement("#Main")
		collector_quotas = main.findAll(".ipo-OverviewMarket")
		league = main.findAll(".ipo-Competition_Sub")
		for x in range(len(collector_quotas)):
			collector_quotas.at(x).removeAllChildren()
			league.at(x).removeAllChildren()

		# print('iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, self.sport)
		if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >= 350000:
			# self.log.info('RESET kolektora - iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print('iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			# self.reload_collector()
			print("Presao limit")

	def reload_collector(self):
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		print(self.reset_sport)
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if self.reset_sport in proces_name and "collector" in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "xvfb-run -a python3 {}".format(proces_name[10:-2])
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue

	def open_sport_group(self):
		"""
		:description:   metod za kretanje kroz navigaciju i otvaranje liste dogadjaja za naredni neparsovani sport
		:return:
		"""
		main = self._frame.findFirstElement("body")

		nav_sports_div = self._frame.findFirstElement("#live-match-filter")
		nav_sports = nav_sports_div.findAll("ul li")

		main.findAll(".live-text-header").at(0).removeAllChildren()
		main.findAll("#liveMessage").at(0).removeAllChildren()
		main.findAll("#header").at(0).removeAllChildren()
		main.findAll(".header-top").at(0).removeAllChildren()
		main.findAll(".top").at(0).removeAllChildren()
		main.findAll("#sidebar").at(0).removeAllChildren()
		main.findAll("#footer").at(0).removeAllChildren()

		nav_sport_collection = []

		if len(nav_sports) > 0:

			for x in range(len(nav_sports)):
				nav_sport = nav_sports.at(x).attribute('title')
				if nav_sport in normalized_sport.keys():
					nav_sport = normalized_sport[nav_sport]

				nav_sport_collection.append(nav_sport)

				if nav_sport == self.sport:
					if nav_sports.at(x).hasClass('active'):
						self.tipbet_sport_id = nav_sports.at(x).findAll('a').at(0).attribute('data-sport')
						# print(self.tipbet_sport_id)
						self.collector_timer.timeout.connect(self.collect_events_without_statistics)
						self.collect_events_without_statistics()

						return

			if self.sport in nav_sport_collection:
				for x in range(len(nav_sports)):
					sport = nav_sports.at(x).attribute('title')
					if self.sport == normalized_sport[sport]:
						btn = nav_sports.at(x).findAll('a').at(0)
						self.tipbet_sport_id = btn.attribute('data-sport')
						# print(self.tipbet_sport_id)
						util.simulate_click(btn)
						self.open_sport_group()
						return

			self.open_sport.stop()
			self.open_sport.start(15000)


			del nav_sport_collection
		else:
			print("Ne postoji ni jedan sport u meniju!!!!!!!!!")

	def collect_events_without_statistics(self):
		"""
		:description:       metod za parsovanje svih evenata u sport grupi
		:return:
		"""

		main = self._frame.findFirstElement('#main')

		# table = main.findAll("#live_conference_wrapper").at(0)
		# active_sport =table.findAll("h2").at(0).toPlainText().strip()
		# # active_sport = active_sport.attribute('data-template-var')
		#
		# try:
		# 	active_sport = normalized_sport[active_sport]
		# except:
		# 	self.collector_timer.stop()
		# 	self.open_sport.start(3000)
		#
		# if active_sport != self.sport:
		# 	print("Puklo je na events bez statistike, nema tog sporta vise. Pokusace opet za 15 sekundi")
		# 	self.open_sport.start(15000)
		# 	self.collector_timer.stop()
		# 	print("Puklo je na events bez statistike, nema tog sporta vise. Pokusace opet za 15 sekundi")
		# 	return

		self.open_sport.stop()
		self.event_watcher_timer.start(500)

		if len(self.parsed_event_hashes):
			del self.parsed_event_hashes
			self.parsed_event_hashes = []

		events = main.findAll('tbody')

		for x in range(len(events)):
			if events.at(x).attribute('data-alive-sport-match') == self.tipbet_sport_id:

				event = events.at(x)

				event.findAll('.col2 .line2').at(0).removeAllChildren()
				event.findAll('.col4 .line2').at(0).removeAllChildren()

				team_1 = event.findAll('.col2').at(0).toPlainText().strip()
				team_2 = event.findAll('.col4').at(0).toPlainText().strip()

				event_hash = util.generate_event_hash(self.sport, team_1, team_2)

				if not util.is_chinese(team_1) and not util.is_chinese(team_2) and event_hash not in self.parsed_event_hashes:
					if not util.redis_exists(self.redis, self.se_r_key, event_hash) and not util.redis_exists(self.redis, self.fe_r_key, event_hash):

						#Instanciramo EVENT i onda dalje u zavisnosti od sporta dodajemo kljuceve i vrednosti
						self.EVENT = eval("classes.sports.{}(team1=team_1, team2=team_2, log=self.log)".format(self.sport).replace("-", ""))
						self.EVENT.setSource("TipBet")
						self.EVENT.setSport(self.sport)
						self.EVENT.setLeague('********')
						self.EVENT.setLeagueGroup('********')
						self.EVENT.setStartTime('None')

						kickoff = False

						if self.sport == 'Tennis' or self.sport == 'Volleyball':

							ev_time = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip()

							if ev_time != "Half":

								if ev_time == "Set 1":
									ev_time = "1st"
								elif ev_time == "Set 2":
									ev_time = "2nd"
								elif ev_time == "Set 3":
									ev_time = "3rd"
								elif ev_time == "Set 4":
									ev_time = "4th"
								elif ev_time == "Set 5":
									ev_time = "5th"
							else:
								kickoff = True
								ev_time = "HT"

						else:
							if self.sport == 'Handball' or self.sport == 'Basketball' or self.sport == 'Hockey' or self.sport == "Football":

								ev_time = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip()

								if ":" not in ev_time:

									ev_time = ev_time.split(".")[0]

									if ev_time != "Half":

										if self.sport == "Basketball":
											if ev_time == '':
												ev_time = '1st'
											else:
												ev_time = int(ev_time)

												if 0 < ev_time <= 10:
													ev_time = '1st'
												elif 10 < ev_time <= 20:
													ev_time = '2nd'
												elif 20 < ev_time <= 30:
													ev_time = '3rd'
												elif 30 < ev_time <= 40:
													ev_time = '4th'
												elif 40 < ev_time:
													ev_time = 'OT'

										elif self.sport == "Football":
											ev_time = int(ev_time)
											if ev_time < 45:
												ev_time = "{}'".format(ev_time)
											else:
												ev_time = "{}'".format(ev_time)
												kickoff = True

										elif self.sport == "Handball":
											ev_time = int(ev_time)
											if ev_time < 30:
												ev_time = "1st"
											else:
												ev_time = "2nd"
												kickoff = True

										if self.sport == "Hockey":
											if ev_time == '':
												ev_time = '1st'
											else:
												ev_time = int(ev_time)

												if 0 < ev_time <= 20:
													ev_time = '1st'
												elif 20 < ev_time <= 40:
													ev_time = '2nd'
												elif 40 < ev_time <= 60:
													ev_time = '3rd'
												elif 40 < ev_time:
													ev_time = 'OT'
									else:
										kickoff = True
										ev_time = "HT"

								else:
									kickoff = True
									ev_time = "1'"

						scores = event.findAll('.col3').at(0).toPlainText().strip().split(":")
						home = scores[0]
						away = scores[1]

						if home == "" or home == " ":
							home = 0
						if away == "" or away == " ":
							away = 0

						current_score = '{}:{}'.format(home, away)
						if self.sport not in ["Tennis", "Volleyball"]:
							setattr(self.EVENT, 'current_score', current_score)

							if self.sport == 'Basketball':
								self.EVENT.live_result_details = str(
									['{}'.format(current_score), '0:0', '0:0', '0:0']).replace("'", '"')

								if ev_time in ["1st", "2nd"]:
									self.EVENT.ht_score = current_score
						else:
							setattr(self.EVENT, 'current_set', current_score)

						setattr(self.EVENT, 'time', ev_time)

						# Sluzi za blokiranje evenata koja nisu u odredjenom vremenskom perioodu (Periodu dozvoljenom za pustanje, uglavnom prvo/a/i (poluvreme, cetvrtina, period, set)
						# Za Fudbal pored ovog blokiranje, malo iznad (obelezeno) stoji deo koji blokira utakmice koje su u drugom poluvremenu

						minutes = event.findAll('.col1 time').at(0).toPlainText().strip().split(".")[0]
						if self.sport == 'Basketball':
							if self.EVENT.time == "1st" and (minutes in ["0", "12", " ", ""]) and self.EVENT.current_score == "0:0" or self.EVENT.time in ["HT", "2nd", "3rd", "4th"]:
								kickoff = True
						elif self.sport == 'Hockey':
							if self.EVENT.time == "1st" and (minutes in ["0", "20", " ", ""]) and self.EVENT.current_score == "0:0" or self.EVENT.time == "2nd" or self.EVENT.time == "3rd":
								kickoff = True
						elif self.sport == "Handball":
							if self.EVENT.time == "1st" and (minutes in ["0", " ", ""]) and self.EVENT.current_score == "0:0" or self.EVENT.time == "2nd":
								kickoff = True
						elif self.sport == "Volleyball":
							if self.EVENT.current_set != "0:0" or self.EVENT.time != "1st":
								kickoff = True
						elif self.sport == "Tennis":
							if self.EVENT.current_set != "0:0" or self.EVENT.time != "1st":
								kickoff = True
						elif self.sport == 'Football':
							if self.EVENT.time in [" ", "", "0:0", "0", "&nbsp;"]:
								kickoff = True

						#Sve utakmice koje nisu blookirane ili su u produzetcima, necemo emmitovati
						if kickoff is not True and self.EVENT.time != "OT":
							self.parsed_event_hashes.append(event_hash)
							util.redis_add_to_collection(self.redis, self.ae_r_key, event_hash)
							data = util.redis_emmit(self.redis, event_hash, self.EVENT, collector=True)
							# print(data)
							self.log.info('Collector emmit: {}'.format(data))
							self.redis.set('event_main_info|{}'.format(event_hash), "{} - {}".format(team_1, team_2))

	def event_watcher(self):
		"""thread worker function"""

		available_event_hashes = []
		main_content = self._frame.findFirstElement('#Main')
		events = main_content.findAll('.ipo-Fixture')
		for z in range(len(events)):
			event = events.at(z)

			if not event.parent().hasClass('ipo-Competition_EventLink'):
				teams = event.findAll('.ipo-Fixture_CompetitorName')
				team_1 = teams[0].toPlainText().strip()
				team_2 = teams[1].toPlainText().strip()
				event_hash = util.generate_event_hash(self.sport, team_1, team_2)

				if self.sport in ['Basketball', 'Hockey', 'Handball']:
					try:
						ot = event.findAll('.ipo-Fixture_MetaContainer').at(0).findAll(".ipo-Fixture_GameInfo-2").at(0).toPlainText().strip().lower()

					except:
						ot = "pass"

					if ot != "ot" and ot != "et":
						available_event_hashes.append(event_hash)
					# else:
						# print("Preskocio zato sto je OT (ET) ***** {} - {} : {}".format(event_hash, team_1, team_2))
						# self.ot_loger.critical("{} - {} : {}".format(event_hash, team_1, team_2))

				elif self.sport in ['Football']:
					try:
						old_available_event_hashes_timer = int(self.available_event_hashes_timer[event_hash])
					except:
						old_available_event_hashes_timer = 0
					ot = event.findAll('.ipo-Fixture_MetaContainer').at(0).findAll('.ipo-Fixture_Time').at(0).toPlainText().strip()

					available_event_hashes = util.football_ft_remove_time_jump(self.redis, ot, event_hash, self.sport, self.available_event_hashes_timer, available_event_hashes, old_available_event_hashes_timer, self.log)
				else:
					available_event_hashes.append(event_hash)


		predicted_ft_hashes = self.redis.keys("predicted_ft_{}@*".format(self.sport.lower()))
		critical_hashes = []
		if len(predicted_ft_hashes):
			for _ in list(predicted_ft_hashes):
				critical_hashes.append(_.split("@")[1])
				# print("[finisher] force_finish_hashes: {}".format(len(critical_hashes)))

		# print("critical_hashes: {}".format(critical_hashes))


		# oduzimaju se samo IZABRANI nestali mecevi, koji su usli u predict_ft fazu, setovanje critical_FT-a
		self.force_finish_hashes = list(set(critical_hashes) - set(available_event_hashes))
		finished_events = util.redis_get_collection(self.redis, self.fe_r_key)
		if len(self.force_finish_hashes):
			for _ in self.force_finish_hashes:

				emmited_ft_key = 'emmited_ft_{}'.format(_)
				predicted_ft_key = "predicted_ft_{}@{}".format(self.sport.lower(), _)
				predicted_ft_ts_key = "predicted_ft_ts_{}".format(_)

				if self.redis.get(predicted_ft_ts_key):
					try:
						razlika = int(time.time()) - int(self.redis.get(predicted_ft_ts_key))
					except:
						print("Nije mogao da izracuna razliku na kolektoru", time.time(), self.redis.get(predicted_ft_ts_key), _)
						print("\n\n")
						razlika = 600

					if razlika < 600:
						if finished_events:
							if _ in finished_events:
								print("vec je poslat FT za {}".format(_))
								self.redis.delete(predicted_ft_key)
								self.redis.delete(predicted_ft_ts_key)
								return False

						data = self.redis.get("predicted_ft_{}@{}".format(self.sport.lower(), _))
						if data and not self.redis.get(emmited_ft_key) and "'time': 'FT'" in data:
							util.node_kill_event(self.redis, sports[self.sport], _)


							node_selected_evs_slug = util.get_curr_node_channels(rdb=self.redis, ev_hash=_, key='selected_events')
							node_event_count_slug = util.get_curr_node_channels(rdb=self.redis, ev_hash=_, key='event_count')

							# update redis kolekcija [izabrani, dostupni, zavrseni]
							util.redis_add_to_collection(self.redis, self.fe_r_key, _)
							util.redis_remove_from_collection(self.redis, self.se_r_key, _)
							single_se_r_key = "{}@{}".format(node_selected_evs_slug, str(sports[self.sport]))
							util.redis_remove_from_collection(self.redis, single_se_r_key, _)
							self.redis.decr(node_event_count_slug)

							self.redis.delete("single_removed_{}@{}".format(self.sport, _))
							self.redis.delete("single_removed_flag_{}@{}".format(self.sport, _))
							# print(data)
							self.finished_logger.info('Zadnji predict pred brisanje (stoji ovde radi provere): {}'.format(data))
							self.redis.delete(predicted_ft_key)
							self.redis.delete(predicted_ft_ts_key)
							self.redis.set(emmited_ft_key, True)

							score_key = "score_details_{}".format(_)
							self.redis.delete(score_key)
							last_emmit_k = "tipbet_last_emmit-{}".format(_)
							self.redis.delete(last_emmit_k)
							print("obrisao {}".format(predicted_ft_key))

							for h_ in list(endpoint_rdb_ch_sets.keys()):
								self.redis.lpush(endpoint_rdb_ch_sets[h_]['publish_ch'], json.dumps({_: eval(data)}))

							data = json.dumps({_: eval(data)})
							self.finished_logger.info('Single emmit FT (30 sec. wait): {}'.format(data))
							print("Emitovan FT [{} {}] {}".format(_, self.sport, datetime.datetime.now()))

							set_remove_flag_key = "remove_single_{}@{}".format(self.sport, _)
							send_removed_data = "{}@{}@{}".format(_, int(time.time()), data)
							self.redis.set(set_remove_flag_key, send_removed_data)
						else:
							self.redis.delete(predicted_ft_key)
							self.redis.delete(predicted_ft_ts_key)
					else:
						self.redis.delete(predicted_ft_key)
						self.redis.delete(predicted_ft_ts_key)
						msg = "Proslo je previse vremena od kad je setovan predict, nemoj da saljes FT, obrisi {}".format(_)
						self.finished_logger.info('Single emmit FT (30 sec. wait): {}'.format(msg))
						return False


		remove_singles = self.redis.keys("remove_single_{}@*".format(self.sport))
		if len(remove_singles):
			for single in remove_singles:
				try:
					rs = self.redis.get(single)
					rs = rs.split("@")
					rs_hash, rs_time = rs[0], rs[1]
					if int(time.time()) - int(rs_time) >= 30:
						util.remove_from_liveboard(rdb=self.redis, ev_hash=rs_hash)
						self.redis.delete("remove_single_{}@{}".format(self.sport, rs_hash))
						print("obrisao remove_single_{} {}".format(rs_hash, datetime.datetime.now()))
						self.finished_logger.info('Single removed - {}'.format(rs_hash))

						util.node_kill_event(self.redis, sports[self.sport], rs_hash)
						self.redis.delete("single_removed_flag_{}@{}".format(self.sport, rs_hash))
						self.redis.delete("single_removed_{}@{}".format(self.sport, rs_hash))
						#util.parserLog('/var/log/sbp/live_parser/single_{}.log'.format(rs_hash), 'tip_bet-single').info(data)
				except Exception as e:
					self.log.critical(e)

		# dobijanje liste svih nestalih meceva za apdejt dostupnih
		if util.redis_exists(self.redis, self.ae_r_key):
			rdb_available_events = util.redis_get_collection(self.redis, self.ae_r_key)
			remove_from_available = list(set(rdb_available_events) - set(available_event_hashes))
			for el in remove_from_available:
				# print("sklonio sam {} iz liste dostupnih".format(el))
				self.finished_logger.info('Event {} removed from {}'.format(el, self.ae_r_key))
				util.redis_remove_from_collection(self.redis, self.ae_r_key, el)

		# todo: za removed evente gasimo single i palimo ga svaka dva minuta da proverimo da li se event vratio
		removed_singles_list = list(self.redis.keys("single_removed_{}@*".format(self.sport)))
		if len(removed_singles_list):
			for removed_single_key in removed_singles_list:
				removed_single_hash = removed_single_key.split("@")[1]
				removed_single_get = self.redis.get(removed_single_key)
				try:
					rm_single_time, rm_single_sport = removed_single_get.split("@")
				except Exception as e:
					self.log.critical(e)
					break

				#ako je 20 puta pokusao da upali single koji je bio removed i nije se vratio, zavrsavamo mec
				#Dodajemo ga u finished, brisemo iz selektovanih(aktivnih), brisemo iz selektovanih sa noda i radimo decr
				try:
					num_of_attemps = int(self.redis.get("single_removed_flag_{}@{}".format(self.sport, removed_single_hash)))
				except:
					print("Nije uspeo da uzme vrednost iz single_removed_flag_{}@{}\nSetujemo tu vrednost na 0\n".format(self.sport, removed_single_hash))
					self.log.critical("Nije uspeo da uzme vrednost iz single_removed_flag_{}@{}\nSetujemo tu vrednost na 0\n".format(self.sport, removed_single_hash))
					num_of_attemps = 0

				if num_of_attemps == 20:
					util.node_kill_event(self.redis, sports[self.sport], removed_single_hash)
					self.redis.delete("single_removed_flag_{}@{}".format(self.sport, removed_single_hash))
					self.redis.delete("single_removed_{}@{}".format(self.sport, removed_single_hash))
					util.redis_add_to_collection(self.redis, self.fe_r_key, removed_single_hash)
					util.redis_remove_from_collection(self.redis, self.se_r_key, removed_single_hash)

					node_selected_evs_slug = util.get_curr_node_channels(rdb=self.redis, ev_hash=removed_single_hash, key='selected_events')

					single_se_r_key = "{}@{}".format(node_selected_evs_slug, str(sports[self.sport]))
					util.redis_remove_from_collection(self.redis, single_se_r_key, removed_single_hash)
					print("Obrisao single_removed_{}@{} i single_removed_flag_{}@{}".format(self.sport, removed_single_hash, self.sport, removed_single_hash))

					self.finished_logger.info('20 puta pokusao da otvori i otisao u removed, saljemo u finished {} {}'.format(removed_single_hash, self.sport))
					node_event_count_slug = util.get_curr_node_channels(rdb=self.redis, ev_hash=removed_single_hash, key='event_count')
					self.redis.decr(node_event_count_slug)
					break

				current_time = int(time.time())
				if (current_time - int(rm_single_time)) >= 60:
					try:
						util.node_kill_event(self.redis, sports[self.sport], removed_single_hash)
						self.redis.delete("single_removed_{}@{}".format(self.sport, removed_single_hash))
						rm_single_sport = sports[rm_single_sport]
						util.node_open_event(self.redis, rm_single_sport, removed_single_hash)
						print("\nPokusavamo da otvorimo event koji je REMOVED, {}. put posle 60 sekundi od predhodnog pokusaja\n{}:{}:{}\n".format(num_of_attemps, self.sport, removed_single_hash, datetime.datetime.now().time()))
					except Exception as e:
						self.log.critical(e)

		flush_collector = list(self.redis.keys("flush_collector_data"))
		# print(flush_collector)
		if len(flush_collector):
			flush_collector = util.redis_get_collection(self.redis, 'flush_collector_data')
			if len(flush_collector):
				if self.sport in flush_collector:
					self.parsed_event_hashes = []
					util.redis_remove_from_collection(self.redis, 'flush_collector_data', str(self.sport))
					self.sidebar_parser_timer.stop()
					self.collector_timer.stop()
					self.collector_timer.start(5000)


if __name__ == "__main__":

	if len(sys.argv) != 2:
		sport = "{} {}".format(sys.argv[-2], sys.argv[-1])
		# sys.exit("usage: python3 collector.py [SPORTNAME]")
	else:
		sport = sys.argv[-1]

	collector_log = util.parserLog('/var/log/sbp/live_parser/tipbet_collector_{}.log'.format(normalized_sport[sport]), 'tipbet-live-collector')
	# todo: if gui in sys.argv True
	app = QApplication(sys.argv)
	web = QWebView()
	webpage = LiveCollector(parent=web, page_link=common.live_link, debug=True, logger=collector_log, sport=sport)
	web.setPage(webpage)
	web.setGeometry(780, 0, 1200, 768)
	web.show()

	try:
		sys.exit(app.exec_())
	except Exception as e:
		collector_log.critical('APP: {}'.format(e))
