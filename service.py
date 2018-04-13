import queries
import json
import sys
import redis
import datetime

from parser.config import *
import parser.common


def insert_countries(country):
	try:
		queries.save("countries", {"name": country})
		print("Success saving country " + country)
	except Exception as e:
		print("GRESKA - insert_countries - ",  e, "\n")

def insert_teams(country, team):
	try:
		id_country = queries.fetch("countries", ["id"], "name='%s'" % country)

		queries.save("teams", {"id_country": id_country[0], "name": team})

		print("Success saving team " + team)
	except Exception as e:
		print("GRESKA - insert_teams - ",  e, "\n")

def insert_types(competition_type):
	try:
		queries.save("competition_types", {"name": competition_type})
		print("Success saving competition_type " + competition_type)
	except Exception as e:
		print("GRESKA - insert_types - ",  e, "\n")

def insert_competition_organisers(competition_type, competition_organiser):
	try:
		id_competition_type = queries.fetch("competition_types", ["id"], "name='%s'" % competition_type)

		queries.save("competition_organisers", {"id_competition_type": id_competition_type[0], "name": competition_organiser})

		print("Success saving competition_organiser " + competition_organiser)
	except Exception as e:
		print("GRESKA - insert_competition_organisers - ",  e, "\n")

def insert_competitions(competition_organiser, competition):
	try:
		id_competition_organiser = queries.fetch("competition_organisers", ["id"], "name='%s'" % competition_organiser)

		queries.save("competitions", {"id_competition_organiser": id_competition_organiser[0], "name": competition})

		print("Success saving competition " + competition)
	except Exception as e:
		print("GRESKA - insert_competitions - ",  e, "\n")


def insert_standings(standings):
	try:
		id_competition = queries.fetch("competitions", ["id"], "name='%s'" % standings['league_name'])[0]
		id_team = queries.fetch("teams", ["id"], "name='%s'" % standings['team'])[0]

		data = {}

		data['id_competition'] = str(id_competition)
		data['id_team'] = str(id_team)

		data['win'] = str(standings['wins'])
		data['lost'] = str(standings['losses'])
		data['draw'] = str(standings['draws'])
		data['goals'] = str(standings['goals'])
		data['points'] = str(standings['points'])
		data['year'] = str(standings['year'])

		queries.save("standings", data)
		print("Success saving standings - competition - team " + standings['league_name'] + standings['team'])
	except Exception as e:
		print("GRESKA - insert_standings - ",  e, "\n")


def insert_events(info):
	try:
		id_competition = queries.fetch("competitions", ["id"], "name='%s'" % info['tournament_part'])[0]
		id_team1 = queries.fetch("teams", ["id"], "name='%s'" % info['home'])[0]
		id_team2 = queries.fetch("teams", ["id"], "name='%s'" % info['away'])[0]

		data = {}

		data['id_competition'] = str(id_competition)
		data['id_team1'] = str(id_team1)
		data['id_team2'] = str(id_team2)

		data['score'] = str(info['score'])

		print(info['time'])
		if ":" and " " in info["time"]:
			info['time'] = info['time'].split(" ")[0]+str(datetime.datetime.now().year)

		# TODO: SREDITI VREME
		data['time_started'] = datetime.datetime.strptime(info['time'], "%d-%m-%Y").strftime('%d-%m-%Y')

		# TODO: URADITI STATISTIKU I SUMMARY
		data['summary'] = "0"
		data['statistics'] = "0"

		queries.save("standings", data)
		print("Success saving standings - competition - team " + standings['league_name'] + standings['team'])
	except Exception as e:
		print("GRESKA - insert_events - ",  e, "\n")





rdb = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)

standings = rdb.keys("standings-*")
for standing in standings:
	standing = rdb.hgetall(standing)
	for competition in standing:
		competition = json.loads(standing[competition].replace("'", '"'))

		insert_competitions(competition['country'], competition['league_name'])

		insert_teams(competition["country"], competition['team'])

		insert_standings(competition)



teams = rdb.keys("new-*")

for team in teams:
	team_data = rdb.hgetall(team)

	current_team = team.replace('new-', '')
	print(current_team)

	for i in team_data:
		data = json.loads(team_data[i])

		print(json.dumps(data, indent=4))

		competition_type = data['sport']

		country = data['country']

		team1 = data['home']
		team2 = data['away']

		time = data['time']

		score = data['score'].replace(" ", "")

		competition = data['tournament_part']

		competition_organiser = data['country_part'].replace(":","").title()

		summary = data['summary']
		statistics = data['statistics']


		# Insert ------ !!!!!!!
		insert_countries(country)

		insert_types(competition_type)
		insert_competition_organisers(competition_type, competition_organiser)
		insert_competitions(competition_organiser, competition)

		insert_teams(country, team1)
		insert_teams(country, team2)

		# insert_statistics(data)
		# insert_summary(data)
		print("11111111111111111111111111111111111111111111111111111111111111111111111111111")
		insert_events(data)

		# ***************************

		print("*" * 25)
		print("Country: " + country)
		print("*" * 25)
		print("Team1: " + team1)
		print("Team2: " + team2)
		print("*" * 25)
		print("Score: " + score)
		print("*" * 25)
		print("Time: " + time)
		print("*" * 25)
		print("Competition: " + competition)
		print("*" * 25)
		print("CompetitionOrganiser: " + competition_organiser)
		print("*" * 25)
		# print("Summary: " + summary)
		# print("*" * 25)
		# print("Statistics: " + statistics)
		# print("*" * 25)
	sys.exit()