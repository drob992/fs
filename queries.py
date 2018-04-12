import utilities

db = __connection = utilities.get_mysql_db('stats')


def fetch(tbl_name, fields=None, where=None):
	if fields:
		fields = ','.join(fields)
	else:
		fields = '*'
	
	_where_tpl = ''
	if where:
		_where_tpl += 'where ' + where
	
	response = []
	__cursor = __connection.cursor()
	__cursor.execute("select {} from {} {}".format(fields, tbl_name, _where_tpl))
	for row in __cursor.fetchall():
		response.append(row[0])
	return response


def save(tbl_name, payload):
	__cursor = __connection.cursor()
	__cursor.execute("insert into {}({}) values({})".format(tbl_name, ','.join(payload.keys()), ','.join(map(utilities.stringify, payload.values()))))
	__cursor.commit()


def update(tbl_name, payload, where=None):
	# spoji argumente
	_update_tpl = ''
	for i in payload:
		_update_tpl += '%s=%s, ' % (i, payload[i])
	
	# da ocistim poslednji zarez
	_update_tpl = _update_tpl[:-2]
	
	if where:
		_update_tpl += ' where ' + where
		
	__cursor = __connection.cursor()
	__cursor.execute("update {} set {} ".format(tbl_name, _update_tpl))
	__cursor.commit()


if __name__ == '__main__':
	save(tbl_name='test', payload={'name': 'pera', 'a': 1, 'fff': True})
	
	update(tbl_name='test', payload={'a': 1, 'fff': True}, where='id=1')
	
	fetch(tbl_name='test', fields=['name', 'id'], where='1=1')
