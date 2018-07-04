# -*- coding: utf-8 -*-

import queries
import json
import sys
import redis
import datetime
import re

from parser.config import *


def team_strip(team):
	team_striped = re.subn(r'\([A-z]{3}\)', '', team)[0].strip()
	return team_striped


def score_parse(score):

	score = str(score).replace(" : ", ":")
	score = str(score).replace(" - ", ":")

	if "(" in score:
		score_split = score.split(" ")
		aet_score = score_split[0].split(":")
		ft_score = score_split[1].replace("(", "").replace(")", "").split(":")
		# event_score = "{}:{} ({}:{})".format(base_score[1], base_score[0], bracket_score[1], bracket_score[0])
		return {"t1_score": aet_score[0], "t2_score": aet_score[1], "t1_ft_score": ft_score[0], "t2_ft_score": ft_score[1]}
	else:
		score_split = score.split(":")
		# event_score = "{}:{}".format(score_split[1], score_split[0])
		return {"t1_score": score_split[0], "t2_score": score_split[1]}


def performance_parse(performance, score):

	performance = str(performance)

	# Ovde spada i Win i Loss i Draw i oni koji nemaju poslati performance
	if performance not in ["Draw/Win", "Draw/Loss", "Loss/Draw", "Win/Draw"]:
		if score["t1_score"] > score["t2_score"]:
			return {"t1_performance": "Win", "t2_performance": "Loss"}
		elif score["t1_score"] < score["t2_score"]:
			return {"t1_performance": "Loss", "t2_performance": "Win"}
		else:
			return {"t1_performance": "Draw", "t2_performance": "Draw"}

	elif performance == "Draw/Win" or performance == "Draw/Loss":
		if score["t1_score"] > score["t2_score"]:
			return {"t1_performance": "Draw/Win", "t2_performance": "Draw/Loss"}
		elif score["t1_score"] < score["t2_score"]:
			return {"t1_performance": "Draw/Loss", "t2_performance": "Draw/Win"}

	elif performance == "Loss/Draw" or performance == "Win/Draw":
		if score["t1_ft_score"] > score["t2_ft_score"]:
			return {"t1_performance": "Win/Draw", "t2_performance": "Loss/Draw"}
		elif score["t1_ft_score"] < score["t2_ft_score"]:
			return {"t1_performance": "Loss/Draw", "t2_performance": "Win/Draw"}


def insert_countries(country):
	try:
		country_id = queries.fetch("stats_countries", ["id"], 'name="%s"' % country)

		if not country_id:
			queries.save("stats_countries", {"name": country})
			# print("Success saving country " + country, "\n")

	except Exception as e:
		print("\nGRESKA - insert_countries - ",  e, "\n")
		return False

	return True


def insert_teams(country, team):
	try:
		try:
			id_country = queries.fetch("stats_countries", ["id"], 'name="%s"' % country)[0][0]
		except:
			insert_countries(country)
			id_country = queries.fetch("stats_countries", ["id"], 'name="%s"' % country)[0][0]

		team = team_strip(team)
		team_id = queries.fetch("stats_teams", ["id"], "name='{}' and id_country='{}'".format(team, id_country))

		if not team_id:
			queries.save("stats_teams", {"id_country": id_country, "name": team})
			# print("Success saving team " + team, "\n")

	except Exception as e:
		print("\nGRESKA - insert_teams - ",  e, country, team, "\n")
		return False

	return True


def insert_types(competition_type):
	try:
		competition_type_id = queries.fetch("stats_competition_types", ["id"], 'name="%s"' % competition_type)
		if not competition_type_id:
			queries.save("stats_competition_types", {"name": competition_type})
			# print("Success saving competition_type " + competition_type, "\n")

	except Exception as e:
		print("\nGRESKA - insert_types - ",  e, "\n")
		return False

	return True


def insert_competition_group(competition_group):
	try:
		competition_group_id = queries.fetch("stats_competition_groups", ["id"], 'name="%s"' % competition_group)
		if not competition_group_id:
			queries.save("stats_competition_groups", {"name": competition_group})
			# print("Success saving competition_group " + competition_group, "\n")

	except Exception as e:
		print("\nGRESKA - insert_competition_group - ",  e, "\n")
		return False

	return True


