import time
import datetime, dateutil
import sys
import re
from dateutil import parser

sys.path.insert(0, '../')
from lookup import games, sports
import util


class EventBase(object):
	'''
	online base event
	'''

	def __init__(self, team1=None, team2=None, *args, **kwargs):
		self.team1 = team1
		self.team2 = team2
		self.time = None
		self.league = None
		self.cache = {}
		self.current_score = "0:0"
		self.info_message = "0"

	def __eq__(self, other):
		return self.__dict__ == other.__dict__

	def __ne__(self, other):
		return self.__dict__ != other.__dict__

	def __str__(self):
		return str(self.__dict__)

	def deliver(self):
		if not self.team1 or not self.team2:
			return False

		content = {}
		for k in self.__dict__:
			if self.__dict__[k]:
				content[k] = self.__dict__[k]
		return content

	def setSport(self, sport):
		self.sport = sport

	def setLeagueGroup(self, league_group):
		self.league_group = league_group

	def setLeague(self, league):
		self.league = league

	def setSource(self, src):
		self.src = src

	def setStartTime(self, starttime):
		self.starttime = starttime

	def invalidScore(self, other):
		try:
			scores = other.current_score.split(":")
			if len(scores) == 2:
				return not (scores[0] and scores[1])
			return True
		except AttributeError:
			return True

	def setInitialOdds(self):
		pass

	def predict_finish(self, main=None, num_of_sets=None):
		pass

	def set_admin_message(self, info_message):
		pass
		self.info_message = info_message
		print("set_admin_message: {}".format(self.info_message))

	def check_score(self, ev_hash=None, rdb=None):
		return True

	def quota_resolve(self, sport, quota, multiplier_key, log):
		try:
			quota_multiplier = games.basic_qts[str(sports.sports[sport])]['quota_multiplier'][multiplier_key]
		except:
			log.critical("Puklo na mupltiplier key, setujemo 1, ici ce originalna kvota {}".format(sport))
			print("Puklo na mupltiplier key, setujemo 1, ici ce originalna kvota {}".format(sport))
			quota_multiplier = 1

		return util.convert_to_decimal(quota, quota_multiplier)


