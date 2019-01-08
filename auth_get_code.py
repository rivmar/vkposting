# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals, absolute_import
import ConfigParser
import urllib
import webbrowser


config = ConfigParser.SafeConfigParser()
config.readfp(open('../settings.ini'))

data = {
	'client_id': config.get('VKMain', 'VK_CLIENT_ID'),
	'redirect_uri': config.get('VKMain', 'VK_REDIRECT_URI'),
	'v': config.get('VKMain', 'VK_APIVersion'),
	'response_type': 'token',
	'scope': 'wall,offline,groups',
}


url = config.get('VKMain', 'VK_AUTH_URL')
params = urllib.urlencode(data)
target_url = '{}/?{}'.format(url, params)

webbrowser.open_new_tab(target_url)

exit()
