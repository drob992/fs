import queries
import json
import sys
import redis
import datetime

from parser.config import *


def insert_countries(country):
	try:
		country_id = queries.fetch("countries", ["id"], "name='%s'" % country)

		if not country_id:
			queries.save("countries", {"name": country})
			print("Success saving country " + country, "\n")
		else:
			pass
			# print("Country alewady exists")

	except Exception as e:
		print("\nGRESKA - insert_countries - ",  e, "\n")


def insert_teams(country, team):
	try:
		id_country = queries.fetch("countries", ["id"], "name='%s'" % country)[0][0]

		team_id = queries.fetch("teams", ["id"], "name='{}' and id_country='{}'".format(team, id_country))

		if not team_id:
			queries.save("teams", {"id_country": id_country, "name": team})
			print("Success saving team " + team, "\n")
		else:
			pass
			# print("Team alewady exists")


	except Exception as e:
		print("\nGRESKA - insert_teams - ",  e, country, team, "\n")


def insert_types(competition_type):
	try:
		competition_type_id = queries.fetch("competition_types", ["id"], "name='%s'" % competition_type)

		if not competition_type_id:
			queries.save("competition_types", {"name": competition_type})
			print("Success saving competition_type " + competition_type, "\n")
		else:
			pass
			# print("Competition type alewady exists")

	except Exception as e:
		print("\nGRESKA - insert_types - ",  e, "\n")


def insert_competition_organisers(competition_type, competition_organiser):
	try:
		id_competition_type = queries.fetch("competition_types", ["id"], "name='%s'" % competition_type)[0][0]

		competition_organiser_id = queries.fetch("competition_organisers", ["id"], "name='{}' and id_competition_type='{}'".format(competition_organiser, id_competition_type))

		if not competition_organiser_id:
			queries.save("competition_organisers", {"id_competition_type": id_competition_type, "name": competition_organiser})
			print("Success saving competition_organiser " + competition_organiser, "\n")
		else:
			pass
			# print("competition_organiser alewady exists")

	except Exception as e:
		print("\nGRESKA - insert_competition_organisers - ",  e, "\n")


def insert_competitions(competition_organiser, competition):
	try:
		id_competition_organiser = queries.fetch("competition_organisers", ["id"], "name='%s'" % competition_organiser)[0][0]

		competition_id = queries.fetch("competitions", ["id"], "name='{}' and id_competition_organiser='{}'".format(competition, id_competition_organiser))

		if not competition_id:
			queries.save("competitions", {"id_competition_organiser": id_competition_organiser, "name": competition})
			print("Success saving competition " + competition, "\n")
		else:
			pass
			# print("competition alewady exists")

	except Exception as e:
		print("\nGRESKA - insert_competitions - ",  e, "\n")


def insert_standings(standings):
	try:
		id_competition = queries.fetch("competitions", ["id"], "name='%s'" % standings['league_name'])[0][0]
		id_team = queries.fetch("teams", ["id"], "name='%s'" % standings['team'])[0][0]

		data = {}

		data['id_competition'] = str(id_competition)
		data['id_team'] = str(id_team)

		data['win'] = str(standings['wins'])
		data['lost'] = str(standings['losses'])
		data['draw'] = str(standings['draws'])
		data['goals'] = str(standings['goals'])
		data['points'] = str(standings['points'])
		data['year'] = str(standings['year'])

		id = queries.fetch("standings", ["id"], "id_competition='{}' and id_team='{}' and year='{}' ".format(data['id_competition'],data['id_team'], data['year']))

		if id:
			queries.update("standings", data, "id = '{}'".format(id[0][0]))
			print("Success update standings - competition - team " + standings['league_name'] + standings['team'], "\n")
		else:
			queries.save("standings", data)
			print("Success saving standings - competition - team " + standings['league_name'] + standings['team'], "\n")

	except Exception as e:
		print("GRESKA - insert_standings - ",  e, "\n")


def insert_summary(data):
	try:
		summary={}
		for i in data:
			summary["{}".format(i.lower().replace(" ", "_"))] = json.dumps(data[i]).replace('"','\\"')

		response = queries.save("summary", summary)
		print("Success saving summary " + str(summary), "\n")
		return response
	except Exception as e:
		print("\nGRESKA - summary - ",  e, "\n")


def insert_statistics(data):
	try:
		statistics={}
		for i in data:
			if i.lower().replace(" ","_") in ["yellow_cards", "red_cards", "ball_possession", "shots_on_goal", "shots_off_goal", "corner_kicks", "free_kicks", "fouls", "offsides"]:
				statistics["team1_{}".format(i.lower().replace(" ", "_"))] = data[i]["team1"].replace("%", "")
				statistics["team2_{}".format(i.lower().replace(" ", "_"))] = data[i]["team2"].replace("%", "")

		response = queries.save("statistics", statistics)
		print("Success saving statistics " + str(statistics), "\n")
		return response
	except Exception as e:
		print("\nGRESKA - statistics - ",  e, "\n")


