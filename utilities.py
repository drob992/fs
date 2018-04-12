import MySQLdb

_DB_HOST = 'localhost'
_DB_USERNAME = 'sbp'
_DB_PASSWORD = 'pr3mi3r'
_DB_USE_UNICODE = False
_DB_CHARSET = 'utf8'

__mysql = None
def get_mysql_db(db_name, host=_DB_HOST, user=_DB_USERNAME, passwd=_DB_PASSWORD, use_unicode=_DB_USE_UNICODE, charset=_DB_CHARSET):
	global __mysql
	
	def conn_to_db():
		return MySQLdb.connect(
			host=host,
			user=user,
			passwd=passwd,
			db=db_name,
			charset=charset,
			use_unicode=use_unicode
		)
	
	try:
		if db_name in __mysql and __mysql[db_name].open:
			return __mysql[db_name]
		__mysql[db_name] = conn_to_db()
	except MySQLdb.OperationalError as e:
		if len(e.args) == 2 and e.args[0] == 2006 and e.args[1] == 'MySQL server has gone away':
			__mysql[db_name] = conn_to_db()
	return __mysql[db_name]


def stringify(item):
	return '"%s"' % item