def insert_competition_organisers(competition_type, competition_organiser):
	try:
		id_competition_type = queries.fetch("stats_competition_types", ["id"], 'name="%s"' % competition_type)[0][0]

		competition_organiser_id = queries.fetch("stats_competition_organisers", ["id"], "name='{}' and id_competition_type='{}'".format(competition_organiser, id_competition_type))
		if not competition_organiser_id:
			queries.save("stats_competition_organisers", {"id_competition_type": id_competition_type, "name": competition_organiser})
			# print("Success saving competition_organiser " + competition_organiser, "\n")

	except Exception as e:
		print("\nGRESKA - insert_competition_organisers - ",  e, "\n")
		return False

	return True


def insert_competitions(competition_organiser, competition):
	try:
		id_competition_organiser = queries.fetch("stats_competition_organisers", ["id"], 'name="%s"' % competition_organiser)[0][0]

		competition_id = queries.fetch("stats_competitions", ["id"], "name='{}' and id_competition_organiser='{}'".format(competition, id_competition_organiser))
		if not competition_id:
			queries.save("stats_competitions", {"id_competition_organiser": id_competition_organiser, "name": competition})
			# print("Success saving competition " + competition, "\n")

	except Exception as e:
		print("\nGRESKA - insert_competitions - ",  e, "\n")
		return False

	return True


def insert_standings(standings):
	try:
		id_competition = queries.fetch("stats_competitions", ["id"], 'name="%s"' % standings['league_name'])[0][0]

		id_team = queries.fetch("stats_teams", ["id"], 'name="%s"' % team_strip(standings['team']))[0][0]

		data = {}
		data['id_competition'] = str(id_competition)
		data['id_team'] = str(id_team)

		data['win'] = str(standings['wins'])
		data['lost'] = str(standings['losses'])
		data['draw'] = str(standings['draws'])
		data['goals'] = str(standings['goals'])
		data['points'] = str(standings['points'])
		data['year'] = str(standings['year'])
		data['rank'] = str(standings['rank'])
		data['rank_title'] = str(standings['rank_title'].replace("'", " ")).encode('utf-8')
		data['rank_class'] = str(standings['rank_class'])
		league_group = str(standings['league_group'])

		id = queries.fetch("stats_standings", ["id"], "id_competition='{}' and id_team='{}' and year='{}' ".format(data['id_competition'],data['id_team'], data['year']))

		data['id_competition_group'] = queries.fetch("stats_competition_groups", ["id"], "name='{}'".format(league_group))[0][0]

		if id:
			queries.update("stats_standings", data, "id = '{}'".format(id[0][0]))
			# print("Success UPDATE standings - competition - team " + standings['league_name'] + " -- " + standings['team'], "")
		else:
			queries.save2_dq("stats_standings", data)
			# print("Success SAVING standings - competition - team " + standings['league_name'] + " -- " + standings['team'], "")

	except Exception as e:
		print("GRESKA - insert_standings - ",  e, "\n", data, "\n")
		return False

	return True


def insert_summary(data):
	try:
		data['first_half'] = data['1st Half']
		data['second_half'] = data['2nd Half']

		data.pop("1st Half", None)
		data.pop("2nd Half", None)
		
		summary={}
		for i in data:
			summary["{}".format(i.lower().replace(" ", "_"))] = json.dumps(data[i]).replace("'","")

		response = queries.save("stats_summary", summary)
		# print("Success saving summary " + str(summary), "\n")
		return response
	except Exception as e:
		print("\nGRESKA - summary - ",  e, "\n")
		return False


def insert_statistics(data):
	try:
		statistics={}
		for i in data:
			if i.lower().replace(" ","_") in ["yellow_cards", "red_cards", "ball_possession", "shots_on_goal", "shots_off_goal", "corner_kicks", "free_kicks", "fouls", "offsides"]:
				statistics["team1_{}".format(i.lower().replace(" ", "_"))] = data[i]["team1"].replace("%", "")
				statistics["team2_{}".format(i.lower().replace(" ", "_"))] = data[i]["team2"].replace("%", "")

		response = queries.save("stats_statistics", statistics)
		# print("Success saving statistics " + str(statistics), "\n")
		return response
	except Exception as e:
		print("\nGRESKA - statistics - ",  e, "\n")
		return False


def time_checker(time):
	if ":" and " " in time:
		time = time.split(" ")[0] + str(datetime.datetime.now().year)
	# elif str(datetime.datetime.now().year) not in time:
	elif len(str(time)) < 7:
		time = time + str(datetime.datetime.now().year)
	return time


