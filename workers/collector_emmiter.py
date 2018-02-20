import datetime
import time
import redis
import json
import sys
sys.path.insert(0, '../')
import util
from config import redis_master_port, redis_pass, endpoint_rdb_ch_sets


rdb = redis.StrictRedis(host='localhost', port=redis_master_port, decode_responses=True, password=redis_pass)
diff_logger = util.parserLog('/var/log/sbp/flashscores/diff_logger.log', 'bet356live-single')
err_logger = util.parserLog('/var/log/sbp/flashscores/collector_emmiter.log', 'bet356live-collector-emmiter')

if __name__ == '__main__':

	print("Emmiter 2 started. - {}".format(datetime.datetime.now().time()))

	old = {}
	new_hashes = rdb.keys('coll_emmit_*')
	for key in new_hashes:
		rdb.delete(key)

	while True:

		old_hashes = list(old.keys())
		new_hashes = rdb.keys('coll_emmit_*')
		crunched = {}

		for _ in new_hashes:

			event_hash = _[11:]
			try:
				new_event = json.loads(rdb.get(_))[event_hash]
				old_event_key = event_hash

				if old_event_key in old_hashes:

					diff = {}
					min_for_emmit = {}
					old_event = old[old_event_key]

					for key in list(new_event.keys()):

						min_for_emmit[key] = new_event[key]
						if key not in list(old_event.keys()):
							diff[key] = new_event[key]
						else:
							if old_event[key] != new_event[key]:
								diff[key] = new_event[key]

					if len(list(diff.keys())):

						for key in list(min_for_emmit.keys()):
							diff[key] = min_for_emmit[key]
						crunched[event_hash] = diff
				else:

					crunched[event_hash] = new_event

				old[old_event_key] = new_event
			except Exception as err:
				print("err na kolektor emiteru")
				print(err)
				err_logger.critical(err)

		if len(list(crunched.keys())):
			for h_ in list(endpoint_rdb_ch_sets.keys()):
				rdb.lpush(endpoint_rdb_ch_sets[h_]['publish_ch'], json.dumps(crunched))
			diff_logger.info(crunched)

		time.sleep(15)
