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

		self.redis = redis.StrictRedis(host='localhost', port=6667, decode_responses=True, password=redis_pass)

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
			print(self.day)

			QTimer().singleShot(3000, self.open_day)
			self.first_load = False

	def open_day(self):

		print("1111111111111111111111")
		main = self._frame.findFirstElement("#fsbody")
		print(len(main.toPlainText()))
		if len(main.toPlainText()) > 20:

			# Otvaramo zeljeni datum (max 7 dana napred nazad od danasnjeg datuma)
			finished_games = main.findAll(".ifmenu").at(0)

			tmp_js = "set_calendar_date('{}')".format(self.day)

			finished_games.evaluateJavaScript(tmp_js)

			QTimer().singleShot(3000, self.open_finished)
		else:
			print("~~~~~~~")
			self.reload_collector()

		print("11111111111!!!!!!!!!!!!!!!!!!!")

	def open_finished(self):

		print("22222222")
		main = self._frame.findFirstElement("#fsbody")

		# Otvaramo tab zavrsene utakmice
		finished_games = main.findAll(".ifmenu").at(0).findAll(".li2").at(0).findAll("a").at(0)
		util.simulate_click(finished_games)

		QTimer().singleShot(3000, self.parse)

		print("222222222!!!!!!!!!!!!!!!!!!!")

	def parse(self):

		print("33333333333")
		main = self._frame.findFirstElement("#fsbody")
		tr = main.findAll("#fs").at(0).findAll(".table-main").at(0).findAll("tr")

		country = None
		country_part = None
		tournament_part = None

		if len(tr) != 0:
			for x in range(len(tr)):
				row = tr.at(x)

				if row.hasClass("league"):
					country = row.findAll(".country").at(0).findAll(".flag").at(0).attribute("title")
					country_part = row.findAll(".country_part").at(0).toPlainText().strip()
					tournament_part = row.findAll(".tournament_part").at(0).toPlainText().strip()
				else:
					timer = row.findAll(".timer").at(0).toPlainText().strip()
					id = row.attribute("id").replace("g_1_", "")
					time = self._frame.findFirstElement("#tzactual").toPlainText().strip().split(" ")[0]
					home = row.findAll(".team-home").at(0).toPlainText().strip()
					away = row.findAll(".team-away").at(0).toPlainText().strip()
					score = row.findAll(".score").at(0).toPlainText().strip().replace("\n", " ").replace(u'\xa0', u' ')
					win_lose = row.findAll(".win_lose_icon").at(0).attribute("title").strip()

					if timer.lower() == "finished":
						event = {"id": x, "sport": "Football", "time": time, "home": home, "away": away,
						         "score": score, "win_lose": win_lose, "country": country,
						         "country_part": country_part, "tournament_part": tournament_part,
						         "flashscore_id": id}

						tournament_list = ["world", "europe", "asia", "africa", "southamerica", "north&centralamerica", "australia&oceania"]
						if all(tournament not in country_part.lower().replace(":", "").replace(" ", "") for tournament in tournament_list):
							self.redis.hset("team-{}".format(home), x, json.dumps(event))

							self.redis.sadd("team_names", home)

						print(country_part, tournament_part)
						print(time, " - ", home, " - ", away, " - ", score, " - ", win_lose, " - ", id)

			print("333333333333335!!!!!!!!!!!!!!!!!!")

			QTimer().singleShot(5000, self.match_statistics)
		else:
			if self.checker_team == 5:
				print("RESTARTTTTTTTT !!!!!!!!!!!!!!!!!!! checker  " + str(self.checker_team))
				self.reload_collector()
			else:
				self.checker_team += 1
				print("++++++++++++++++++ 11111111111111111111111111  checker " + str(self.checker_team))
				QTimer().singleShot(1000, self.parse)

	def match_statistics(self):

		team_names = self.redis.smembers("team_names")
		print("POKUSAO SAM")
		for team in team_names:

			# self.statistics.stop()
			matches = self.redis.hgetall("team-{}".format(team))
			print("STVARNO")
			if matches:

				# cmd = 'python3 {}parser/classes/collector_statistics.py'.format(project_root_path)  #
				cmd = 'python3.4 {}parser/classes/collector_statistics.py'.format(project_root_path)  #
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
					# cmd += " (1)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (2)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (3)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (4)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (5)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (6)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (7)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (8)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (9)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					# time.sleep(2)
					# cmd += " (10)"
					# subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
					sys.exit()
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
				if "collector_per_day" in proces_name and '/bin/sh' not in proces_name:
					print("eeeeeee")
					# relaunch_cmd = "python3 {}".format(proces_name[10:-2])
					relaunch_cmd = "python3.4 {}".format(proces_name[12:-2])
					print(relaunch_cmd)
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue


if __name__ == "__main__":

	collector_log = util.parserLog('/var/log/sbp/flashscore/collector_per_day.log', 'flashscore-collector')

	day = sys.argv[-1]
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
