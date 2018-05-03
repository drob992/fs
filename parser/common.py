# UserAgent for web browser
uAgent = b"Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"

# Web Page reloading interval in miliseconds
liveReloadInterval = 1 * 1000
single2ExecCheckInterval = 1 * 500
check_signal_interval = 1 * 150

# setup dynamic logging
log_file_loc = '/var/log/sbp/'

live_link = 'https://www.flashscore.com/'


statistics_num = 5

europe = ["France", "England", "England", "Germany", "Spain", "Turkey", "Italy", "Portugal", "Belgium", "Hungary", "Russia", "Iceland", "Northern Ireland", "Ireland", "Czech Republic", "Albania", "Romania", "Wales", "Slovakia", "Ukraine", "Croatia", "Sweden", "Austria", "Poland"]

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
