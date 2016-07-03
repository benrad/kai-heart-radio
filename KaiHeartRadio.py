import requests
import ConfigParser
from bs4 import BeautifulSoup
from urllib2 import quote


config = ConfigParser.ConfigParser()
config.read('confix.txt')

SPOTIFY_ACCOUNT_HOST = 'https://accounts.spotify.com/'
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
	title = urllib2.quote(title, safe='')
	artist = urllib2.quote(artist, safe='')
	base_url = SPOTIFY_API_HOST + 'search/' + '?q=track:{0}+artist:{1}&type=track&limit=1'
	url = base_url.format(title, artist)

	results = requests.get(url).json()

	if results['tracks']['total'] == 0:
		return ''
	return results['tracks']['items'][0]['uri']


def add_songs(playlist_id, user_id, uris):
	"""
	Adds songs from a list of spotify uris to user_id's playlist_id.
	"""
	token = get_token()
	# Should use position=0 url param to prepend songs, otherwise will be appended
	pass


def get_token():
	"""
	Checks for a new spotify access token for the user who granted the refresh token.
	Returns the access token for that user.
	If a new refresh token is sent, that refresh token is written to the config file. 
	"""
	refresh_token = config.read('spotifycredentials', 'refresh_token')
	pass


def main():
	playlist_id = spotify:user:1248422519:playlist:3zJ2HaPyALFHcyTZnh8BXl
	songs = get_songs()
	uris = [search_song(song['title'], song['artist']) for song in songs]
	add_songs(SPOTIFY_PLAYLIST_ID, SPOTIFY_USER_ID, uris)


# Need to ensure duplicates not added or else they'll pop to the top of the playlist
