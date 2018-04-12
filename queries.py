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
		response.append(row)
	return response


def save(tbl_name, payload):
	__cursor = __connection.cursor()
	__cursor.execute("insert into {}({}) values({})".format(tbl_name, ','.join(payload.keys()), ','.join(map(utilities.stringify, payload.values()))))
	__connection.commit()


def update(tbl_name, payload, where=None):
	# spoji argumente
	_update_tpl = ''
	for i in payload:
		_update_tpl += '%s="%s", ' % (i, payload[i])
	
	# da ocistim poslednji zarez
	_update_tpl = _update_tpl[:-2]
	
	if where:
		_update_tpl += ' where ' + where
		
	__cursor = __connection.cursor()
	__cursor.execute("update {} set {} ".format(tbl_name, _update_tpl))
	__connection.commit()


if __name__ == '__main__':
	pass
	# save(tbl_name='countries', payload={'name': 'Serbia'})
	#
	# update(tbl_name='countries', payload={'name': 'Srbija'}, where='id=5')
	#
	# data = (fetch(tbl_name='countries', fields=['name', 'id'], where='1=1'))
	#
	# for i in data:
	# 	print(i[1])
