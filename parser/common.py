# UserAgent for web browser
import random

uAgent = b"Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"

# Web Page reloading interval in miliseconds
liveReloadInterval = 1 * 1000
single2ExecCheckInterval = 1 * 500
check_signal_interval = 1 * 150

# setup dynamic logging
log_file_loc = '/var/log/sbp/'

live_link = "https://www.flashscore.com/"


statistics_num = 7

europe = ["England"]
# europe = ["France", "England", "Germany", "Spain"]
# europe = ["France", "England", "Germany", "Spain", "Turkey", "Italy", "Portugal", "Belgium", "Hungary", "Russia", "Iceland", "Northern Ireland", "Ireland", "Czech Republic", "Albania", "Romania", "Wales", "Slovakia", "Ukraine", "Croatia", "Sweden", "Austria", "Poland"]

master_servers = ["master", "stefan-desktop", "www-desktop"]
node_servers = ["premier", "parser2", "igor-desktop", "www-desktop"]


available_commands = {
	'system': ['start', 'resend', 'forced'],
	'event': ['open', 'reload', 'kill'],
	'tools': ['list_rm', 'list_rm_detailed', 'tennis_tb', 'football_ht', 'full_log']
}

max_opened_events = 200
redis_channels = {
	'commands': 'commands',
	'finished_events': 'finished_events',
	'available_events': 'available_events',
	'selected_events': 'active_events',
	'flush_data': 'flush_data',
	'flush_collector_data': 'flush_collector_data',
	'singles_stop': 'do_not_emmit'
}

def generate_cookie():
	chars = ['A', 'B', 'C', 'D', 'E', 'F', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
	pstk = ""
	for i in range(32):
		pstk += str(random.choice(chars))
	pstk += '000003'
	cookie = bytearray("pstk={}; session=processform=0; aps03=lng=1&tzi=1&ct=240&cst=0&cg=0&oty=1".format(pstk), 'utf-8')
	return cookie

