# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '../')
import util
import config
import common

if __name__ == '__main__':

	endpoint_name = sys.argv[-3]
	endpoint = sys.argv[-2]
	redis_ch = sys.argv[-1]

	if config.hostname in common.master_servers or util.check_local_dev():
		util.sync(endpoint=endpoint, redis_ch=redis_ch, endpoint_name=endpoint_name)
	else:
		sys.exit('Unknown host {}'.format(config.hostname))
