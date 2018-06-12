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

	def __init__(self, parent=None, page_link=None, debug=None, logger=None, day=None):
		super(Collector, self).__init__(parent)

		self._parent = parent
		self.debug = debug
		self.log = logger
		self.day = day

		self.EVENT = None

		self.redis = redis.StrictRedis(host=redis_master_host, port=redis_master_port, decode_responses=True, password=redis_pass)

		self._url = QUrl(page_link)
		self._req = QNetworkRequest(self._url)

		self._req.setRawHeader(b"Accept-Language", b"en-US,en;q=0.8")
		self._req.setRawHeader(b"Cache-Control", b"no-cache")
		self._req.setRawHeader(b"Connection", b"keep-alive")
		self._req.setRawHeader(b"User-Agent", common.uAgent)
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
			print(self.day)
			if self.redis.get("per_day_standings_parser"):
				self.open_teams_standings()
			QTimer().singleShot(3000, self.open_day)
			self.first_load = False

	def open_day(self):
		print("open_day")
		main = self._frame.findFirstElement("#fsbody")
		if len(main.toPlainText()) > 20:

			# Otvaramo zeljeni datum (max 7 dana napred nazad od danasnjeg datuma)
			finished_games = main.findAll(".ifmenu").at(0)
			tmp_js = "set_calendar_date('{}')".format(self.day)
			finished_games.evaluateJavaScript(tmp_js)
			QTimer().singleShot(3000, self.open_finished)
		else:
			self.reload_collector()

	def open_finished(self):
		print("open_finished")

		main = self._frame.findFirstElement("#fsbody")

		# Otvaramo tab zavrsene utakmice
		finished_games = main.findAll(".ifmenu").at(0).findAll(".li2").at(0).findAll("a").at(0)
		util.simulate_click(finished_games)

		QTimer().singleShot(3000, self.open_country_menu)


	def open_country_menu(self):
		print("open_country_menu")
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

	def get_league_links(self):

		print("get_league_links")
		main = self._frame.findFirstElement("#main")

		# Mora se raditi iz dva dela, zato sto je kod njih lista u dva diva iz dva dela
		country_list = main.findAll(".menu.country-list").at(2).findAll("li")
		country_list1 = main.findAll(".menu.country-list").at(3).findAll("li")
		if self.redis.get("parse_leagues_per_day") != "True":
			for i in range(1, len(country_list)):
				if country_list.at(i).hasAttribute("id"):

					# Ovde je izbacena lista "Other Competitions" (Africa, Asia, World, Europe ....)
					if country_list.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
						continue

					country = country_list.at(i).findAll("a").at(0)
					# if country.toPlainText().strip() not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
					# Uzimamo samo Germany
					# if country.toPlainText().strip() in common.europe:
					league_list = country_list.at(i).findAll("ul").at(0).findAll("li")
					for x in range(0, len(league_list)):
						league = league_list.at(x).findAll("a").at(0)
						if league.toPlainText().strip():
							# if "cup" not in league.toPlainText().lower().strip():
							self.redis.hset('per_day_leagues_{}'.format(country.toPlainText().lower().strip()), league.toPlainText().lower().replace(" ", "-"), "https://www.flashscore.com{}".format(league.attribute("href")))


			for i in range(0, len(country_list1)):
				if country_list1.at(i).hasAttribute("id"):

					# Ovde je izbacena lista "Other Competitions" (Africa, Asia, World, Europe ....)
					if country_list1.at(i).attribute("id") in ['lmenu_1' 'lmenu_2', 'lmenu_3', 'lmenu_4', 'lmenu_5', 'lmenu_6', 'lmenu_7', 'lmenu_8']:
						continue

					country = country_list1.at(i).findAll("a").at(0)
					# if country.toPlainText().strip() not in ["Africa", "Asia", "Australia & Oceania", "Europe", "North & Central America", "South America", "World"]:
					# Uzimamo samo Germany
					# if country.toPlainText().strip() in common.europe:
					league_list = country_list1.at(i).findAll("ul").at(0).findAll("li")
					for x in range(0, len(league_list)):
						league = league_list.at(x).findAll("a").at(0)
						if league.toPlainText().strip():
							# if "cup" not in league.toPlainText().lower().strip():
							self.redis.hset('per_day_leagues_{}'.format(country.toPlainText().lower().strip()), league.toPlainText().lower().replace(" ", "-"), "https://www.flashscore.com{}".format(league.attribute("href")))

			# Posto smo gore izbacili "Other Competitions" moramo rucno dodati world_cup
			self.redis.hset('per_day_leagues_world', "world-cup", "https://www.flashscore.com/football/world/world-cup/")
		self.redis.set("parse_leagues_per_day", True)
		QTimer().singleShot(3000, self.parse)


	def parse(self):
		print("parse")

		if self.redis.get("per_day_standings_parser"):
			self.open_teams_standings()

		main = self._frame.findFirstElement("#fsbody")
		table = main.findAll("#fs").at(0).findAll(".table-main").at(0).findAll('table')

		if len(table) != 0:
			for i in range(len(table)):
				row = table.at(i).findAll('thead').at(0).findAll("tr").at(0)

				country_part = row.findAll(".country_part").at(0).toPlainText().strip().lower().replace(":", "")
				tournament_part = row.findAll(".tournament_part").at(0).toPlainText().strip().lower().replace(" ", "-")

				all_leagues = self.redis.hgetall("per_day_leagues_{}".format(country_part))
				for league in all_leagues:
					if league in tournament_part:
						self.redis.sadd("per_day_leagues_links", self.redis.hget("per_day_leagues_{}".format(country_part), league))

			self.redis.set("per_day_standings_parser", True)
			QTimer().singleShot(5000, self.open_teams_standings)
		else:
			if self.checker_team == 5:
				print("RESTARTTTTTTTT !!!!!!!!!!!!!!!!!!! checker  " + str(self.checker_team))
				self.reload_collector()
			else:
				self.checker_team += 1
				QTimer().singleShot(1000, self.parse)


	def open_teams_standings(self):
		print("\nopen_teams_standings\n")
		leagues = self.redis.smembers('per_day_leagues_links')

		print(len(leagues))
		if len(leagues) == 0:
			self.redis.delete("per_day_standings_parser")
			print("Nema vise")
			time.sleep(300)
			self.reload_collector()

		for link in leagues:
			print("USAO U LINK")
			print(link)
			self._frame.load(QNetworkRequest(QUrl(link)))
			QTimer().singleShot(5000, self.get_teams_standings)
			self.redis.srem('per_day_leagues_links', link)
			break


	def get_teams_standings(self):
		print("\nget_teams_standings\n")

		bubble = None
		groups = None
		groups_draw = None
		league_name = None
		country = None
		year = None
		league_group = "/"
		try:
			main = self._frame.findFirstElement("#main")
			groups = main.findAll(".stats-table-container").at(0).findAll("table")
			groups_draw = main.findAll(".playoff").at(0).toPlainText().strip()
			bubble = main.findAll(".bubble").at(0).findAll("a").at(0)
			country = main.findAll(".tournament").at(0).findAll("a").at(1).toPlainText().strip()
			league_name = main.findAll('.tournament-name').at(0).toPlainText().strip()
			year = main.findAll('.tournament').at(0).toPlainText().strip().split(" » ")[-1]
		except:
			self.log.error("get team standings [1]")

		print("Grupa", len(groups))
		for i in range(len(groups)):
			tr = groups.at(i).findAll("tr")
			for x in range(len(tr)):
				if tr.at(x).hasClass("main"):
					league_group = tr.at(x).findAll("th").at(1).toPlainText().strip()
				else:
					rank = tr.at(x).findAll("td").at(0).toPlainText().strip()
					rank_title = tr.at(x).findAll("td").at(0).attribute("title").strip()
					rank_class = tr.at(x).findAll("td").at(0).attribute("class").replace("rank col_rank no", "").replace("col_sorted", "").strip()
					team = tr.at(x).findAll("td").at(1).findAll("span").at(1).findAll("a").at(0)
					played = tr.at(x).findAll("td").at(2).toPlainText().strip()
					wins = tr.at(x).findAll("td").at(3).toPlainText().strip()

					if len(tr.at(x).findAll("td")) == 9:
						draws = tr.at(x).findAll("td").at(4).toPlainText().strip()
						losses = tr.at(x).findAll("td").at(5).toPlainText().strip()
						goals = tr.at(x).findAll("td").at(6).toPlainText().strip()
						points = tr.at(x).findAll("td").at(7).toPlainText().strip()
					elif len(tr.at(x).findAll("td")) == 10:
						draws = "0"
						losses = tr.at(x).findAll("td").at(6).toPlainText().strip()
						goals = tr.at(x).findAll("td").at(7).toPlainText().strip()
						points = tr.at(x).findAll("td").at(8).toPlainText().strip()
					else:
						draws = tr.at(x).findAll("td").at(4).toPlainText().strip()
						losses = tr.at(x).findAll("td").at(5).toPlainText().strip()
						goals = tr.at(x).findAll("td").at(6).toPlainText().strip()
						points = tr.at(x).findAll("td").at(7).toPlainText().strip()

					link_for_team = team.attribute("onclick").replace("javascript:getUrlByWinType('", "").replace("');", "")
					self.redis.sadd("team_links", "https://www.flashscore.com{}".format(link_for_team))
					self.redis.hset("standings@{}@{}".format(league_name, country), team.toPlainText().strip(), {"country":country, "league_name":league_name, "team":team.toPlainText().strip(), "played":played, "wins":wins, "draws":draws, "losses":losses, "goals":goals, "points":points, "year": year, "league_group":league_group, "rank_title":rank_title, "rank":rank, "rank_class":rank_class})

		if len(bubble.toPlainText().strip()) > 1 and not main.findAll(".bubble").at(0).findAll("li").at(0).hasClass("selected"):
			self.log.info("Kliknuo na bubble class-u")
			print("KLIKNUO")
			util.simulate_click(bubble)
			QTimer().singleShot(4000, self.get_teams_standings)

		else:
			if len(groups_draw):
				print("000000000000")
				self.redis.set("restart_standings", False)
				QTimer().singleShot(1500, self.open_teams_standings)

			elif len(groups) == 0:
				if self.checker == 5:
					print("1111111111111")
					self.redis.set("restart_standings", True)
					self.reload_collector()
				else:
					self.checker += 1
					print("222222222")
					QTimer().singleShot(1000, self.get_teams_standings)
			else:
				self.redis.set("restart_standings", False)
				QTimer().singleShot(500, self.resourse_check)
				QTimer().singleShot(1500, self.open_teams_standings)


	def resourse_check(self):

		print('!!!!!!!!!!!!!!!!!!!!!!iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >= 700000:
			print('iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print("Presao limit")
			self.reload_collector()

	def reload_collector(self):
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if "collector_per_day" in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "python3 {}".format(proces_name[10:-2])
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue


if __name__ == "__main__":

	collector_log = util.parserLog('/var/log/sbp/flashscore/collector_per_day.log', 'flashscore-collector-per-day')

	day = sys.argv[-1]

	try:
		day = int(day)
	except:
		day = 0

	print(day)
	# todo: if gui in sys.argv True
	app = QApplication(sys.argv)
	web = QWebView()
	webpage = Collector(parent=web, page_link=common.live_link, debug=True, logger=collector_log, day=day)
	web.setPage(webpage)
	web.setGeometry(780, 0, 1200, 768)
	web.show()

	try:
		sys.exit(app.exec_())
	except Exception as e:
		collector_log.critical('APP: {}'.format(e))
