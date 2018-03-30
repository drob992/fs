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

		if self.debug:
			self.log.info("Flashscore parser started, with headers: ")
			for hd in self._req.rawHeaderList():
				self.log.info("{} : {}".format(hd, self._req.rawHeader(hd)))

		self.first_load = True

	@pyqtSlot()
	def read_page(self):

		if self.first_load:

			self.redis.delete("processed")

			# self.statistics = QTimer()
			# self.statistics.timeout.connect(self.match_statistics)
			# self.statistics.start(60000)

			QTimer().singleShot(1000, self.open_live)
			self.first_load = False

	def open_live(self):

		print("1111111111111111111111")
		main = self._frame.findFirstElement("#main")

		live = main.findAll(".ifmenu-live").at(0).findAll("a").at(0)

		util.simulate_click(live)

		QTimer().singleShot(2000, self.scan_events)


	def scan_events(self):
		print("222222222222222")

		tr = None

		main = self._frame.findFirstElement("#main")
		try:
			tr = main.findAll(".fs-table").at(0).findAll("tr")
		except:
			print("EXCEPT BRE open_team22")

		country_part = None
		tournament_part = None

		for x in range(len(tr)):

			row = tr.at(x)

			if row.hasClass("league"):
				country_part = row.findAll(".country_part").at(0).toPlainText().strip()
				tournament_part = row.findAll(".tournament_part").at(0).toPlainText().strip()
			else:
				id = row.attribute("id").replace("g_1_", "")
				time = row.findAll(".time").at(0).toPlainText().strip()
				timer = row.findAll(".timer").at(0).toPlainText().strip()
				home = row.findAll(".team-home").at(0).toPlainText().strip()
				away = row.findAll(".team-away").at(0).toPlainText().strip()
				score = row.findAll(".score").at(0).toPlainText().strip().replace("\n", " ").replace(u'\xa0', u' ')
				ht_score = row.findAll(".part-top").at(0).toPlainText().strip().replace("\n", " ").replace(u'\xa0', u' ')

				event = {"id": x, "time": time, "timer": timer, "home": home, "away": away, "score": score, "ht_score": ht_score, "country_part": country_part, "tournament_part": tournament_part,
				         "flashscore_id": id}

				print(country_part, tournament_part)
				print(time, " - ", home, " - ", away, " - ", score, " - ", ht_score, " - ", timer, " - ", id)

		# self.redis.sadd("team_names", team_name)
		# self.resourse_check()
		# QTimer().singleShot(3000, self.open_leagues)
		# print("555555555555555!!!!!!!!!!!!!!!!!!")

	def match_statistics(self):

		team_names = self.redis.smembers("team_names")
		print("POKUSAO SAM")
		for team in team_names:

			# self.statistics.stop()
			matches = self.redis.hgetall(team)
			print("STVARNO")
			if matches:

				cmd = 'xvfb-run -a python3 {}classes/collector_statistics.py'.format(project_root_path)  #
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
					relaunch_cmd = "xvfb-run -a python3 {}".format(proces_name[10:-2])
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
