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

		self.checker = 0
		self.checker_team = 0
		if self.debug:
			self.log.info("Flashscore parser started, with headers: ")
			for hd in self._req.rawHeaderList():
				self.log.info("{} : {}".format(hd, self._req.rawHeader(hd)))

		self.first_load = True

	@pyqtSlot()
	def read_page(self):

		if self.first_load:

			if self.redis.get("restart_standings") and self.redis.get("restart_standings") == "True":
				self.redis.set("restart_standings", False)
				link = self.redis.get("s-link")
				self._frame.load(QNetworkRequest(QUrl(link)))
				print("restart_standings TRUE")
				QTimer().singleShot(2000, self.get_teams_standings)
				self.first_load = False

			elif self.redis.get("restart_team") and self.redis.get("restart_team") == "True":
				self.redis.set("restart_team", False)
				link = self.redis.get("t-link")
				self._frame.load(QNetworkRequest(QUrl(link + "results")))
				print("restart_team TRUE")
				QTimer().singleShot(2000, self.parse_team)
				self.first_load = False

			else:
				self.redis.delete("processed")

				self.statistics = QTimer()
				self.statistics.timeout.connect(self.match_statistics)
				self.statistics.start(10000)

				QTimer().singleShot(2000, self.open_country_menu)


				self.active = QTimer()
				self.active.timeout.connect(self.leagues_active)
				self.active.start(5000)

				self.first_load = False

	def leagues_active(self):
		self.redis.set("leagues_active", True)
		self.redis.expire("leagues_active", 30)

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

		for i in range(0, len(country_list1)):
			if country_list1.at(i).hasAttribute("id"):
				country1 = country_list1.at(i).findAll("a").at(0)
				util.simulate_click(country1)
				self.redis.sadd('countries', country1.toPlainText().lower().replace(" ", "-"))

		QTimer().singleShot(2000, self.get_league_links)

		print("11111111111!!!!!!!!!!!!!!!!!!!")

	def get_league_links(self):

		print("22222222222222222")
		main = self._frame.findFirstElement("#main")

		# Mora se raditi iz dva dela, zato sto je kod njih lista u dva diva iz dva dela
		country_list = main.findAll(".menu.country-list").at(2).findAll("li")
		country_list1 = main.findAll(".menu.country-list").at(3).findAll("li")
		if self.redis.get("parse_leagues") != "True":
			for i in range(1, len(country_list)):
				if country_list.at(i).hasAttribute("id"):

					# Ovde je izbacena lista "Other Competitions" (Africa, Asia, World, Europe ....)
					if country_list.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
						continue

					country = country_list.at(i).findAll("a").at(0)
					# if country.toPlainText().strip() not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
					# Uzimamo samo Germany
					if country.toPlainText().strip() in common.europe:

						league_list = country_list.at(i).findAll("ul").at(0).findAll("li")
						for x in range(0, len(league_list)):
							league = league_list.at(x).findAll("a").at(0)

							# Uzimamo samo Bundesliga
							if league.toPlainText().strip():
								# if "cup" not in league.toPlainText().lower().strip():
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
					if country.toPlainText().strip() in common.europe:

						league_list = country_list1.at(i).findAll("ul").at(0).findAll("li")
						for x in range(0, len(league_list)):
							league = league_list.at(x).findAll("a").at(0)

							# Uzimamo samo Bundesliga
							if league.toPlainText().strip():
								# if "cup" not in league.toPlainText().lower().strip():
								print(league.toPlainText().strip())
								self.redis.sadd('leagues_links', "https://www.flashscore.com{}".format(league.attribute("href")))
								self.redis.sadd('leagues', league.toPlainText().lower().replace(" ", "-"))
								# print(league.toPlainText().strip())
								# print("----------------------------")

			# Posto smo gore izbacili "Other Competitions" moramo rucno dodati world_cup
			# self.redis.sadd('leagues_links', "https://www.flashscore.com/football/world/world-cup/")
			# self.redis.sadd('leagues', "world-cup")

		self.redis.set("parse_leagues", True)
		print("222222222!!!!!!!!!!!!!!!!!!")
		QTimer().singleShot(3000, self.open_leagues)


	def open_leagues(self):

		print("3333333333333333")

		league_links = self.redis.smembers('leagues_links')

		if self.redis.get("parse_teams") and self.redis.get("parse_teams") == "True":
			print("333111111")
			team_links = self.redis.smembers('team_links')

			if len(team_links) == 0:
				self.match_statistics()
				sys.exit()

			# OPEN TEAM LINK
			for link in team_links:
				self.redis.srem("team_links", link)
				self.redis.set("t-link", link)
				print(link+"results")
				if link != "https://www.flashscore.com":
					self._frame.load(QNetworkRequest(QUrl(link+"results")))

					QTimer().singleShot(3000, self.parse_team)
				else:
					QTimer().singleShot(3500, self.open_leagues)
				break

		else:
			print("33312222")
			# Prvo otvaramo lige, kada dodjemo do kraja, setujemo parse_teams na True da bi ulazili u if iznad
			if len(league_links) in [0, 1]:
				print("3331444441")
				print(len(league_links))
				self.redis.set("parse_teams", True)

			for link in league_links:

				self.redis.srem("leagues_links", link)
				self.redis.set("s-link", link)
				print(link.lower())
				# Izbacujemo kupove za sada, potrebni drugacije parsiranje :D
				if "cup" in link.lower() and link.lower() != "https://www.flashscore.com/football/world/world-cup/" or "offs" in link.lower():
					QTimer().singleShot(3000, self.open_leagues)
					continue

				self._frame.load(QNetworkRequest(QUrl(link)))

				QTimer().singleShot(3000, self.get_teams_standings)

				break

			# break
		print("333333333333!!!!!!!!!!!!!!!!!!")

	def get_teams_standings(self):
		print("44444444444444444444444444")

		bubble = None
		groups = None
		groups_draw = None
		league_name = None
		country = None
		year = None
		try:
			main = self._frame.findFirstElement("#main")
			groups = main.findAll(".stats-table-container").at(0).findAll("tbody")
			groups_draw = main.findAll(".playoff").at(0).toPlainText().strip()
			bubble = main.findAll(".bubble").at(0).findAll("a").at(0)
			country = main.findAll(".tournament").at(0).findAll("a").at(1).toPlainText().strip()
			league_name = main.findAll('.tournament-name').at(0).toPlainText().strip()
			year = main.findAll('.tournament').at(0).toPlainText().strip().split(" » ")[-1]
		except:
			print("EXCEPT BRE 444444444")

		print(country, league_name)

		for i in range(len(groups)):
			teams = groups.at(i).findAll("tr")
			print("Teams", len(teams))
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
				self.redis.hset("standings-%s" % league_name, team.toPlainText().strip(), {"country":country, "league_name":league_name, "team":team.toPlainText().strip(), "played":played, "wins":wins, "draws":draws, "losses":losses, "goals":goals, "points":points, "year": year})
				# print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
				# print(team.toPlainText(), played, wins, draws, losses, goals, points)

		print("###################################")
		print("bubble", (bubble.toPlainText().strip()))
		print(main.findAll(".bubble").at(0).findAll("li").at(0).hasClass("selected"))
		print(main.findAll(".bubble").at(0).findAll("li").at(0).attribute("class"))
		print(bubble)
		print("!!!!!!!!!!!!!!!!!!!!!!!!")
		if len(bubble.toPlainText().strip()) > 1 and not main.findAll(".bubble").at(0).findAll("li").at(0).hasClass("selected"):
			print("KLIKNUO")
			util.simulate_click(bubble)
			QTimer().singleShot(4000, self.get_teams_standings)

		else:
			print("Groups", len(groups))
			if len(groups_draw):
				print("44444444444!!!!!!!!!!!!!!!!!!wwwwwwwwwwwwwwwwwwwwwwwwwww")
				self.redis.set("restart_standings", False)
				QTimer().singleShot(1500, self.open_leagues)

			elif len(groups) == 0:
				if self.checker == 5:
					print("RESTARTTTTTTTT !!!!!!!!!!!!!!!!!!!!")
					self.redis.set("restart_standings", True)
					self.reload_collector()
				else:
					self.checker += 1
					print("+++++++++++++++ 11111111111111111111111111")
					QTimer().singleShot(1000, self.get_teams_standings)
			else:
				print("44444444444!!!!!!!!!!!!!!!!!!")
				self.redis.set("restart_standings", False)
				QTimer().singleShot(1500, self.open_leagues)

	def parse_team(self):
		print("555555555555555555")

		self.redis.set("restart_standings", False)
		self.redis.set("restart_team", False)

		tr = None
		team_name = None
		country =None

		main = self._frame.findFirstElement("#main")
		try:
			country = main.findAll(".tournament").at(0).findAll("a").at(1).toPlainText().strip()
		except:
			print("Pukloeeeeee")

		tr = main.findAll("#fs-results").at(0).findAll("tr")
		team_name = main.findAll('.team-name').at(0).toPlainText().strip()

		opened_team = self.redis.get("t-link").split("/")[4]
		menu = main.findAll(".ifmenu").at(0).findAll("a").at(0).attribute("href")

		print("|\n{}\n{}\n|".format(opened_team, menu))
		if opened_team not in menu:
			print("\n\nONAJ BAG KAD ZABODE TIM\n\n")
			self.redis.set("restart_team", True)
			self.reload_collector()

		country_part = None
		tournament_part = None

		try:
			if team_name is None or country is None:
				if self.checker_team == 5:
					print("RESTARTTTTTTTT !!!!!!!!!!!!!!!!!!! checker_team  " + str(self.checker_team))
					self.redis.set("restart_team", True)
					self.reload_collector()
				else:
					self.checker_team += 1
					print("++++++++++++++++++ 11111111111111111111111111  checker_team " + str(self.checker_team))
					QTimer().singleShot(1000, self.parse_team)
			else:
				self.redis.sadd("teams_countries", "{}@{}".format(team_name, country))
				print("\n\n\n\n" + team_name)
				print("teams_countries", "{}@{}".format(team_name, country))
		except:
			print("EXCEPT BRE open_team3333")

		if len(tr) != 0:
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
							event = {"id":x, "sport":"Football", "time":time, "home":home, "away":away, "score":score, "win_lose":win_lose, "country":country, "country_part":country_part, "tournament_part":tournament_part, "flashscore_id":id}

							###  OVDE JE PROBLEM
							### PRIMER: U ENGLESKOJ PREMIJER LIGI, IGRAJU TIMOVI IZ WELSA
							### ZATO NE MOZEMO KORISTITI "IF" DOLE ISPOD, ZA TE TIMOVE NECE PROCI UPIS

							# if country.title().replace(":","").replace(" ", "") == country_part.title().replace(":","").replace(" ", ""):# and team_name == "Bayern Munich":
							tournament_list = ["world", "europe", "asia", "africa", "southamerica", "north&centralamerica", "australia&oceania"]
							if all(tournament not in country_part.lower().replace(":","").replace(" ", "") for tournament in tournament_list):
								self.redis.hset("team-{}".format(team_name), x, json.dumps(event))

							# print(country_part, tournament_part)
							# print(time, " - ", home, " - ", away, " - ", score, " - ", win_lose, " - ", id)

			print("\n\n\n\n" + team_name)
			print("YYYYYYYYYYYYYYYYYYYYYYYYYYYYYY\n\n\n\n")
			self.redis.sadd("team_names", team_name)

			QTimer().singleShot(1500, self.resourse_check)
			QTimer().singleShot(2500, self.open_leagues)
			print("555555555555555!!!!!!!!!!!!!!!!!!")
		else:
			if self.checker_team == 5:
				print("RESTARTTTTTTTT !!!!!!!!!!!!!!!!!!! checker_team  " + str(self.checker_team))
				self.redis.set("restart_team", True)
				self.reload_collector()
			else:
				self.checker_team += 1
				print("++++++++++++++++++ 11111111111111111111111111  checker_team " + str(self.checker_team))
				QTimer().singleShot(1000, self.parse_team)

		print("\n\n")

	def match_statistics(self):

		team_names = self.redis.smembers("team_names")
		for team in team_names:

			# self.statistics.stop()
			matches = self.redis.hgetall("team-{}".format(team))
			if matches:

				# cmd = 'python3 {}parser/classes/collector_statistics.py'.format(project_root_path)  #
				cmd = 'python3.4 {}parser/classes/collector_statistics.py'.format(project_root_path)  #
				allready_running = None
				pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
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
					for i in range(0, common.statistics_num):
						# cmd = 'python3 {}parser/classes/collector_statistics.py ({})'.format(project_root_path, i)  #
						cmd = 'python3.4 {}parser/classes/collector_statistics.py ({})'.format(project_root_path, i)
						subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
						time.sleep(2)
				else:
					print("RADI")
			break


	def resourse_check(self):

		print('!!!!!!!!!!!!!!!!!!!!!!iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		self.settings().setAttribute(QWebSettings.clearMemoryCaches(), True)
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
					# relaunch_cmd = "python3 {}".format(proces_name[10:-2])
					relaunch_cmd = "python3.4 {}".format(proces_name[12:-2])
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue


if __name__ == "__main__":

	collector_log = util.parserLog('/var/log/sbp/flashscore/collector_leagues.log', 'flashscore-collector')
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
