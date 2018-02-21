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
from PyQt5.QtTest import QTest

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
		self.reset_sport = sport
		self.sport = normalized_sport[sport]

		self.EVENT = None

		# available events redis key
		self.redis = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)

		self._url = QUrl(page_link)
		self._req = QNetworkRequest(self._url)

		self._req.setRawHeader(b"Accept-Language", b"en-US,en;q=0.8")
		self._req.setRawHeader(b"Cache-Control", b"no-cache")
		self._req.setRawHeader(b"Connection", b"keep-alive")
		self._req.setRawHeader(b"User-Agent", common.uAgent)
		self._req.setRawHeader(b"Origin", b"https://www.flashscore.com/")
		self._req.setRawHeader(b"Referer", b"https://www.flashscore.com/")
		self._req.setRawHeader(b"Upgrade-Insecure-Requests", b"1")
		self._req.setRawHeader(b"Pragma", b"no-cache")
		self._req.setRawHeader(b"X-Requested-With", b"XMLHttpRequest")
		# self._req.setRawHeader(b"Cookie", util.generate_cookie())

		self._frame = self.currentFrame()
		self._frame.load(self._req)

		self.settings().setAttribute(QWebSettings.AutoLoadImages, False)
		self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, False)
		self.settings().setAttribute(QWebSettings.JavaEnabled, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanAccessClipboard, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanCloseWindows, True)
		self.settings().setAttribute(QWebSettings.JavascriptCanOpenWindows, True)
		self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, False)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)
		self.settings().setAttribute(QWebSettings.LocalStorageDatabaseEnabled, False)
		self.settings().setAttribute(QWebSettings.LocalStorageEnabled, False)
		self.settings().setAttribute(QWebSettings.OfflineStorageDatabaseEnabled, False)
		self.settings().setAttribute(QWebSettings.OfflineWebApplicationCacheEnabled, False)
		self.settings().setAttribute(QWebSettings.PluginsEnabled, True)
		self.settings().setAttribute(QWebSettings.XSSAuditingEnabled, True)
		# self.settings().setAttribute(QWebSettings.ZoomTextOnly, True)

		self.tipbet_sport_id = 0
		self.click_tenth_time = 0

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

		self.checker = True

	@pyqtSlot()
	def read_page(self):
		"""
		:description:
		:return:
		"""

		if self.checker:

			# self.statistics = QTimer()
			# self.statistics.timeout.connect(self.match_statistics)
			# self.statistics.start(10000)

			QTimer().singleShot(2000, self.match_statistics)
			self.checker = False

	def open_countries(self):

		print("1111111111111111111111")
		main = self._frame.findFirstElement("#main")
		country_list = main.findAll(".menu.country-list").at(2).findAll("li")
		country_list1 = main.findAll(".menu.country-list").at(3).findAll("li")

		for i in range(1, len(country_list)):
			if country_list.at(i).hasAttribute("id"):
				# print(country_list.at(i).attribute("id"))
				country = country_list.at(i).findAll("a").at(0)
				self.redis.sadd('countries', country.toPlainText().lower().replace(" ", "-"))
				util.simulate_click(country)
				# print(country.toPlainText().strip())
				# print("----------------------------")

		for i in range(0, len(country_list1)):
			if country_list1.at(i).hasAttribute("id"):
				# print(country_list1.at(i).attribute("id"))
				country1 = country_list1.at(i).findAll("a").at(0)
				util.simulate_click(country1)
				self.redis.sadd('countries', country1.toPlainText().lower().replace(" ", "-"))
				# print(country1.toPlainText().strip())
				# print("----------------------------")

		QTimer().singleShot(2000, self.get_league_links)

		print("11111111111!!!!!!!!!!!!!!!!!!!")


	def get_league_links(self):

		print("22222222222222222")
		main = self._frame.findFirstElement("#main")
		country_list = main.findAll(".menu.country-list").at(2).findAll("li")
		country_list1 = main.findAll(".menu.country-list").at(3).findAll("li")

		for i in range(1, len(country_list)):
			if country_list.at(i).hasAttribute("id"):
				if country_list.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
					continue
				# print(country_list.at(i).attribute("id"))
				league_list = country_list.at(i).findAll("ul").at(0).findAll("li")
				for x in range(0, len(league_list)):
					league = league_list.at(x).findAll("a").at(0)

					# if league.toPlainText().strip() in ["Championship", "Ligue 1"]:
					if league.toPlainText().strip() in ["Championship"]:
						print(league.toPlainText().strip())
						print("111111111111111111111111111111111111111111111111")
					# if league not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
						# print(league.attribute("href"))
						self.redis.sadd('leagues_links', "https://www.flashscore.com{}".format(league.attribute("href")))
						self.redis.sadd('leagues', league.toPlainText().lower().replace(" ", "-"))
						# util.simulate_click(league)
						# print(league.toPlainText().strip())
						# print("----------------------------")

		for i in range(0, len(country_list1)):
			if country_list1.at(i).hasAttribute("id"):
				if country_list.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
					continue
				# print(country_list1.at(i).attribute("id"))
				league_list = country_list1.at(i).findAll("ul").at(0).findAll("li")
				for x in range(0, len(league_list)):
					league = league_list.at(x).findAll("a").at(0)

					# if league.toPlainText().strip() in ["Championship", "Ligue 1"]:
					if league.toPlainText().strip() in ["Championship"]:
						print(league.toPlainText().strip())
						print("11111111111111111111111111111111111111111111111111")
					# if league not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
						# print(league.attribute("href"))
						self.redis.sadd('leagues_links', "https://www.flashscore.com{}".format(league.attribute("href")))
						self.redis.sadd('leagues', league.toPlainText().lower().replace(" ", "-"))
						# util.simulate_click(league)
						# print(league.toPlainText().strip())
						# print("----------------------------")

		# self.redis.sadd('leagues_links', "https://www.flashscore.com/football/world/world-cup/")
		# self.redis.sadd('leagues', "world-cup")

		print("222222222!!!!!!!!!!!!!!!!!!")
		QTimer().singleShot(3000, self.parse_leagues_links)


	def parse_leagues_links(self):

		print("3333333333333333")

		league_links = self.redis.smembers('leagues_links')

		if self.redis.get("parse_teams"):

			team_links = self.redis.smembers('team_links')

			if len(team_links) == 0:
				sys.exit()

			# OPEN TEAM LINK
			for link in team_links:
				# print(link)
				self.redis.srem("team_links", link)
				print(link+"results")
				if link != "https://www.flashscore.com":
					self._frame.load(QNetworkRequest(QUrl(link+"results")))
					self.more = True
					QTimer().singleShot(3500, self.parse_team)
					break
		else:
			if len(league_links) == 1:
				self.redis.set("parse_teams", True)

			for link in league_links:
				# print(link)
				self.redis.srem("leagues_links", link)
				if "cup" in link.lower() or "offs" in link.lower():
					continue

				print(link)
				self._frame.load(QNetworkRequest(QUrl(link)))

				QTimer().singleShot(3500, self.get_teams_links)

				break

			# break
		print("333333333333!!!!!!!!!!!!!!!!!!")

	def get_teams_links(self):
		print("44444444444444444444444444")

		groups = None
		teams = 0
		league_name = None
		country = None
		try:
			main = self._frame.findFirstElement("#main")
			groups = main.findAll(".stats-table-container").at(0).findAll("tbody")
			country = main.findAll(".tournament").at(0).findAll("a").at(1).toPlainText().strip()
			league_name = main.findAll('.tournament-name').at(0).toPlainText().strip()
		except:
			print("EXCEPT BRE 444444444")

		print(country, league_name)
		for i in range(len(groups)):
			teams = groups.at(i).findAll("tr")
			for x in range(len(teams)):
				team = teams.at(x).findAll("td").at(1).findAll("span").at(1).findAll("a").at(0)
				played = teams.at(x).findAll("td").at(2).toPlainText().strip()
				wins = teams.at(x).findAll("td").at(3).toPlainText().strip()
				draws = teams.at(x).findAll("td").at(4).toPlainText().strip()
				losses = teams.at(x).findAll("td").at(5).toPlainText().strip()
				goals = teams.at(x).findAll("td").at(6).toPlainText().strip()
				points = teams.at(x).findAll("td").at(7).toPlainText().strip()

				link_for_team = team.attribute("onclick").replace("javascript:getUrlByWinType('", "").replace("');", "")
				self.redis.sadd("team_links", "https://www.flashscore.com{}".format(link_for_team))
				print(team.toPlainText(), played, wins, draws, losses, goals, points)
				# print("11111111111111111111")

		print("44444444444!!!!!!!!!!!!!!!!!!")
		QTimer().singleShot(1500, self.parse_leagues_links)


	def parse_team(self):
		print("555555555555555555")

		tr = None
		team_name = None

		# if self.more:
		# 	print("5555555555@@@@@@@@@@@@@@@@@@@")
		# 	self.more = False
		# 	try:
		# 		load_more = self._frame.findFirstElement("#participant-page-results-more")
		# 		util.simulate_click(load_more.findAll("a").at(0))
		# 		print("5555555555###################################################")
		# 		QTimer().singleShot(3500, self.parse_team)
		# 	except:
		# 		print("EXCEPT BRE open_team11")
		# 		QTimer().singleShot(1000, self.parse_team)
		#
		# else:
		print("5555555555&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")

		main = self._frame.findFirstElement("#main")
		try:
			country = main.findAll(".tournament").at(0).findAll("a").at(1).toPlainText().strip()
		except:
			print("Pukloeeeeee")

		try:
			tr = main.findAll("#fs-results").at(0).findAll("tr")
			team_name = main.findAll('.team-name').at(0).toPlainText().strip()
		except:
			print("EXCEPT BRE open_team22")


		country_part = None
		tournament_part = None
		time = None
		team_home = None
		team_away = None
		score = None
		win_lose = None

		print("55555555555555(((((((((((((((((((((((((")
		for x in range(len(tr)):

			row = tr.at(x)

			if row.hasClass("league"):
				country_part = row.findAll(".country_part").at(0).toPlainText().strip()
				tournament_part = row.findAll(".tournament_part").at(0).toPlainText().strip()
			else:
				id = row.attribute("id").replace("g_1_", "")
				time = row.findAll(".time").at(0).toPlainText().strip()
				home = row.findAll(".team-home").at(0).toPlainText().strip()
				away = row.findAll(".team-away").at(0).toPlainText().strip()
				score = row.findAll(".score").at(0).toPlainText().strip().replace("\n", " ").replace(u'\xa0', u' ')
				win_lose = row.findAll(".win_lose_icon").at(0).attribute("title").strip()

				if team_name != None:
					if "2016" not in time and "2015" not in time and "2014" not in time and "2013" not in time and "2012" not in time and "2011" not in time and "2010" not in time and "2009" not in time:
						# event = time, " - ", home, " - ", away, " - ", score, " - ", win_lose, " - ", country_part, tournament_part, " - ", id
						event = {"id":x, "time":time, "home":home, "away":away, "score":score, "win_lose":win_lose, "country_part":country_part, "tournament_part":tournament_part, "flashscore_id":id}

						self.redis.hset(team_name, x, json.dumps(event))

						print(country_part, tournament_part)
						print(time, " - ", team_home, " - ", team_away, " - ", score, " - ", win_lose, " - ", id)

		print("555555555555555!!!!!!!!!!!!!!!!!!")

		self.redis.sadd("team_names", team_name)
		self.resourse_check()
		QTimer().singleShot(3000, self.parse_leagues_links)
		print("@!#!!@#!@$!@#!@#!@$!@$!$!#$")

	def match_statistics(self):

		# self.statistics.stop()

		team_names = self.redis.smembers("team_names")

		for team in team_names:

			matches = self.redis.hgetall(team)

			if len(matches) == 0 or team in ["", " ", None]:
				self.redis.srem("team_names", team)
				continue

			for i in matches:

				match = json.loads(matches[i])

				print("https://www.flashscore.com/match/{}/#match-summary".format(match['flashscore_id']))
				self._frame.load(QNetworkRequest(QUrl("https://www.flashscore.com/match/{}/#match-summary".format(match['flashscore_id']))))

				self.summary_click = True
				self.redis.hdel(team, i)
				QTimer().singleShot(3000, self.parse_statistics)

				break
			break


	def parse_statistics(self):
		summary = {}
		statistics = {}
		if self.summary_click:
			try:
				summary_btn = self._frame.findFirstElement("#a-match-statistics")
				util.simulate_click(summary_btn)
				self.summary_click = False
				QTimer().singleShot(2000, self.parse_statistics)
				print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
			except Exception as e:
				self.summary_click = False
				QTimer().singleShot(2000, self.parse_statistics)
				print("puklo na klik statistics", e)
		else:
			try:
				main = self._frame.findFirstElement("#summary-content")
				rows = main.findAll("tr")
				self.period = None

				time = {}
				team1 = []
				team2 = []
				summary["1st Half"] = {}
				summary["2nd Half"] = {}

				for i in range(len(rows)):
					self.team1 = None
					self.team2 = None
					self.score = None
					col = rows.at(i).findAll('td')

					if len(col) == 1:
						self.period = col.at(0).toPlainText().strip()
						team1 = []
						team2 = []

					if len(col) == 3:
						self.team1 = col.at(0).toPlainText().strip().replace("\xa0", "")
						if self.team1 not in [" ", "", None]:
							self.time = col.at(0).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(0).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.team1 = self.team1.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.team1
							team1.append(time)
							time = {}

						self.team2 = col.at(2).toPlainText().strip().replace("\xa0", "")
						if self.team2 not in [" ", "", None]:
							self.time = col.at(2).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(2).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.team2 = self.team2.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.team2
							team2.append(time)
							time = {}

						self.score = col.at(1).toPlainText().strip().replace(" ", "")

					if len(col) == 2:
						self.team1 = col.at(0).toPlainText().strip().replace("\xa0", "")
						if self.team1 not in [" ", "", None]:
							self.time = col.at(0).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(0).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.team1 = self.team1.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.team1
							team1.append(time)
							time = {}

						self.team2 = col.at(1).toPlainText().strip().replace("\xa0", "")
						if self.team2 not in [" ", "", None]:
							self.time = col.at(1).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(1).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.team2 = self.team2.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.team2
							team2.append(time)
							time = {}

					if self.team1 not in [" ", "", None]:
						summary[self.period]["team1"] = team1

					if self.team2 not in [" ", "", None]:
						summary[self.period]["team2"] = team2

					if self.score:
						summary[self.period]["score"] = self.score
					# print("aaaaaaaa", summary)

			except Exception as e:
				print("Puklo na SUMMARY", e)

			try:
				main = self._frame.findFirstElement("#tab-statistics-0-statistic")
				rows = main.findAll('tr')

				for i in range(len(rows)):

					stats_name = rows.at(i).findAll('td').at(1).toPlainText().strip()
					stats_team1 = rows.at(i).findAll('td').at(0).toPlainText().strip()
					stats_team2 = rows.at(i).findAll('td').at(2).toPlainText().strip()

					statistics[stats_name] = {'team1': stats_team1, 'team2': stats_team2}

			except Exception as e:
				print("Puklo na STATISTICS", e)

			# https://www.flashscore.com/match/OnDFnJ4P/#match-summary
			print("0000000000000000000000000")
			print(summary)
			print()
			print(statistics)
			print("0000000000000000000000000")

			self.resourse_check()
			self.summary_click = True
			QTimer().singleShot(3000, self.match_statistics)
			#dodaj statistiku u redis




	def resourse_check(self):

		print('!!!!!!!!!!!!!!!!!!!!!!iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >= 700000:
			# self.log.info('RESET kolektora - iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print('iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			self.reload_collector()
			print("Presao limit")

	def reload_collector(self):
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		print(self.reset_sport)
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if self.reset_sport in proces_name and "collector" in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "python3 {}".format(proces_name[10:-2])
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue

	#################333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333
	# def get_teams_links(self):
	# 	print("44444444444444444444444444")
	#
	# 	teams = 0
	# 	try:
	# 		main = self._frame.findFirstElement(".stats-table-container")
	#
	# 		teams = main.findAll("tbody").at(0).findAll("tr")
	# 	except:
	# 		print("EXCEPT BRE")
	#
	#
	# 	for i in range(len(teams)):
	# 		team = teams.at(i).findAll("td").at(1).findAll("span").at(1).findAll("a").at(0)
	# 		link_for_team = team.attribute("onclick").replace("javascript:getUrlByWinType('", "").replace("');", "")
	# 		self.redis.sadd("team_links", "https://www.flashscore.com{}".format(link_for_team))
	# 		self.redis.sadd("team_names", team)
	# 		print(team.toPlainText())
	# 		# print("11111111111111111111")
	#
	# 	print("44444444444!!!!!!!!!!!!!!!!!!")
	# 	QTimer().singleShot(1500, self.parse_leagues_links)
	############################################################################################
































	def open_sport_group(self):
		"""
		:description:   metod za kretanje kroz navigaciju i otvaranje liste dogadjaja za naredni neparsovani sport
		:return:
		"""
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

				if nav_sport == self.sport:
					if nav_sports.at(x).hasClass('active'):
						self.tipbet_sport_id = nav_sports.at(x).findAll('a').at(0).attribute('data-sport')
						# print(self.tipbet_sport_id)
						self.collector_timer.start(15000)
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
			self.open_sport.timeout.connect(self.open_sport_group)


			del nav_sport_collection
		else:
			print("Ne postoji ni jedan sport u meniju!!!!!!!!!")

	def collect_events_without_statistics(self):
		"""
		:description:       metod za parsovanje svih evenata u sport grupi
		:return:
		"""
		main = self._frame.findFirstElement('body')


		self.open_sport.stop()
		self.event_watcher_timer.start(500)

		if len(self.parsed_event_hashes):
			del self.parsed_event_hashes
			self.parsed_event_hashes = []

		events = main.findAll('tbody')

		if self.click_tenth_time == 10:
			nav = main.findAll("#live-match-filter ul").at(0)
			last_btn = nav.findAll("li").at(len(nav.findAll("li"))-1).findAll("a").at(0)
			util.simulate_click(last_btn)
			self.click_tenth_time = 0
		else:
			self.click_tenth_time += 1

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

									if ev_time.lower() not in ["half", "end"]:

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
												# kickoff = True

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
						# elif self.sport == "Tennis":
							# if self.EVENT.current_set != "0:0" or self.EVENT.time != "1st":
								# kickoff = True
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
		main_content = self._frame.findFirstElement('body')
		events = main_content.findAll('tbody')
		for z in range(len(events)):
			event = events.at(z)

			event.findAll('.col2 .line2').at(0).removeAllChildren()
			event.findAll('.col4 .line2').at(0).removeAllChildren()

			team_1 = event.findAll('.col2').at(0).toPlainText().strip()
			team_2 = event.findAll('.col4').at(0).toPlainText().strip()

			event_hash = util.generate_event_hash(self.sport, team_1, team_2)

			if self.sport in ['Basketball', 'Hockey', 'Handball']:
				try:
					ot = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip().lower()
				except:
					ot = "pass"

				if ot != "ot" and ot != "et":
					available_event_hashes.append(event_hash)
				# else:
					# print("Preskocio zato sto je OT (ET) ***{}*** {} - {} : {}".format(event_hash, ot, team_1, team_2))
					# self.ot_loger.critical("Preskocio zato sto je OT (ET) ***{}*** {} - {} : {}".format(event_hash, ot, team_1, team_2))

			elif self.sport in ['Football']:
				try:
					old_available_event_hashes_timer = int(self.available_event_hashes_timer[event_hash])
				except:
					old_available_event_hashes_timer = 0
				ot = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip().lower()
				if event.attribute("data-alive-sport-match") == "1":
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

							util.hide_quotas_on_liveboard(event_hash=_)
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