def insert_events(info):
	data = {}
	try:
		id_competition = queries.fetch("stats_competitions", ["id"], 'name="%s"' % info['tournament_part'])[0][0]
		try:
			id_team1 = queries.fetch("stats_teams", ["id"], 'name="%s"' % info['home'])[0][0]
		except:
			insert_teams(info['country'], info['home'])
			id_team1 = queries.fetch("stats_teams", ["id"], 'name="%s"' % info['home'])[0][0]

		try:
			id_team2 = queries.fetch("stats_teams", ["id"], 'name="%s"' % info['away'])[0][0]
		except:
			insert_teams(info['country'], info['away'])
			id_team2 = queries.fetch("stats_teams", ["id"], 'name="%s"' % info['away'])[0][0]

		data['id_competition'] = int(id_competition)
		data['id_team1'] = int(id_team1)
		data['id_team2'] = int(id_team2)

		if info['score'] == "-":
			return True

		data['score'] = score_parse(info['score'])
		data['performance'] = performance_parse(info['win_lose'], data['score'])
		data['score'] = json.dumps(data['score'])
		data['performance'] = json.dumps(data['performance'])

		info['time'] = time_checker(info['time'])

		data['time_started'] = datetime.datetime.strptime(info['time'], "%d.%m.%Y")

		event = queries.fetch("stats_events", ["id"], "time_started='{}' and id_team1={} and id_team2={} and id_competition={}".format(data['time_started'],data['id_team1'],data['id_team2'], data['id_competition']))

		if not event:
			data['id_statistics'] = insert_statistics(info['statistics'])[0]
			data['id_summary'] = insert_summary(info['summary'])[0]

			if not data['id_statistics'] or not data['id_summary']:
				return False

			queries.save("stats_events", data)
			# print("Success saving event - time - teams " + str(data['time_started']) + " - " + str(data['id_team1']) + " - " + str(data['id_team2']), "\n")

	except Exception as e:
		print("\nGRESKA - insert_events - ",  e, info['home'], " *** ", info['away'], " *** ", info, " *** ", data, "\n")
		return False

	return True


def update_statistics(team1, team2, time, statistics_data):
	try:
		id_team1 = queries.fetch("stats_teams", ["id"], 'name="%s"' % team1)[0][0]
		id_team2 = queries.fetch("stats_teams", ["id"], 'name="%s"' % team2)[0][0]

		if ":" and " " in time:
			time = time.split(" ")[0]+str(datetime.datetime.now().year)
		time = datetime.datetime.strptime(time, "%Y-%m-%d")

		event = queries.fetch("stats_events", ["id"], "time_started='{}' and id_team1='{}' and id_team2='{}'".format(time, id_team1, id_team2))[0][0]

		statistics={}
		for i in statistics_data:
			if i.lower().replace(" ","_") in ["yellow_cards", "red_cards", "ball_possession", "shots_on_goal", "shots_off_goal", "corner_kicks", "free_kicks", "fouls", "offsides"]:
				statistics["team1_{}".format(i.lower().replace(" ", "_"))] = statistics_data[i]["team1"].replace("%", "")
				statistics["team2_{}".format(i.lower().replace(" ", "_"))] = statistics_data[i]["team2"].replace("%", "")

		queries.update("stats_statistics", statistics, "id = '{}'".format(event))
		# print("Success updating statistics " + str(statistics), "\n")

	except Exception as e:
		print("\nGRESKA - statistics update - ",  e, "\n")
		return False

	return True


def update_summary(team1, team2, time, summary_data):
	try:
		id_team1 = queries.fetch("teams", ["id"], 'name="%s"' % team_strip(team1))[0][0]
		id_team2 = queries.fetch("teams", ["id"], 'name="%s"' % team_strip(team2))[0][0]

		if ":" and " " in time:
			time = time.split(" ")[0]+str(datetime.datetime.now().year)
		time = datetime.datetime.strptime(time, "%Y-%m-%d")

		event_id = queries.fetch("stats_events", ["id"], "time_started='{}' and id_team1='{}' and id_team2='{}'".format(time, id_team1, id_team2))[0][0]

		summary={}
		for i in summary_data:
			summary["{}".format(i.lower().replace(" ", "_"))] = json.dumps(summary_data[i]).replace('"','\\"')

		queries.update("stats_summary", summary, "id = '{}'".format(event_id))
		# print("Success updating summary " + str(summary), "\n")

	except Exception as e:
		print("\nGRESKA - summary update - ",  e, "\n")
		return False

	return True