def insert_events(info):
	data = {}
	try:
		id_competition = queries.fetch("competitions", ["id"], "name='%s'" % info['tournament_part'])[0][0]
		id_team1 = queries.fetch("teams", ["id"], "name='%s'" % info['home'])[0][0]
		id_team2 = queries.fetch("teams", ["id"], "name='%s'" % info['away'])[0][0]

		data['id_competition'] = int(id_competition)
		data['id_team1'] = int(id_team1)
		data['id_team2'] = int(id_team2)

		data['score'] = str(info['score']).replace(" : ", ":")

		if ":" and " " in info["time"]:
			info['time'] = info['time'].split(" ")[0]+str(datetime.datetime.now().year)

		data['time_started'] = datetime.datetime.strptime(info['time'], "%d.%m.%Y")

		event = queries.fetch("events", ["id"], "time_started='{}' and id_team1={} and id_team2={} and id_competition={}".format(data['time_started'],data['id_team1'],data['id_team2'], data['id_competition']))

		if not event:
			data['id_statistics'] = insert_statistics(info['statistics'])[0]
			data['id_summary'] = insert_summary(info['summary'])[0]

			queries.save("events", data)
			print("Success saving event - time - teams " + str(data['time_started']) + " - " + str(data['id_team1']) + " - " + str(data['id_team2']), "\n")
		else:
			pass
			print("@@@@@@@Event already exists - time - teams " + str(data['time_started']) + " - " + str(data['id_team1']) + " - " + str(data['id_team2']), "\n")
	except Exception as e:
		print("\nGRESKA - insert_events - ",  e, info['home'],info['away'],data, "\n")


def update_statistics(team1, team2, time, statistics_data):
	try:
		id_team1 = queries.fetch("teams", ["id"], "name='%s'" % team1)[0][0]
		id_team2 = queries.fetch("teams", ["id"], "name='%s'" % team2)[0][0]

		if ":" and " " in time:
			time = time.split(" ")[0]+str(datetime.datetime.now().year)
		time = datetime.datetime.strptime(time, "%Y-%m-%d")

		event = queries.fetch("events", ["id"], "time_started='{}' and id_team1='{}' and id_team2='{}'".format(time, id_team1, id_team2))[0][0]

		statistics={}
		for i in statistics_data:
			if i.lower().replace(" ","_") in ["yellow_cards", "red_cards", "ball_possession", "shots_on_goal", "shots_off_goal", "corner_kicks", "free_kicks", "fouls", "offsides"]:
				statistics["team1_{}".format(i.lower().replace(" ", "_"))] = statistics_data[i]["team1"].replace("%", "")
				statistics["team2_{}".format(i.lower().replace(" ", "_"))] = statistics_data[i]["team2"].replace("%", "")

		queries.update("statistics", statistics, "id = '{}'".format(event))
		print("Success updating statistics " + str(statistics), "\n")

	except Exception as e:
		print("\nGRESKA - statistics update - ",  e, "\n")


def update_summary(team1, team2, time, summary_data):
	try:
		id_team1 = queries.fetch("teams", ["id"], "name='%s'" % team1)[0][0]
		id_team2 = queries.fetch("teams", ["id"], "name='%s'" % team2)[0][0]

		if ":" and " " in time:
			time = time.split(" ")[0]+str(datetime.datetime.now().year)
		time = datetime.datetime.strptime(time, "%Y-%m-%d")

		event_id = queries.fetch("events", ["id"], "time_started='{}' and id_team1='{}' and id_team2='{}'".format(time, id_team1, id_team2))[0][0]

		summary={}
		for i in summary_data:
			summary["{}".format(i.lower().replace(" ", "_"))] = json.dumps(summary_data[i]).replace('"','\\"')

		queries.update("summary", summary, "id = '{}'".format(event_id))
		print("Success updating summary " + str(summary), "\n")

	except Exception as e:
		print("\nGRESKA - summary update - ",  e, "\n")


