import requests
import ConfigParser
import logging
from bs4 import BeautifulSoup
from urllib2 import quote
from base64 import b64encode
from time import sleep


config = ConfigParser.ConfigParser()
config.read('config.txt')

SPOTIFY_ACCOUNT_HOST = 'https://accounts.spotify.com/api/'
SPOTIFY_API_HOST = 'https://api.spotify.com/v1/'

SPOTIFY_CLIENT_ID = config.get('spotify_credentials', 'client_id')
SPOTIFY_CLIENT_SECRET = config.get('spotify_credentials', 'client_secret')
SPOTIFY_USER_ID = config.get('spotify_user_info', 'user_id')
SPOTIFY_PLAYLIST_ID = config.get('spotify_user_info', 'playlist_id')


def get_songs(url, latest=True):
	"""
	Gets the tracks from a marketplace.org/latest-music page.
	If latest is True, gets only the latest day. False gets all days on page.
	Returns a list of dicts of artist, title that represent song listings. 
	Returns the empty list if connection fails or no songs found.
	"""
	try:
		page = requests.get(url)
	except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
		return []

	html = BeautifulSoup(page.text, 'html.parser')
	results = []
	if latest:
		# Get just the latest day's group of listings	
		listing_divs = [html.find('div', class_='episode-music')]
	else:
		# Get all days' listings
		listing_divs = html.find_all('div', class_='episode-music')
	for div in listing_divs:
		# Parse into songs
		song_groups = div.find_all('div', class_='episode-music-group')
		# Divs with additional class "last" are the links to amazon; we don't want those
		last_divs = div.find_all('div', class_='last')
		song_listings = [song for song in song_groups if song not in last_divs]


		for song in song_listings:
			title = song.find('a', class_='episode-music-title').text.encode('utf8')
			artist = song.find('div', class_='episode-music-artist').text.encode('utf8')
			results.append({'title': title, 'artist': artist})
			logging.debug('get_songs: found song {0} by {1}'.format(title, artist))
		
	return results


def search_song(title, artist):
	"""
	Searches for a song by its title and artist. 
	Returns a string of the best result's spotify uri, or the empty string if no result.
	"""
	title = quote(title, safe='')
	artist = quote(artist, safe='')
	base_url = SPOTIFY_API_HOST + 'search/' + '?q=track:{0}+artist:{1}&type=track&limit=1'
	url = base_url.format(title, artist)

	results = requests.get(url).json()

	if results['tracks']['total'] == 0:
		logging.debug('Found no results for song {0}'.format(title))
		return ''
	uri_string = results['tracks']['items'][0]['uri']
	logging.debug('Found uri {0} for song {1}'.format(uri_string[uri_string.rfind(':')+1:], title))
	return uri_string[uri_string.rfind(':')+1:]  # Strip off the 'spotify:track:' tag.


def get_playlist_contents(playlist_id, user_id, limit=100):
	"""
	Gets the latest 100 tracks in a playlist.
	Returns a list of spotify track uris.
	"""
	token = get_token()
	headers = {'Authorization': 'Bearer ' + token}
	base_url = SPOTIFY_API_HOST + 'users/{0}/playlists/{1}/tracks?limit={2}'
	url = base_url.format(SPOTIFY_USER_ID, SPOTIFY_PLAYLIST_ID, limit)
	response = requests.get(url, headers=headers).json()  # Todo: Handle errors here. Not using this function so ok for now.

	uris = []
	for item in response['items']:
		uri_string = item['track']['uri']
		uris.append(uri_string[uri_string.rfind(':')+1:])
	return uris


def add_songs(playlist_id, user_id, uris):
	"""
	Adds songs from a list of spotify uris to user_id's playlist_id.
	"""
	"""
	TODO: ensure duplicates not added or else they'll pop to the top of the playlist
	Not going to do this right now. If you want the playlist to be a record of daily tracks, 
	doesn't make sense to get rid of duplicates.
	"""
	for uri in uris:
		logging.debug('Adding uri {0}'.format(uri))
	token = get_token()
	headers = {'Authorization': 'Bearer ' + token}
	base_url = SPOTIFY_API_HOST + 'users/{0}/playlists/{1}/tracks?position=0&uris={2}'

	formatted_uris = [quote('spotify:track:{0}'.format(uri), safe='') for uri in uris if uri]  # Probably shouldn't quote
	uri_string = ','.join(formatted_uris)

	url = base_url.format(SPOTIFY_USER_ID, SPOTIFY_PLAYLIST_ID, uri_string)
	response = requests.post(url, headers=headers)
	logging.debug('Called add url {0}'.format(url))
	logging.debug('Got response {0}'.format(response.text))
	if response.status_code == 429:
		logging.warning('!!!!!!!!!!!!!!!!!!!!!GOT STATUS CODE 429; RATE LIMITING FROM SPOTIFY!!!!!!!!!!!!!!!!!!')


def get_token():
	"""
	Checks for a new spotify access token for the user who granted the refresh token.
	Returns the access token for that user.
	If a new refresh token is sent, that refresh token is written to the config file. 
	"""
	url = SPOTIFY_ACCOUNT_HOST + 'token'
	current_refresh_token = config.get('spotify_credentials', 'refresh_token')
	body = {'grant_type': 'refresh_token', 'refresh_token': current_refresh_token}
	auth_header = 'Basic ' + b64encode('{0}:{1}'.format(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
	headers = {'Authorization': auth_header}
	
	response = requests.post(url, headers=headers, data=body).json()
	if response.has_key('refresh_token'):
		config.set('spotify_credentials', 'refresh_token', response['refresh_token'])
	return response['access_token']


def main(log_level=logging.WARNING):
	# Todo: check that latest songs are not already in playlist. If they are, day hasn't been posted yet.
	logging.basicConfig(level=log_level)
	if config.getboolean('spotify_user_info', 'is_new_playlist'):
		# Playlist is empty, so prime the playlist with ~6 months' worth of titles
		for i in range(13, 0, -1):
			songs = get_songs('http://www.marketplace.org/latest-music?page={0}', latest=False)
			uris = [search_song(song['title'], song['artist']) for song in songs]
			add_songs(SPOTIFY_PLAYLIST_ID, SPOTIFY_USER_ID, uris)

		songs = get_songs('http://www.marketplace.org/latest-music', latest=False)
		uris = [search_song(song['title'], song['artist']) for song in songs]
		add_songs(SPOTIFY_PLAYLIST_ID, SPOTIFY_USER_ID, uris)
		config.set('spotify_user_info', 'is_new_playlist', False)

	else:
		songs = get_songs('http://www.marketplace.org/latest-music')
		if not songs:
			return
		uris = [search_song(song['title'], song['artist']) for song in songs]
		uris = filter(None, uris)
		latest_playlist_songs = get_playlist_contents(SPOTIFY_PLAYLIST_ID, SPOTIFY_USER_ID, len(uris))
		if set(uris).issubset(set(latest_playlist_songs)):  # The latest site songs are the same as the latest playlist songs
			logging.debug("Songs from site {0} == songs from playlist {1}".format(uris, latest_playlist_songs))
			return
		add_songs(SPOTIFY_PLAYLIST_ID, SPOTIFY_USER_ID, uris)


if __name__ == '__main__':
	main()