def update_event(old_data, new_data):
	try:

		old_data["home"] = team_strip(old_data["home"])
		old_data["away"] = team_strip(old_data["away"])
		new_data["home"] = team_strip(new_data["home"])
		new_data["away"] = team_strip(new_data["away"])

		id_competition = queries.fetch("stats_competitions", ["id"], 'name="%s"' % old_data['tournament_part'])[0][0]
		id_team1 = queries.fetch("stats_teams", ["id"], 'name="%s"' % team_strip(old_data["home"]))[0][0]
		id_team2 = queries.fetch("stats_teams", ["id"], 'name="%s"' % team_strip(old_data["away"]))[0][0]

		old_data['time'] = time_checker(old_data['time'])
		new_data['time'] = time_checker(new_data['time'])

		time = datetime.datetime.strptime(old_data['time'], "%d.%m.%Y")

		event = queries.fetch("stats_events", ["id"], "time_started='{}' and id_team1={} and id_team2={} and id_competition='{}'".format(old_data['time'], id_team1, id_team2, id_competition))

		time = str(time).split(" ")[0]
		if old_data['statistics']:
			update_statistics(team_strip(new_data['home']), new_data['away'], new_data['time'], new_data['statistics'])
		if old_data['summary']:
			update_summary(team_strip(new_data['home']), new_data['away'], new_data['time'], new_data['summary'])

		if event:
			queries.update("stats_events", new_data, "id = '{}'".format(event[0][0]))
			# print("Success updating event - time - teams " + str(time) + " - " + str(team_strip(old_data['home'])) + " - " + str(team_strip(old_data['away'])), "\n")
		else:
			pass
			print("Cant find Event to update")

	except Exception as e:
		print("\nGRESKA - event update - ",  e, "\n")
		return False

	return True



def team_countries():
	tc = rdb.smembers("teams_countries")
	for i in tc:
		tc_team, tc_country = i.split("@")
		tc_team = tc_team.replace("'", "\\'")

		check_country = insert_countries(tc_country)
		check_team = insert_teams(tc_country, tc_team)

		if check_country and check_team:
			rdb.srem("teams_countries", i)


def standings():
	standings = rdb.keys("standings@*")

	for standing in standings:

		standing_row = rdb.hgetall(standing)

		standing_split = standing.split("@")

		country = standing_split[2]

		# print("\n", standing, "\n")
		for competition in standing_row:
			try:
				competition_event = eval(standing_row[competition])

				competition_event['league_name'] = competition_event['league_name'].replace("'", "\\'")

				# TODO: U liniji ispod stoji zakucan sport(competition organiser), potrebno slati to sa parsera
				check_c_organiser = insert_competition_organisers("Football", country)
				check_competition = insert_competitions(country, competition_event['league_name'])
				check_competition_group = insert_competition_group(competition_event['league_group'])

				# ISPARSIRAJ PRVO SVE TIMOVE KOJI POSTOJE, NJIH UBACI, PA ONDA PARSIRAJ EVENTE I STATISTIKE
				# insert_teams(competition_event["country"], team_strip(competition_event['team'].replace("'", "\\'")))

				check_standing = insert_standings(competition_event)
			except Exception as e:
				check_standing = check_competition = check_competition_group = check_c_organiser = False
				print("Puklo standing", e, standing_row[competition])

			if check_standing and check_competition and check_competition_group and check_c_organiser:
				rdb.hdel(standing, competition)

		# sys.exit()

def events():

	teams = rdb.keys("new-*")
	for team in teams:
		team_data = rdb.hgetall(team)

		# current_team = team.replace('new-', '')
		# print(current_team)
		for i in team_data:
			data = json.loads(team_data[i])
			data['home'] = team_strip(data['home'].replace("'", "\\'"))
			data['away'] = team_strip(data['away'].replace("'", "\\'"))
			if "'" in data['tournament_part']:
				data['tournament_part'] = data['tournament_part'].replace("'", "\\'")

			competition_type = data['sport']

			competition = data['tournament_part']

			competition_organiser = data['country_part'].replace(":", "").title()

			check_type = insert_types(competition_type)
			check_c_organiser = insert_competition_organisers(competition_type, competition_organiser)
			check_competitions = insert_competitions(competition_organiser, competition)
			# print(team)
			# print(team_data)
			# print(i)
			# print(data['statistics'])
			# print(data['summary'])
			check_event = insert_events(data)

			if check_type and check_c_organiser and check_competitions and check_event:
				rdb.hdel(team, i)
			# else:
			# 	print("\n\nqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq\n\n")

			# check_upd_event = update_event(data['home'], data['away'], data['time'], data)

			# sys.exit()


if __name__ == '__main__':
	rdb = redis.StrictRedis(host='localhost', port=6668, decode_responses=True, password=redis_pass)

	team_countries()
	print("Done - teams and countries.")
	standings()
	print("Done - standings.")
	events()
	print("Done - events.")

