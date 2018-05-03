# -*- coding: utf-8 -*-
import socket

hostname = socket.gethostname()

project_root_path = '/home/www/work/flashscore/'

redis_master_host = 'master'


redis_admin_host = 'localhost'
redis_master_port = 6668
redis_admin_port = 3108
redis_pass = 'pr3mi3r'

endpoint_rdb_ch_sets = {
    'localhost': {
        'publish_ch': 'bet365_feed_local',
        'endpoint': 'http://{}/svclive/events/bet365/feed'.format(redis_admin_host),
        'hide_quotas_api': 'http://admin.sbp.dev/svclive/event/set_enable_for_betting'
    }
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