class Football(EventBase):
	'''
	livescore soccer event
	'''

	def __init__(self, team1=None, team2=None, log=None):
		super(Football, self).__init__(team1=team1, team2=team2, log=log)
		self.event_remove_time = 0
		global football_log
		football_log = log

	def setTime(self, event, event_hash, rdb=None):

		ev_time = None
		time = event.findAll('.col1').at(0).findAll('span').at(0).toPlainText().strip()

		ev_time = time.replace(".", "'")

		# print(ev_time)
		ht_marker = 'ht_marker_{}'.format(event_hash)
		if time.lower() not in ["half", "end"]:

			if time in ['0', " ", ""]:
				ev_time = '0'

			first_half_t1 = event.findAll('.col2').at(0).findAll(".desc1").at(0).toPlainText().strip().lower()
			first_half_t2 = event.findAll('.col4').at(0).findAll(".desc1").at(0).toPlainText().strip().lower()

			ht = rdb.get(ht_marker)
			if not ht:
				if first_half_t1 or first_half_t2 in ['first half']:
					second_ht = False
				else:
					rdb.set(ht_marker, True)
					second_ht = True
			else:
				second_ht = True

		elif time.lower() == "half":
			rdb.set(ht_marker, True)
			ev_time = "HT"
		elif time.lower() == "end":
			rdb.set(ht_marker, True)
			ev_time = "FT"

		self.time = str(ev_time)

	def setStartTime(self, starttime):
		self.starttime = starttime

	def setScore(self, event):
		score = None
		try:
			score = event.findAll(".col3").at(0).toPlainText().strip().split(":")

			res_1 = score[0]
			res_2 = score[1]

			if not len(res_1) or "'" in res_1:
				res_1 = 0
			if not len(res_2) or "'" in res_2:
				res_2 = 0

			score = "{}:{}".format(res_1, res_2)
		except Exception as e:
			f = '*' * 50
			football_log.critical('ERROR [13 - Set football score]: \n{}\n{}'.format(e, f))

		self.current_score = score

	def setOdds(self, event):

		qts = {}
		sport_lookup = games.basic_qts[str(sports.sports['Football'])]
		initial_odds = sport_lookup['initial_odds']
		# additional_keys = sport_lookup['additional_keys']

		qts.update(initial_odds)

		game_vars = sport_lookup['vars']
		for key in game_vars:
			if isinstance(game_vars[key], list):
				game_vars[key] = []
			else:
				game_vars[key] = None

		team1 = self.team1
		team2 = self.team2

		sum_score = 0
		try:
			score = self.current_score.split(":")
			sum_score = int(score[0]) + int(score[1])
		except Exception as e:
			f = '*' * 50
			football_log.critical('ERROR [14 - Football Set sum score]: \n{}\n{}'.format(e, f))

		quota_keys = ['LFT5', 'LTFT5', 'MTFT5', 'LFT4', 'LTFT4', 'MTFT4', 'LFT3', 'LTFT3', 'MTFT3', 'LFT2', 'LTFT2', 'MTFT2', 'LFT1', 'LTFT1', 'MTFT1', 'LHT1', 'MTHT1', 'LTHT1']
		for key in quota_keys:
			qts[key] = 0

		#Final
		qts['F1'] = event.findAll(".col5").at(0).findAll("span").at(0).toPlainText().strip()
		qts['FX'] = event.findAll(".col6").at(0).findAll("span").at(0).toPlainText().strip()
		qts['F2'] = event.findAll(".col7").at(0).findAll("span").at(0).toPlainText().strip()

		qts['FHT1'] = event.findAll(".col5").at(0).findAll("span").at(1).toPlainText().strip()
		qts['FHTX'] = event.findAll(".col6").at(0).findAll("span").at(1).toPlainText().strip()
		qts['FHT2'] = event.findAll(".col7").at(0).findAll("span").at(1).toPlainText().strip()

		#Rest od time
		qts['Z1'] = event.findAll(".col8").at(0).findAll("span").at(0).toPlainText().strip()
		qts['ZX'] = event.findAll(".col9").at(0).findAll("span").at(0).toPlainText().strip()
		qts['Z2'] = event.findAll(".col10").at(0).findAll("span").at(0).toPlainText().strip()

		#Double chance
		qts['DC1X'] = event.findAll(".col11").at(0).findAll("span").at(0).toPlainText().strip()
		qts['DC12'] = event.findAll(".col12").at(0).findAll("span").at(0).toPlainText().strip()
		qts['DCX2'] = event.findAll(".col13").at(0).findAll("span").at(0).toPlainText().strip()

		#Next goal
		qts['NG1'] = event.findAll(".col14").at(0).findAll("span").at(0).toPlainText().strip()
		qts['NGX'] = event.findAll(".col15").at(0).findAll("span").at(0).toPlainText().strip()
		qts['NG2'] = event.findAll(".col16").at(0).findAll("span").at(0).toPlainText().strip()

		#Limit Ft
		qts['LFT'] = event.findAll(".col17").at(0).findAll("span").at(0).toPlainText().strip()
		qts['MTFT'] = event.findAll(".col18").at(0).findAll("span").at(0).toPlainText().strip()
		qts['LTFT'] = event.findAll(".col19").at(0).findAll("span").at(0).toPlainText().strip()

		qts['LHT'] = event.findAll(".col17").at(0).findAll("span").at(1).toPlainText().strip()
		qts['MTHT'] = event.findAll(".col18").at(0).findAll("span").at(1).toPlainText().strip()
		qts['LTHT'] = event.findAll(".col19").at(0).findAll("span").at(1).toPlainText().strip()

		game_row = event.findAll(".left-border").at(0).findAll("tr") #Treba da pise left_border iako se nalazi na desnoj strani ?!?!?!?!

		for x in range(len(game_row)):
			odd_group_header = game_row.at(x).findAll(".sphead").at(0).toPlainText().strip()

			odd_group_bets = game_row.at(x).findAll(".specialoddstore").at(0)

			odd_group_tips = odd_group_bets.findAll('.tip')
			odd_group_limits = odd_group_bets.findAll('.oddinfo')
			odd_group_bets = odd_group_bets.findAll('.live-special')

			for nmb_bets in range(len(odd_group_tips)):
				odd_tip = odd_group_tips.at(nmb_bets).toPlainText().strip()
				odd_limit = odd_group_limits.at(0).toPlainText().strip()
				odd_bet = odd_group_bets.at(nmb_bets).findAll('span').at(1).toPlainText().strip()

				if re.search(r'draw no bet$', odd_group_header.lower()):
					qts['W{}'.format(odd_tip)] = odd_bet

				elif re.search(r'^both teams score$', odd_group_header.lower()):
					if odd_tip == 'Yes':
						qts["GG"] = odd_bet
					elif odd_tip == 'No':
						qts["NG"] = odd_bet

				elif re.search(r'^odd/even$', odd_group_header.lower()):
					qts[odd_tip.upper()] = odd_bet

				elif re.search(r'^home over/under$', odd_group_header.lower()):
					qts['LT1'] = odd_limit
					if odd_tip.lower() == 'over':
						qts['MTT1'] = odd_bet
					elif odd_tip.lower() == 'under':
						qts['LTT1'] = odd_bet

				elif re.search(r'^away over/under$', odd_group_header.lower()):
					qts['LT2'] = odd_limit
					if odd_tip.lower() == 'over':
						qts['MTT2'] = odd_bet
					elif odd_tip.lower() == 'under':
						qts['LTT2'] = odd_bet

				elif re.search(r'^goals home team$', odd_group_header.lower()):
					if str(odd_tip) == '0':
						qts["EXG1_0"] = odd_bet
					elif str(odd_tip) == '1':
						qts["EXG1_1"] = odd_bet
					elif str(odd_tip) == '2':
						qts["EXG1_2"] = odd_bet
					elif str(odd_tip) == '3+':
						qts["EXG1_3p"] = odd_bet

				elif re.search(r'^goals away team$', odd_group_header.lower()):
					if str(odd_tip) == '0':
						qts["EXG2_0"] = odd_bet
					elif str(odd_tip) == '1':
						qts["EXG2_1"] = odd_bet
					elif str(odd_tip) == '2':
						qts["EXG2_2"] = odd_bet
					elif str(odd_tip) == '3+':
						qts["EXG2_3p"] = odd_bet

				elif re.search(r'^handicap ', odd_group_header.lower()):
					handicap_res = odd_group_header.split("p ")[1]
					handicap = handicap_res.split(":")
					handicap = int(handicap[0]) - int(handicap[1])

					if str(handicap_res) not in game_vars['threewayhnd_ft_parsed']:
						game_vars['threewayhnd_ft_parsed'].append(str(handicap_res))
						game_vars['threewayhnd_ft_key'] = util.handicap_round_detect(
							game_vars['threewayhnd_ft_parsed'], 1)
						qts["H" + game_vars['threewayhnd_ft_key']] = float(handicap)

					if odd_tip == '1':
						qts["H{}1".format(game_vars['threewayhnd_ft_key'])] = odd_bet
					elif odd_tip == 'X':
						qts["H{}X".format(game_vars['threewayhnd_ft_key'])] = odd_bet
					elif odd_tip == '2':
						qts["H{}2".format(game_vars['threewayhnd_ft_key'])] = odd_bet

		for i in qts:
			if qts[i] in ["", " ", "^nbsp;"]:
				qts[i] = 0

		self.odds = qts

	def setOverTime(self, overtime):
		self.overtime = overtime
		if self.current_score:
			scores = self.current_score.split(":")
			if len(scores) == 2:
				s1 = int(scores[0]) - int(self.overtime[0])
				s2 = int(scores[1]) - int(self.overtime[1])
				self.current_score = '{}:{}'.format(s1, s2)

	def setHTScore(self, htscore):
		self.halftime_score = htscore

	def setRedCards(self, event):

		home_col_card_red = 0
		away_col_card_red = 0
		try:
			home_col_card_red = event.findAll(".col2").at(0).findAll(".card").at(0).toPlainText().strip()
		except:
			football_log.critical('ERROR [Nema statistike za crvene kartone vracamo 0]: \n{}'.format('*' * 50))
			print('ERROR [Nema statistike za crvene kartone vracamo 0]: \n{}'.format('*' * 50))

		try:
			away_col_card_red = event.findAll(".col4").at(0).findAll(".card").at(0).toPlainText().strip()
		except:
			football_log.critical('ERROR [Nema statistike za crvene kartone vracamo 0]: \n{}'.format('*' * 50))
			print('ERROR [Nema statistike za crvene kartone vracamo 0]: \n{}'.format('*' * 50))

		if not len(home_col_card_red) or "'" in home_col_card_red:
			home_col_card_red = 0
		if not len(away_col_card_red) or "'" in away_col_card_red:
			away_col_card_red = 0

		self.redcards = [home_col_card_red, away_col_card_red]

	def predict_finish(self, main=None, num_of_sets=None, event_hash=None):

		predicted_ft_data = {}
		for key in self.__dict__:
			predicted_ft_data[key] = self.__dict__[key]

		time = predicted_ft_data['time']
		if time != 'HT' and time != 'FT' and time != "None":
			time = int(time.split("'")[0])
			if time >= 90 and isinstance(time, int):
				print("setujem predikt. {} : {}  ****  {} /// {} {} --- {}".format(predicted_ft_data['team1'],
				                                                                   predicted_ft_data['team2'],
				                                                                   datetime.datetime.now().time(),
				                                                                   predicted_ft_data['sport'],
				                                                                   event_hash,
				                                                                   predicted_ft_data['time']))
				football_log.critical(
					"setujem predikt. {} : {} *** {} /// {} {} --- {}".format(predicted_ft_data['team1'],
					                                                          predicted_ft_data['team2'],
					                                                          datetime.datetime.now().time(),
					                                                          predicted_ft_data['sport'], event_hash,
					                                                          predicted_ft_data['time']))
				predicted_ft_data['time'] = 'FT'
				return predicted_ft_data


