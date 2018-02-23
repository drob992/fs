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

		self.summary_click = True
		self._check_hash_counter = 0

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

			# self.statistics = QTimer()
			# self.statistics.timeout.connect(self.match_statistics)
			# self.statistics.start(10000)

			QTimer().singleShot(2000, self.match_statistics)
			self.first_load = False


	def check_hash(self):
		"""
		:description:   metod koji sluzi kao delay za pocetak parsovanja stranice
		:param seconds: koliko puta (sekundi) je potrebno da hash ostane nepromenjen da bi stranica bila spremna
		:return:
		"""
	################################################################################################################################################
		main = self._frame.findFirstElement('#Main')

		if main.isNull():

			self._check_hash_counter += 1
			if self._check_hash_counter == common.window_not_active_limit[str(self._event_sport)]:
				self.log.info("\nCheck hash brojac i limit za neaktivnost su se poklopili, restartujemo stranu")
				self.reload_single_page()
		else:

			check_hash_sport = [True, "", ""]
			if self.delay_kickoff_log is True:
				if self._event_sport == "Football":
					ht_flag = main.findAll('.ml1-Anims_H2Text').at(0).toPlainText().strip()
					kickoff_flag = main.findAll('.ml1-ScoreHeader_AdditionalText').at(0).toPlainText().strip()
					kickoff_flag2 = main.findAll('.ml1-FixtureInfo_KickOff').at(0).toPlainText().strip()
					clock45_flag = main.findAll('.ml1-ScoreHeader_Clock').at(0).toPlainText().strip()

					if ht_flag != 'Half Time' and 'Kick Off' not in kickoff_flag and 'Kick Off' not in kickoff_flag2 and clock45_flag != '45:00':
						check_hash_sport = [True, "", ""]
					else:
						check_hash_sport = [False, "", ""]

				message_exp = check_hash_sport[1]
				message_stats = check_hash_sport[2]
				if message_exp != "":
					self.log.critical(message_exp)
				elif message_stats != "":
					self.log.info(message_stats)

			if check_hash_sport[0] is True:

				content_area = main.findAll('.ip-MobileViewController').at(0).toPlainText().strip()
				content_hash = util.hash(content_area)

				if self._content_hash == content_hash:
					self._check_hash_counter += 1
					self.log.info("{} sekundi nema promena na prozoru ".format(self._check_hash_counter))
					if self._check_hash_counter == common.window_not_active_limit[str(self._event_sport)]:
						self.log.critical("Resetujemo prozor, nije bilo promena do zadatog limita")
						self.reload_single_page()
				else:
					self._check_hash_counter = 0

				self._content_hash = content_hash

	################################################################################################################################################


	def match_statistics(self):

		# self.statistics.stop()
		print("ppppppppppppppppppppppppppppp")
		team_names = self.redis.smembers("team_names")
		print(len(team_names), "stefan 11111")
		print("ooooooooooooooooooooooooooooo")


		if len(team_names) == 0:
			QTimer().singleShot(30000, self.match_statistics)


		for team in team_names:

			matches = self.redis.hgetall(team)

			if len(matches) == 0 or team in ["", " ", None]:
				try:
					print(len(matches), "stefan 222222")
					self.redis.srem("team_names", team)
					continue
				except:
					print("Ne moze da uradi brisanje")
					continue
			print("LETS BEGIN")
			for i in matches:
				try:
					if self.redis.hget("processed", team) == i:
						print("OBRADJENOOOOOOOOOO", team, i)
						print("OBRADJENOOOOOOOOOO", team, i)
						print("OBRADJENOOOOOOOOOO", team, i)
						print("OBRADJENOOOOOOOOOO", team, i)
						print("OBRADJENOOOOOOOOOO", team, i)
						QTimer().singleShot(3000, self.parse_statistics)
						break
				except:
					print("OBRADJENOOOOOOOOOO", team, i)
					print("OBRADJENOOOOOOOOOO", team, i)
					print("OBRADJENOOOOOOOOOO", team, i)
					print("OBRADJENOOOOOOOOOO", team, i)
					print("OBRADJENOOOOOOOOOO", team, i)
					QTimer().singleShot(3000, self.parse_statistics)
					break

				self.redis.hset("processed", team, i)

				match = json.loads(matches[i])

				print("https://www.flashscore.com/match/{}/#match-summary".format(match['flashscore_id']))
				self._frame.load(QNetworkRequest(QUrl("https://www.flashscore.com/match/{}/#match-summary".format(match['flashscore_id']))))

				self.summary_click = True
				QTimer().singleShot(3000, self.parse_statistics)

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
					self.text_left = False
					self.text_right = False
					self.score = False
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

					if self.text_left not in [" ", "", None]:
						summary[self.period]["team1"] = team1

					if self.text_right not in [" ", "", None]:
						summary[self.period]["team2"] = team2

					if self.score not in [" ", "", None]:
						summary[self.period]["score"] = self.score

				main = self._frame.findFirstElement("#tab-statistics-0-statistic")
				rows = main.findAll('tr')

				for i in range(len(rows)):

					stats_name = rows.at(i).findAll('td').at(1).toPlainText().strip()
					stats_team1 = rows.at(i).findAll('td').at(0).toPlainText().strip()
					stats_team2 = rows.at(i).findAll('td').at(2).toPlainText().strip()

					statistics[stats_name] = {'team1': stats_team1, 'team2': stats_team2}

			except Exception as e:
				self.redis.hdel("processed", self.team)
				print("Puklo na STATISTICS", e)
				print("Puklo na SUMMARY", e)

			# https://www.flashscore.com/match/OnDFnJ4P/#match-summary
			print("0000000000000000000000000")
			print(summary)
			print()
			print(statistics)
			print("0000000000000000000000000")

			event = json.loads(self.redis.hget(self.team, self.i))

			self.redis.hset("@@"+self.team, self.i, json.dumps(event))

			event["statistics"] = statistics
			event["summary"] = summary

			self.redis.hset("!!"+self.team, self.i, json.dumps(event))

			self.redis.hdel(self.team, self.i)

			self.resourse_check()
			self.summary_click = True
			QTimer().singleShot(2000, self.match_statistics)
			print("TA TA TA TIRA")
			#dodaj statistiku u redis




	def resourse_check(self):

		print('!!!!!!!!!!!!!!!!!!!!!!iskorisceno memorije: %s (kb)   --    ' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
		if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss >= 600000:
			# self.log.info('RESET kolektora - iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			print('iskorisceno memorije: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
			self.reload_collector()
			print("Presao limit")
		print("BAZINGA")

	def reload_collector(self):
		pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
		for pid in pids:
			try:
				proces_name = str(open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()).replace('\\x00', ' ')
				if "collector_statistics" in proces_name and '/bin/sh' not in proces_name:
					relaunch_cmd = "python3 {}".format(proces_name[10:-2])
					subprocess.Popen(shlex.split(relaunch_cmd), stderr=None, stdout=None)
					sys.exit()
			except IOError:
				continue




if __name__ == "__main__":

	collector_log = util.parserLog('/var/log/sbp/flashscores/collector_statistics.log', 'flashscore-collector')
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

