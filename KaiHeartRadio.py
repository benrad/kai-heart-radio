import requests
import ConfigParser
from bs4 import BeautifulSoup
from urllib2 import quote
from base64 import b64encode


config = ConfigParser.ConfigParser()
config.read('config.txt')

SPOTIFY_ACCOUNT_HOST = 'https://accounts.spotify.com/api/'
SPOTIFY_API_HOST = 'https://api.spotify.com/v1/'
SPOTIFY_CLIENT_ID = config.get('spotifycredentials', 'client_id')
SPOTIFY_CLIENT_SECRET = config.get('spotifycredentials', 'client_secret')
SPOTIFY_USER_ID = '1248422519':
SPOTIFY_PLAYLIST_ID = '3zJ2HaPyALFHcyTZnh8BXl'


def get_songs():
	"""
	Gets the most recent single-day listing of tracks.
	Returns a list of dicts of artist, title that represent song listings. 
	Returns the empty list if connection fails or no songs found.
	"""
	try:
		page = requests.get('http://www.marketplace.org/latest-music')
	except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
		return []

	html = BeautifulSoup(page.text, 'html.parser')
	listing_div = html.find('div', class_='episode-music')
	# Parse into songs
	song_groups = listing_div.find_all('div', class_='episode-music-group')
	# Divs with additional class "last" are the links to amazon; we don't want those
	last_divs = listing_div.find_all('div', class_='last')
	song_listings = [song for song in song_groups if song not in last_divs]

	results = []
	for song in song_listings:
		title = song.find('a', class_='episode-music-title').text
		artist = song.find('div', class_='episode-music-artist').text
		results.append({'title': title, 'artist': artist})
	
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
		return ''
	uri_string = results['tracks']['items'][0]['uri']
	return uri_string[uri_string.rfind(':'):]  # Strip off the 'spotify:track:' tag.


def get_playlist_contents(playlist_id, user_id):
	"""
	Gets the latest 100 tracks in a playlist.
	Returns a list of spotify track uris.
	"""
	token = get_token()
	headers = {'Authorization': 'Bearer ' + token}
	base_url = SPOTIFY_API_HOST + 'users/{0}/playlists/{1}/tracks'
	url = base_url.format(SPOTIFY_USER_ID, SPOTIFY_PLAYLIST_ID)
	response = requests.get(url, headers=headers).json()  # Todo: Handle errors here. Not using this function so ok for now.

	uris = []
	for item in response['items']:
		uri_string = item['track']['uri']
		uris.append(uri_string[uri_string.rfind(':'):])
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
	token = get_token()
	headers = {'Authorization': 'Bearer ' + token}
	base_url = SPOTIFY_API_HOST + 'users/{0}/playlists/{1}/tracks?position=0&uris={2}'

	formatted_uris = [quote('spotify:track:{0}'.format(uri)) for uri in uris]
	uri_string = ','.join(formatted_uris)

	url = base_url.format(SPOTIFY_USER_ID, SPOTIFY_PLAYLIST_ID, uri_string)
	requests.post(url, headers=headers)


def get_token():
	"""
	Checks for a new spotify access token for the user who granted the refresh token.
	Returns the access token for that user.
	If a new refresh token is sent, that refresh token is written to the config file. 
	"""
	url = SPOTIFY_ACCOUNT_HOST + 'token'
	current_refresh_token = config.read('spotifycredentials', 'refresh_token')
	body = {'grant_type': 'refresh_token', 'refresh_token': current_refresh_token}
	auth_header = 'Basic ' + b64encode('{0}:{1}'.format(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET))
	headers = {'Authorization': auth_header}
	
	response = requests.post(url, headers=headers, data=body).json()
	if response.has_key('refresh_token'):
		config.set('spotifycredentials', 'refresh_token', response['refresh_token'])
	return response['access_token']


def main():
	songs = get_songs()
	uris = [search_song(song['title'], song['artist']) for song in songs]
	add_songs(SPOTIFY_PLAYLIST_ID, SPOTIFY_USER_ID, uris)