class Tennis(EventBase):
	'''
	tipico live event
	'''
	def __init__(self, team1=None, team2=None, log=None):
		super(Tennis, self).__init__(team1=team1, team2=team2, log=log)

		global tennis_log
		tennis_log = log

	def setPlayerOnServe(self, event):

		serve_1 = event.findAll(".col14").at(0).findAll("img").at(0).attribute("src")
		serve_2 = event.findAll(".col16").at(0).findAll("img").at(0).attribute("src")

		if len(serve_1):
			serve = 1
			# print("servira 1")
		elif len(serve_2):
			serve = 2
			# print("servira 2")
		else:
			serve = 0
			# print("servira 0")

		self.current_service = int(serve)

	def setTime(self, event, event_hash):

		ev_time = None

		ev_time_tennis = 0


		try:
			score = event.findAll(".col3").at(0).toPlainText().strip().split(":")
			score1 = score[0]
			score2 = score[1]
			score = int(score1) + int(score2) + 1
			ev_time_tennis = int(score)
		except Exception as e:
			f = '*' * 50
			tennis_log.critical('ERROR [12 - Tennis Time]: \n{}\n{}'.format(e, f))

		try:
			ft = event.findAll(".col1").at(0).toPlainText().strip()
			if ft.lower() == "end":
				ev_time = "FT"
		except Exception as e:
			f = '*' * 50
			tennis_log.critical('ERROR [12 - Tennis Time FT]: \n{}\n{}'.format(e, f))

		if ev_time_tennis == 1:
			ev_time = '1st'
		elif ev_time_tennis == 2:
			ev_time = '2nd'
		elif ev_time_tennis == 3:
			ev_time = '3rd'
		elif ev_time_tennis == 4:
			ev_time = '4th'
		elif ev_time_tennis == 5:
			ev_time = '5th'
		elif ev_time_tennis == 6:
			ev_time = '6th'

		self.time = ev_time

	def setCurrentSet(self, event):

		# odnos u gemovima tekuceg seta
		home, away = None, None
		try:
			score = event.findAll(".col15").at(0).toPlainText().strip().split(":")
			home = score[0]
			away = score[1]
		except Exception as e:
			f = '*' * 50
			tennis_log.critical('ERROR [12 - Tennis setCurrentSet]: \n{}\n{}'.format(e, f))

		self.current_set = "{}:{}".format(home, away)

	def setScore(self, event):
		score = None
		try:
			score = event.findAll(".col3").at(0).toPlainText().strip().split(":")
			home = score[0]
			away = score[1]

			score = "{}:{}".format(home, away)
		except Exception as e:
			f = '*' * 50
			tennis_log.critical('ERROR [12 - Tennis setScore]: \n{}\n{}'.format(e, f))

		self.current_score = score

	def setLiveDetails(self, event, redis, event_hash, ev_time, set_score, score):

		score_key = "score_details_{}".format(event_hash)

		set_index = ev_time[:1]
		redis.hset(score_key, "set_index", set_index)
		redis.hset(score_key, set_index, '{}'.format(set_score))
		redis.hset(score_key, "current_score", '{}'.format(score))

		live_result_details = "["
		for i in range(1, 6):
			none_current_score_set = redis.hget(score_key, i)
			if none_current_score_set is None:
				none_current_score_set = "0:0"
			live_result_details = live_result_details + '"{}", '.format(none_current_score_set)
		live_result_details = live_result_details[:-2] + "]"

		self.live_result_details = live_result_details

	def setOdds(self, event):

		qts = {}
		sport_lookup = games.basic_qts[str(sports.sports['Tennis'])]
		initial_odds = sport_lookup['initial_odds']
		# additional_keys = sport_lookup['additional_keys']

		qts.update(initial_odds)

		game_vars = sport_lookup['vars']
		for key in game_vars:
			if isinstance(game_vars[key], list):
				game_vars[key] = []
			else:
				game_vars[key] = None

		# team1 = self.team1
		# team2 = self.team2
		#
		# sum_score = 0
		# try:
		# 	score = self.current_score.split(":")
		# 	sum_score = int(score[0]) + int(score[1])
		# except Exception as e:
		# 	f = '*' * 50
		# 	football_log.critical('ERROR [14 - Tennis Set sum score]: \n{}\n{}'.format(e, f))

		# Final
		qts['TF1'] = event.findAll(".col5").at(0).findAll("span").at(0).toPlainText().strip()
		qts['TF2'] = event.findAll(".col7").at(0).findAll("span").at(0).toPlainText().strip()

		# Set result
		qts['TCS1'] = event.findAll(".col8").at(0).findAll("span").at(0).toPlainText().strip()
		qts['TCS2'] = event.findAll(".col9").at(0).findAll("span").at(0).toPlainText().strip()

		# Games in current set
		qts['LGIS_MD_INFO'] = event.findAll(".col11").at(0).findAll("span").at(0).toPlainText().strip() # Limit
		qts['LGIS_MD_P'] = event.findAll(".col12").at(0).findAll("span").at(0).toPlainText().strip() # Ovder
		qts['LGIS_MD_M'] = event.findAll(".col13").at(0).findAll("span").at(0).toPlainText().strip() # Under

		# Games on match
		qts['LGIM_MD_INFO'] = event.findAll(".col17").at(0).findAll("span").at(0).toPlainText().strip() # Limit
		qts['LGIM_MD_P'] = event.findAll(".col18").at(0).findAll("span").at(0).toPlainText().strip() # Ovder
		qts['LGIM_MD_M'] = event.findAll(".col19").at(0).findAll("span").at(0).toPlainText().strip() # Under


		# ZA DODATNE IGRE KOJE SE NALAZDE U EKSPANDIRAJUCEM MENIJU

		# game_row = event.findAll(".left-border").at(0).findAll("tr") #Treba da pise left_border iako se nalazi na desnoj strani ?!?!?!?!
		#
		# for x in range(len(game_row)):
		# 	odd_group_header = game_row.at(x).findAll(".sphead").at(0).toPlainText().strip()
		#
		# 	odd_group_bets = game_row.at(x).findAll(".specialoddstore").at(0)
		#
		# 	odd_group_tips = odd_group_bets.findAll('.tip')
		# 	odd_group_limits = odd_group_bets.findAll('.oddinfo')
		# 	odd_group_bets = odd_group_bets.findAll('.live-special')
		#
		# 	for nmb_bets in range(len(odd_group_tips)):
		# 		odd_tip = odd_group_tips.at(nmb_bets).toPlainText().strip()
		# 		odd_limit = odd_group_limits.at(0).toPlainText().strip()
		# 		odd_bet = odd_group_bets.at(nmb_bets).findAll('span').at(1).toPlainText().strip()
		#
		# 		if re.search(r'draw no bet$', odd_group_header.lower()):
		# 			qts['W{}'.format(odd_tip)] = odd_bet


		for i in qts:
			if qts[i] in ["", " ", "^nbsp;"]:
				qts[i] = 0

		self.odds = qts

	def validate_score(self, event=None, num_of_sets=None):

		return True
		num_of_sets = int(num_of_sets)
		score_board = event.findAll('.ml13-ScoreBoard').at(0).findAll('.ml13-ScoreBoardColumn')
		total_sets = len(score_board) - 2

		if num_of_sets == 2:
			if total_sets > 3:
				return None

		if num_of_sets == 3:
			if total_sets > 5:
				return None

		sets = score_board.at(0).findAll('.ml13-ScoreBoardColumn_Data')
		sets_result = [int(sets.at(0).toPlainText().strip()), int(sets.at(1).toPlainText().strip())]

		if sets_result[0] == num_of_sets or sets_result[1] == num_of_sets:
			return None

		winned_sets_home = 0
		winned_sets_away = 0
		for cntr in range(total_sets):
			set = score_board.at(cntr + 1).findAll('.ml13-ScoreBoardColumn_Data')
			home_res_in_set = int(set.at(0).toPlainText().strip())
			away_res_in_set = int(set.at(1).toPlainText().strip())
			if (home_res_in_set == 6 and home_res_in_set - away_res_in_set >= 2) or (home_res_in_set == 7 and home_res_in_set - away_res_in_set >= 1):
				winned_sets_home += 1
			elif (away_res_in_set == 6 and away_res_in_set - home_res_in_set >= 2) or (away_res_in_set == 7 and away_res_in_set - home_res_in_set >= 1):
				winned_sets_away += 1

		if winned_sets_home >= num_of_sets or winned_sets_away >= num_of_sets:
			return None

		if winned_sets_home != sets_result[0] or winned_sets_away != sets_result[1]:
			return None

		return True

	def predict_finish(self, event=None, current_score=None, current_set=None, num_of_sets=None, event_hash=None, rdb=None):

		predicted_ft_data = {}
		for key in self.__dict__:
			predicted_ft_data[key] = self.__dict__[key]

		score_split = current_score.split(":")
		set_split = current_set.split(":")

		time = event.findAll(".col1").at(0).toPlainText().strip().lower()

		predicted_ft_data = {}
		for key in self.__dict__:
			predicted_ft_data[key] = self.__dict__[key]

		if time == "end":
			predicted_ft_data['current_set'] = "{}:{}".format(set_split[0], set_split[1])
			predicted_ft_data['current_score'] = "{}:{}".format(score_split[0], score_split[1])
			predicted_ft_data['time'] = 'FT'

		score_split[0] = int(score_split[0])
		score_split[1] = int(score_split[1])
		set_split[0] = int(set_split[0])
		set_split[1] = int(set_split[1])

		if score_split[0] >= 1 and score_split[1] >= 1:
			if set_split[0] >= 5 and set_split[1] >= 5:
				predicted_ft_data['time'] = 'removed'

			elif set_split[0] >= 5 and set_split[0] - set_split[1] > 1:
				predicted_ft_data['current_set'] = "{}:{}".format(set_split[0] + 1, set_split[1])
				predicted_ft_data['current_score'] = "{}:{}".format(score_split[0] + 1, score_split[1])
				predicted_ft_data['time'] = 'FT'

			elif set_split[1] >= 5 and set_split[1] - set_split[0] > 1:
				predicted_ft_data['current_set'] = "{}:{}".format(set_split[0], set_split[1] + 1)
				predicted_ft_data['current_score'] = "{}:{}".format(score_split[0], score_split[1] + 1)
				predicted_ft_data['time'] = 'FT'

		if score_split[0] >= 1 and score_split[1] == 0:
			if set_split[0] >= 5 and set_split[0] - set_split[1] > 1:
				predicted_ft_data['current_set'] = "{}:{}".format(set_split[0] + 1, set_split[1])
				predicted_ft_data['current_score'] = "{}:{}".format(score_split[0] + 1, score_split[1])
				predicted_ft_data['time'] = 'FT'

		if score_split[1] >= 1 and score_split[0] == 0:
			if set_split[1] >= 5 and set_split[1] - set_split[0] > 1:
				predicted_ft_data['current_set'] = "{}:{}".format(set_split[0], set_split[1] + 1)
				predicted_ft_data['current_score'] = "{}:{}".format(score_split[0], score_split[1] + 1)
				predicted_ft_data['time'] = 'FT'

		return True


	@staticmethod
	def get_sets_to_win(competition_name):
		three_set_tournaments = ["Davis Cup", "Wimbledon", "US Open", "French Open", "Australian Open"]
		for tour_name in three_set_tournaments:
			if tour_name.lower() in competition_name.lower() and "women" not in competition_name.lower():
				return 3
		return 2
