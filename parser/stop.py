import signal
import os
from config import *
import common
import sys
sys.path.insert(0, '../')
import util
import redis

if hostname in common.master_servers and not util.check_local_dev():
	processes = ['starter', 'collector', 'enqueuer', 'defunct', 'emmiter', 'event_finisher', 'xvfb-run', 'inactive_single_process']
elif hostname in common.node_servers and not util.check_local_dev():
	processes = ['starter', 'single', 'defunct', 'xvfb-run']
else:
	processes = ['starter', 'collector', 'enqueuer', 'defunct', 'emmiter', 'event_finisher', 'xvfb-run', 'inactive_single_process', 'single']

pids = [pid for pid in os.listdir('/proc') if pid.isdigit()]
for pid in pids:
	try:
		tst = open(os.path.join('/proc', pid, 'cmdline'), 'rb').read()

		for filename in processes:
			if filename in str(tst) and "-platform" in str(tst):
				os.kill(int(pid), signal.SIGTERM)

	except IOError:  # proc has already terminated
		continue

sys.exit()
