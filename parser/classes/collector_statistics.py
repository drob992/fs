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
import random

class Collector(QWebPage):

	_cursor_position = None

	# define signal
	newChanges = pyqtSignal(dict)

	def __init__(self, parent=None, page_link=None, debug=None, logger=None, order_num=None):
		super(Collector, self).__init__(parent)

		self._parent = parent
		self.debug = debug
		self.log = logger
		self.order_num = order_num

		self.EVENT = None

		self.redis = redis.StrictRedis(host=redis_master_host, port=redis_master_port, decode_responses=True, password=redis_pass)

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

		self.summary_click = True
		self._check_hash_counter = 0

		self._content_hash = None

		if self.debug:
			self.log.info("Flashscore parser started, with headers: ")
			for hd in self._req.rawHeaderList():
				self.log.info("{} : {}".format(hd, self._req.rawHeader(hd)))

		self.first_load = True

	@pyqtSlot()
	def read_page(self):
		if self.first_load:

			self.hash = QTimer()
			self.hash.timeout.connect(self.check_hash)
			self.hash.start(5000)

			QTimer().singleShot(2000, self.match_statistics)
			self.first_load = False

	def check_hash(self):

		self._check_hash_counter += 1
		if self._check_hash_counter == 6:
			self.log.info("\nCheck hash brojac i limit za neaktivnost su se poklopili, restartujemo stranu")
			self.redis.hdel("processed", self.team, self.i)
			self.reload_collector()
		else:
			content_area = self._frame.findFirstElement('#content-all').toPlainText().strip()
			content_hash = util.hash(content_area)

			if self._content_hash == content_hash:
				self._check_hash_counter += 1
				self.log.info("{} sekundi nema promena na prozoru ".format(self._check_hash_counter))
				if self._check_hash_counter == 6:
					self.log.critical("Resetujemo prozor, nije bilo promena do zadatog limita")
					self.redis.hdel("processed", self.team, self.i)
					self.reload_collector()
			else:
				self._check_hash_counter = 0

			self._content_hash = content_hash

	def match_statistics(self):

		team_names = self.redis.smembers("team_names")

		if len(team_names) == 0:
			time.sleep(5)
			cmd = 'python3.4 {}parser/stop.py'.format(project_root_path)
			# cmd = 'xvfb-run -a python3 {}parser/stop.py'.format(project_root_path)
			subprocess.Popen(shlex.split(cmd), stderr=None, stdout=None)
			QTimer().singleShot(30000, self.match_statistics)

		team_names = (list(team_names))
		random.shuffle(team_names)
		for team in team_names:

			matches = self.redis.hgetall("team-{}".format(team))

			if len(matches) == 0 or team in ["", " ", None]:
				try:
					self.redis.srem("team_names", team)
					continue
				except:
					self.log.error("Ne moze da uradi brisanje")
					print("Ne moze da uradi brisanje")
					continue
			else:
				for i in matches:
					if self.redis.hget("processed", team) == i:
						QTimer().singleShot(2000, self.match_statistics)
						break

					self.redis.hset("processed", team, i)
					self.redis.expire("processed", 10)

					match = json.loads(matches[i])

					self._frame.load(QNetworkRequest(QUrl("https://www.flashscore.com/match/{}/#match-summary".format(match['flashscore_id']))))

					self.summary_click = True
					QTimer().singleShot(3500, self.parse_statistics)

					self.team = team
					self.i = i

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
				QTimer().singleShot(3500, self.parse_statistics)
			except Exception as e:
				self.summary_click = False
				QTimer().singleShot(3000, self.parse_statistics)
		else:
			try:
				try:
					main = self._frame.findFirstElement("#summary-content")
					rows = main.findAll("tr")
				except Exception as e:
					self.log.error("\nNe mogu da nadjem stranicu\norder_num = ", self.order_num)
					print("\nNe mogu da nadjem stranicu\norder_num = ", self.order_num)
					self.reload_collector()

				self.period = None

				time = {}
				team1 = []
				team2 = []
				summary["1st Half"] = {}
				summary["2nd Half"] = {}
				summary["Extra Time"] = {}
				summary["Penalties"] = {}

				for i in range(len(rows)):
					self.text_left = None
					self.text_right = None
					self.score = None
					col = rows.at(i).findAll('td')

					if len(col) == 1:
						self.period = col.at(0).toPlainText().strip()
						team1 = []
						team2 = []

					if len(col) == 3:
						self.text_left = col.at(0).toPlainText().strip().replace("\xa0", "")
						if self.text_left not in [" ", "", None]:
							self.time = col.at(0).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(0).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.text_left = self.text_left.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.text_left
							team1.append(time)
							time = {}

						self.text_right = col.at(2).toPlainText().strip().replace("\xa0", "")
						if self.text_right not in [" ", "", None]:
							self.time = col.at(2).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(2).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.text_right = self.text_right.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.text_right
							team2.append(time)
							time = {}

						self.score = col.at(1).toPlainText().strip().replace(" ", "")

					if len(col) == 2:
						self.text_left = col.at(0).toPlainText().strip().replace("\xa0", "")
						if self.text_left not in [" ", "", None]:
							self.time = col.at(0).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(0).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.text_left = self.text_left.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.text_left
							team1.append(time)
							time = {}

						self.text_right = col.at(1).toPlainText().strip().replace("\xa0", "")
						if self.text_right not in [" ", "", None]:
							self.time = col.at(1).findAll(".time-box").at(0).toPlainText().strip().replace("\n ", "")
							self.type = col.at(1).findAll(".icon").at(0).attribute("class").replace("icon ", "")
							self.text_right = self.text_right.replace(self.time, "").replace(self.type, "").replace("\n ", "")
							time[self.time] = self.type, self.text_right
							team2.append(time)
							time = {}

					if self.period not in [" ", "", None]:
						print("period", self.period)
						if self.text_left not in [" ", "", None]:
							print("text_left", self.period)
							summary[self.period]["team1"] = team1

						if self.text_right not in [" ", "", None]:
							print("text_right", self.period)
							summary[self.period]["team2"] = team2

						if self.score not in [" ", "", None]:
							print("score", self.period)
							print(self.score)
							summary[self.period]["score"] = self.score

				try:
					try:
						summary_btn = self._frame.findFirstElement("#a-match-statistics")
						util.simulate_click(summary_btn)
					except Exception as e:
						self.log.error("parse_statistics [1]", e)

					main = self._frame.findFirstElement("#tab-statistics-0-statistic")
					rows = main.findAll('tr')

					for i in range(len(rows)):
						stats_name = rows.at(i).findAll('td').at(1).toPlainText().strip()
						stats_team1 = rows.at(i).findAll('td').at(0).toPlainText().strip()
						stats_team2 = rows.at(i).findAll('td').at(2).toPlainText().strip()
						statistics[stats_name] = {'team1': stats_team1, 'team2': stats_team2}
						print(statistics[stats_name])
				except Exception as e:
					self.log.error("\nPotraga za statistikom nije uspela\n", e)
					print("\nPotraga za statistikom nije uspela\n", e)

			except Exception as e:
				self.log.error("Puklo na STATISTICS order_num = ", self.order_num, e)
				self.log.error("Puklo na SUMMARY order_num = ", self.order_num, e)
				self.redis.hdel("processed", self.team, self.i)
				print("Puklo na STATISTICS order_num = ", self.order_num, e)
				print("Puklo na SUMMARY order_num = ", self.order_num, e)
				self.redis.hset("processed", self.team, self.i)
				self.match_statistics()

			try:
				event = json.loads(self.redis.hget("team-{}".format(self.team), self.i))

				self.redis.hset("old-"+self.team, self.i, json.dumps(event))

				event["statistics"] = statistics
				event["summary"] = summary

				self.redis.hset("new-"+self.team, self.i, json.dumps(event))

				# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
				# data = util.redis_emmit(self.redis, self.team, event, True)
				# self.log.info('Collector emmit: {}'.format(data))
				# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

				self.redis.hdel("team-{}".format(self.team), self.i)

				self.resourse_check()
				self.summary_click = True
				QTimer().singleShot(2000, self.match_statistics)
			except Exception as e:
				self.log.error("Doslo je do otvaranja istog eventa u 2 prozora, vec je upisan", self.team, self.i, "--", e)
				print("Doslo je do otvaranja istog eventa u 2 prozora, vec je upisan", self.team, self.i, "--", e)
				self.redis.hdel("processed", self.team, self.i)
				QTimer().singleShot(2000, self.match_statistics)


	def resourse_check(self):

		# print('!!!!!!!!!!!!!!!!!!!!!!iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >= 600000:
			# self.log.info('RESET kolektora - iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print('iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print("Presao limit\norder_num = ", self.order_num)
			self.reload_collector()

	def reload_collector(self):
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if "collector_statistics" in proces_name and str(self.order_num) in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "python3.4 collector_statistics.py {}".format(self.order_num)
					# relaunch_cmd = "xvfb-run -a python3 collector_statistics.py {}".format(self.order_num)
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue


if __name__ == "__main__":

	order_num = sys.argv[-1]

	collector_log = util.parserLog('/var/log/sbp/flashscore/collector_statistics.log', 'flashscore-collector-statistics')
	app = QApplication(sys.argv)
	web = QWebView()
	webpage = Collector(parent=web, page_link=common.live_link, debug=True, logger=collector_log, order_num=order_num)
	web.setPage(webpage)
	web.setGeometry(780, 0, 1200, 768)
	web.show()

	try:
		sys.exit(app.exec_())
	except Exception as e:
		collector_log.critical('APP: {}'.format(e))

