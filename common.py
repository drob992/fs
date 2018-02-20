# UserAgent for web browser
uAgent = b"Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"

# Web Page reloading interval in miliseconds
liveReloadInterval = 1 * 1000
single2ExecCheckInterval = 1 * 500
check_signal_interval = 1 * 150

# setup dynamic logging
log_file_loc = '/var/log/sbp/'

live_link = 'https://www.flashscore.com/'

tip_bet_allowed_sports = [
	'Soccer',
	# 'Tennis',

	# 'Handball',
	# 'Volleyball',
	# 'Basketball',
	# 'Ice Hockey',

	# 'American Football',
	# 'Baseball',
	# 'Golf',
	# 'Water Polo',
	# 'Futsal',
	# 'Cricket',
	# 'Darts',
	# 'Rugby League',
	# 'Rugby Union',
	# 'Speedway',
]

window_not_active_limit = {
	'Football': 20,
	'Tennis': 120,
	'Basketball': 120,
	'Hockey': 180,
	'Handball': 120,
	'Volleyball': 120,
	'NFL': 120,
	'RugbyUnion': 120,

	'Futsal': 15,
	'Beach Volleyball': 15,
	'Table Tennis': 15,
	'Baseball': 120,
	'Golf': 15,
	'Horse Racing': 15,
	'Cricket': 15,
	'Darts': 15,
	'E Sports': 15,
	'Greyhounds': 15,
	'Rugby League': 15,
	'Speedway': 15,
}
delay_after_ft = 15
single_event_ttl = 1800
kickof_time_offset = 1


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
