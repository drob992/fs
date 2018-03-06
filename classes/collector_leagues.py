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
import util
from config import *
import common


class Collector(QWebPage):

	_cursor_position = None

	# define signal
	newChanges = pyqtSignal(dict)

	def __init__(self, parent=None, page_link=None, debug=None, logger=None):
		super(Collector, self).__init__(parent)

		self._parent = parent
		self.debug = debug
		self.log = logger

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

		self._timer = QTimer()
		self._parent.setMouseTracking(True)
		self._cursor_position = QCursor.pos()

		# connect signals and slots
		self.loadFinished.connect(self.read_page)

		if self.debug:
			self.log.info("Flashscore parser started, with headers: ")
			for hd in self._req.rawHeaderList():
				self.log.info("{} : {}".format(hd, self._req.rawHeader(hd)))

		self.first_load = True

	@pyqtSlot()
	def read_page(self):
		"""
		:description:
		:return:
		"""

		if self.first_load:

			self.redis.delete("processed")

			self.statistics = QTimer()
			self.statistics.timeout.connect(self.match_statistics)
			self.statistics.start(10000)

			QTimer().singleShot(2000, self.open_country_menu)
			self.first_load = False

	def open_country_menu(self):

		print("1111111111111111111111")
		main = self._frame.findFirstElement("#main")

		# Mora se raditi iz dva dela, zato sto je kod njih lista u dva diva iz dva dela
		country_list = main.findAll(".menu.country-list").at(2).findAll("li")
		country_list1 = main.findAll(".menu.country-list").at(3).findAll("li")

		for i in range(1, len(country_list)):
			if country_list.at(i).hasAttribute("id"):
				country = country_list.at(i).findAll("a").at(0)
				self.redis.sadd('countries', country.toPlainText().lower().replace(" ", "-"))
				util.simulate_click(country)
				# print(country.toPlainText().strip())
				# print("----------------------------")

		for i in range(0, len(country_list1)):
			if country_list1.at(i).hasAttribute("id"):
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

		# Mora se raditi iz dva dela, zato sto je kod njih lista u dva diva iz dva dela
		country_list = main.findAll(".menu.country-list").at(2).findAll("li")
		country_list1 = main.findAll(".menu.country-list").at(3).findAll("li")

		for i in range(1, len(country_list)):
			if country_list.at(i).hasAttribute("id"):

				# Ovde je izbacena lista "Other Competitions" (Africa, Asia, World, Europe ....)
				if country_list.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
					continue

				country = country_list.at(i).findAll("a").at(0)
				# if country.toPlainText().strip() not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
				# Uzimamo samo Germany
				if country.toPlainText().strip() in ["Germany", "England"]:

					league_list = country_list.at(i).findAll("ul").at(0).findAll("li")
					for x in range(0, len(league_list)):
						league = league_list.at(x).findAll("a").at(0)

						# Uzimamo samo Bundesliga
						if league.toPlainText().strip() in ["Bundesliga", "Premier League"]:
							print(league.toPlainText().strip())
							self.redis.sadd('leagues_links', "https://www.flashscore.com{}".format(league.attribute("href")))
							self.redis.sadd('leagues', league.toPlainText().lower().replace(" ", "-"))
							# print(league.toPlainText().strip())
							# print("----------------------------")

		for i in range(0, len(country_list1)):
			if country_list1.at(i).hasAttribute("id"):

				# Ovde je izbacena lista "Other Competitions" (Africa, Asia, World, Europe ....)
				if country_list1.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
					continue

				country = country_list1.at(i).findAll("a").at(0)
				# if country.toPlainText().strip() not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
				# Uzimamo samo Germany
				if country.toPlainText().strip() in ["Germany", "England"]:

					league_list = country_list1.at(i).findAll("ul").at(0).findAll("li")
					for x in range(0, len(league_list)):
						league = league_list.at(x).findAll("a").at(0)

						# Uzimamo samo Bundesliga
						if league.toPlainText().strip() in ["Bundesliga", "Premier League"]:
							print(league.toPlainText().strip())
							self.redis.sadd('leagues_links', "https://www.flashscore.com{}".format(league.attribute("href")))
							self.redis.sadd('leagues', league.toPlainText().lower().replace(" ", "-"))
							# print(league.toPlainText().strip())
							# print("----------------------------")

		# Posto smo gore izbacili "Other Competitions" moramo rucno dodati world_cup
		self.redis.sadd('leagues_links', "https://www.flashscore.com/football/world/world-cup/")
		self.redis.sadd('leagues', "world-cup")

		print("222222222!!!!!!!!!!!!!!!!!!")
		QTimer().singleShot(3000, self.open_leagues)


	def open_leagues(self):

		print("3333333333333333")

		league_links = self.redis.smembers('leagues_links')

		if self.redis.get("parse_teams"):

			team_links = self.redis.smembers('team_links')

			if len(team_links) == 0:
				self.match_statistics()
				sys.exit()

			# OPEN TEAM LINK
			for link in team_links:
				self.redis.srem("team_links", link)
				print(link+"results")
				if link != "https://www.flashscore.com":
					self._frame.load(QNetworkRequest(QUrl(link+"results")))
					# self.more = True
					QTimer().singleShot(3500, self.parse_team)
				else:
					QTimer().singleShot(3500, self.open_leagues)
				break

		else:
			# Prvo otvaramo lige, kada dodjemo do kraja, setujemo parse_teams na True da bi ulazili u if iznad
			if len(league_links) in [0, 1]:
				print("usaooooooooooo")
				self.redis.set("parse_teams", True)

			for link in league_links:

				self.redis.srem("leagues_links", link)

				# Izbacujemo kupove za sada, potrebni drugacije parsiranje :D
				if "cup" in link.lower() or "offs" in link.lower():
					QTimer().singleShot(3000, self.open_leagues)
					continue

				self._frame.load(QNetworkRequest(QUrl(link)))

				QTimer().singleShot(3500, self.get_teams_standings)

				break

			# break
		print("333333333333!!!!!!!!!!!!!!!!!!")

	def get_teams_standings(self):
		print("44444444444444444444444444")

		groups = None
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

		print("44444444444!!!!!!!!!!!!!!!!!!")
		QTimer().singleShot(1500, self.open_leagues)


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
		home = None
		away = None
		score = None
		win_lose = None

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
						print(time, " - ", home, " - ", away, " - ", score, " - ", win_lose, " - ", id)


		self.redis.sadd("team_names", team_name)
		self.resourse_check()
		QTimer().singleShot(3000, self.open_leagues)
		print("555555555555555!!!!!!!!!!!!!!!!!!")

	def match_statistics(self):

		team_names = self.redis.smembers("team_names")
		print("POKUSAO SAM")
		for team in team_names:

			# self.statistics.stop()
			matches = self.redis.hgetall(team)
			print("STVARNO")
			if matches:

				cmd = 'python3 {}classes/collector_statistics.py'.format(project_root_path)  #
				allready_running = None
				pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
				print("MAJKE MI")
				for pid in pids:
					try:
						tst = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()

						for filename in ["collector_statistics.py"]:
							if filename in str(tst):
								allready_running = True

					except IOError:  # proc has already terminated
						continue

				print(allready_running)
				print("JEL RADI")
				if not allready_running:
					print("PUSTAM")
					cmd += " (1)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (2)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (3)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (4)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (5)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (6)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (7)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (8)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (9)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					time.sleep(2)
					cmd += " (10)"
					subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
				else:
					print("RADI")
			break


	def resourse_check(self):

		print('!!!!!!!!!!!!!!!!!!!!!!iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >= 700000:
			# self.log.info('RESET kolektora - iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print('iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			self.reload_collector()
			print("Presao limit")

	def reload_collector(self):
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if "collector_leagues" in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "python3 {}".format(proces_name[10:-2])
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue


if __name__ == "__main__":

	collector_log = util.parserLog('/var/log/sbp/flashscores/collector_leagues.log', 'flashscore-collector')
	# todo: if gui in sys.argv True
	app = QApplication(sys.argv)
	web = QWebView()
	webpage = Collector(parent=web, page_link=common.live_link, debug=True, logger=collector_log)
	web.setPage(webpage)
	web.setGeometry(780, 0, 1200, 768)
	web.show()

	try:
		sys.exit(app.exec_())
	except Exception as e:
		collector_log.critical('APP: {}'.format(e))
