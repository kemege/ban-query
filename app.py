import ipaddress
import os
import json
import logging
import datetime
from flask import Flask, request, render_template, Blueprint, abort, send_from_directory
from pyctuator.auth import BasicAuth
from flaskext.mysql import MySQL
import pymysql.cursors
from pyctuator.pyctuator import Pyctuator


# Initialize flask app
app = Flask(__name__)

# Load parameters
logPath = os.path.abspath(os.path.join('.', 'logs'))
app.config.from_json('config.json')
ipWhitelist = [ipaddress.ip_network(x) for x in app.config['IP_WHITELIST'].split()]

# Configure logging
logFilename = os.path.join(logPath, 'log-%s.log' % datetime.date.today().isoformat())
logging.basicConfig(filename=logFilename,
                    format='%(asctime)s - %(levelname)s : %(message)s',
                    level=logging.INFO)

# Initialize MySQL
mysql = MySQL(app, autocommit=True,
              cursorclass=pymysql.cursors.DictCursor)

# Setup pyctuator monitor
auth = BasicAuth(app.config['SBA_USER'], app.config['SBA_PASSWORD'])
Pyctuator(app, app.config['APP_NAME'], app_url=app.config['APP_URL'],
          pyctuator_endpoint_url=app.config['APP_ENDPOINT_URL'],
          registration_url=app.config['SBA_URL'],
          registration_auth=auth)

# IP whitelist limit
@app.before_request
def limitRemoteAddress():
    ipRemote = ipaddress.ip_address(request.remote_addr)
    passRequest = False
    for w in ipWhitelist:
        if ipRemote in w:
            passRequest = True
    if not passRequest:
        abort(403)

# Static files
@app.route('/static/<path:path>')
def staticFiles(path):
    type = path.split('/', maxsplit=1)[0]
    if type not in ['js', 'css', 'img', 'fonts']:
        abort(404)
    return send_from_directory('static', path)


# App routes
@app.route('/')
def index():
    '''
    Index page for testing
    '''
    return 'It works!'


@app.route('/ui')
def indexUI():
    '''
    UI page index
    '''
    return render_template('ui.html')


@app.route('/query', methods=['POST'])
def queryRecord():
    '''
    Query lock records
    '''
    keyword = request.form.get('keyword', '')
    c = mysql.get_db().cursor()
    sql = 'SELECT * FROM lock_list WHERE account LIKE %s ORDER BY time DESC LIMIT %s;'
    result = []
    logging.info(f'User from {request.remote_addr} querying records with keyword "{keyword}"')
    c.execute(sql, ('%' + keyword + '%', 100))
    for row in c:
        result.append(row)
    return json.dumps(result, default=str)


@app.route('/add', methods=['POST'])
def addRecord():
    '''
    Add lock records
    '''
    account = request.form.get('account', None)
    operation = request.form.get('operation', None)
    timeString = request.form.get('time', None)
    reason = request.form.get('reason', None)
    source = request.form.get('source', 'MANUAL')

    if timeString is not None:
        recordTime = datetime.datetime.strptime(timeString, '%Y-%m-%d %H:%M:%S')

    if account is None or operation is None or recordTime is None or reason is None:
        result = {'code': 1, 'reason': 'Invalid input'}
    else:
        try:
            c = mysql.get_db().cursor()
            sql = ('INSERT INTO lock_list(account, operation, time, reason, source) VALUE (%s, %s, %s, %s, %s);')
            c.execute(sql, (account, operation, recordTime, reason, source))
            logging.info(f'User from {request.remote_addr} added {operation} record for user "{account}" with reason "{reason}"')
            result = {'code': 0}
        except Exception as ex:
            logging.info(f'Exception encountered for request from {request.remote_addr}, content: ({account}, {operation}, {reason}), reason: {str(ex)}')
            result = {'code': 2, 'reason': 'Exception encountered: ' + str(ex)}

    return json.dumps(result)