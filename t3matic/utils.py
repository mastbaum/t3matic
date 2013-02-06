'''Various utilities.'''

import string

class MyTemplate(string.Template):
    delimiter = '%'


def read_config(path):
    '''Read the configuration from a JSON file.

    :param path: The path to the configuration JSON file
    '''
    import json
    config = None
    with open(path) as f:
        config = json.load(f)
    return config


def read_config_db(host, dbname, username, password):
    '''Read the configuration from a CouchDB database.

    :param host: Server hostname
    :param dbname: Database name
    :param username: CouchDB username (optional)
    :param password: CouchDB assword (optional)
    '''
    import couchdb
    couch = couchdb.Server(host)
    if username is not None and password is not None:
        couch.resource.credentials = (username, password)
    db = couch[dbname]
    config = dict(db['config'])
    return config


def email(recipients, subject, message, sender=None):
    '''sends a good, old-fashioned email via smtp

    From yelling: https://github.com/mastbaum/yelling
    '''
    import types
    import getpass
    import socket
    import smtplib
    import settings

    if type(recipients) is not types.ListType:
        recipients = [recipients]
    if not sender:
        username = getpass.getuser()
        hostname = socket.gethostname()
        sender = '%s@%s' % (username, hostname)
    try:
        smtp = smtplib.SMTP(settings.smtp_server)
        smtp.sendmail(sender, recipients, message)
    except smtplib.SMTPException:
        print 'yelling: email: Failed to send message'
        raise