def update_event(old_data, new_data):
	try:
		id_competition = queries.fetch("competitions", ["id"], "name='%s'" % old_data['tournament_part'])[0][0]
		id_team1 = queries.fetch("teams", ["id"], "name='%s'" % old_data["home"])[0][0]
		id_team2 = queries.fetch("teams", ["id"], "name='%s'" % old_data["away"])[0][0]

		if ":" and " " in old_data['time']:
			old_data['time'] = old_data['time'].split(" ")[0]+str(datetime.datetime.now().year)

		time = datetime.datetime.strptime(old_data['time'], "%d.%m.%Y")

		event = queries.fetch("events", ["id"], "time_started='{}' and id_team1={} and id_team2={} and id_competition='{}'".format(old_data['time'], id_team1, id_team2, id_competition))

		time = str(time).split(" ")[0]
		if data['statistics']:
			update_statistics(old_data['home'], old_data['away'], old_data['time'], old_data['statistics'])
		if data['summary']:
			update_summary(old_data['home'], old_data['away'], old_data['time'], old_data['summary'])

		if event:
			queries.update("events", new_data, "id = '{}'".format(event[0][0]))
			print("Success updating event - time - teams " + str(time) + " - " + str(old_data['home']) + " - " + str(old_data['away']), "\n")
		else:
			pass
			print("Cant find Event to update")

	except Exception as e:
		print("\nGRESKA - event update - ",  e, "\n")


if __name__ == '__main__':
	rdb = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)

	tc = rdb.smembers("teams_countries")
	print(len(tc))
	br = 1
	for i in tc:
		print(br)
		tc_team, tc_country = i.split("@")
		tc_team = tc_team.replace("'", "\\'")

		insert_countries(tc_country)

		insert_teams(tc_country, tc_team)
		br += 1
	teams = rdb.keys("new-*")

	# for team in teams:
	# 	team_data = rdb.hgetall(team)
	#
	# 	current_team = team.replace('new-', '')
	# 	# print(current_team)
	#
	# 	for i in team_data:
	# 		data = json.loads(team_data[i])
	# 		data['home'] = data['home'].replace("'", "\\'")
	# 		data['away'] = data['away'].replace("'", "\\'")
	# 		# print(json.dumps(data, indent=4))
	#
	# 		competition_type = data['sport']
	#
	# 		country = data['country']
	#
	# 		team1 = data['home']
	# 		team2 = data['away']
	#
	# 		time = data['time']
	#
	# 		score = data['score'].replace(" ", "")
	#
	# 		competition = data['tournament_part'].replace("'", "\\'")
	#
	# 		competition_organiser = data['country_part'].replace(":", "").title()
	#
	# 		summary = data['summary']
	# 		statistics = data['statistics']
	#
	# 		# Insert ------ !!!!!!!
	# 		# insert_countries(country)
	#
	# 		insert_types(competition_type)
	# 		insert_competition_organisers(competition_type, competition_organiser)
	# 		insert_competitions(competition_organiser, competition)
	#
	# 		# ISPARSIRAJ PRVO SVE TIMOVE KOJI POSTOJE, NJIH UBACI, PA ONDA PARSIRAJ EVENTE I STATISTIKE
	# 		# insert_teams(country, team1)
	# 		# insert_teams(country, team2)
	#
	# 		insert_events(data)
	#
	# 		# update_statistics(data['home'], data['away'], data['time'], data['statistics'])
	#
	# 		# update_summary(data['home'], data['away'], data['time'], data['summary'])
	#
	# 		# update_event(data['home'], data['away'], data['time'], data)
	#
	# 		# sys.exit()
	# 		# ***************************
	#
	# 		# print("*" * 25)
	# 		# print("Country: " + country)
	# 		# print("*" * 25)
	# 		# print("Team1: " + team1)
	# 		# print("Team2: " + team2)
	# 		# print("*" * 25)
	# 		# print("Score: " + score)
	# 		# print("*" * 25)
	# 		# print("Time: " + time)
	# 		# print("*" * 25)
	# 		# print("Competition: " + competition)
	# 		# print("*" * 25)
	# 		# print("CompetitionOrganiser: " + competition_organiser)
	# 		# print("*" * 25)
	# 		# print("Summary: " + summary)
	# 		# print(summary)
	# 		# print("*" * 25)
	# 		# print("Statistics: " + statistics)
	# 		# print("*" * 25)
	# 		# sys.exit()
	#
	# standings = rdb.keys("standings-*")
	# for standing in standings:
	#
	# 	standing = rdb.hgetall(standing)
	# 	for competition in standing:
	# 		try:
	# 			competition = competition.replace("'", "\\'")
	# 			competition = json.loads(standing[competition].replace("'", '"'))
	#
	# 			insert_competitions(competition['country'], competition['league_name'])
	#
	# 			# ISPARSIRAJ PRVO SVE TIMOVE KOJI POSTOJE, NJIH UBACI, PA ONDA PARSIRAJ EVENTE I STATISTIKE
	# 			# insert_teams(competition["country"], competition['team'].replace("'", "\\'"))
	#
	# 			insert_standings(competition)
	# 		except Exception as e:
	# 			print("Puklo standing", e, competition)

	# sys.exit()