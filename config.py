# -*- coding: utf-8 -*-
import socket

hostname = socket.gethostname()

project_root_path = '/home/stex92/work/flashscores/'
if hostname == "www-desktop":
    redis_master_host = '192.168.1.5'
elif hostname == "www-desktop":
    redis_master_host = '192.168.1.5'
else:
    redis_master_host = 'localhost'


redis_admin_host = 'localhost'
redis_master_port = 6666
redis_admin_port = 3108
redis_pass = 'pr3mi3r'

endpoint_rdb_ch_sets = {
    'localhost': {
        'publish_ch': 'bet365_feed_local',
        'endpoint': 'http://{}/svclive/events/bet365/feed'.format(redis_admin_host),
        'hide_quotas_api': 'http://admin.sbp.dev/svclive/event/set_enable_for_betting'
    },
    #'staging': {
    #    'publish_ch': 'bet365_feed_stg',
    #    'endpoint': 'http://stg.premierbet.me/svclive/events/bet365/feed',
    #    'hide_quotas_api': 'http://stg.premierbet.me/svclive/event/set_enable_for_betting'
    #}
}

admin_redis_ch = 'bet365_comm_ch'

nodes = [
	{
		'type': 'node',
		'id': 'www-desktop',
		'ip': '192.168.1.5',
		'r_channels': {
			'commands': 'commands',
			'selected_events': 'active_events',
			'event_count': 'event_count'
		}
	}
]