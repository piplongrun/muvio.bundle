import unicodedata

VERSION = '1.0.0'
SERACH_URL = 'https://tadata.me/muvio/?artist=%s'

TYPE_ORDER = ['music_video', 'live_music', 'lyric_video']
TYPE_MAP = {
  'music_video': MusicVideoObject,
  'live_music': LiveMusicVideoObject,
  'lyric_video': LyricMusicVideoObject
}

RE_LIVE_VIDEO = Regex('live (on|at|in|from|for)|\(live|unstaged\)|.*(tour|festival).*', Regex.IGNORECASE)

####################################################################################################
def Start():

  HTTP.CacheTime = CACHE_1WEEK
  HTTP.Headers['User-Agent'] = 'MUVIO/%s (%s %s; Plex Media Server %s)' % (VERSION, Platform.OS, Platform.OSVersion, Platform.ServerVersion)

####################################################################################################
def ArtistName(artist):

  try:
    artist = unicodedata.normalize('NFKD', artist.decode('utf-8'))
  except UnicodeError:
    artist = unicodedata.normalize('NFKD', artist)

  # Strip diacritics
  stripped = u''

  for i in range(len(artist)):
    point = artist[i]

    if not unicodedata.combining(point):
      stripped += point

  return stripped

####################################################################################################
class Muvio(Agent.Artist):

  name = 'MUVIO'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.lastfm']

  def search(self, results, media, lang):

    results.Append(MetadataSearchResult(
      id = ArtistName(media.primary_metadata.title),
      score = 100
    ))

  def update(self, metadata, media, lang):

    try:
      json_obj = JSON.ObjectFromURL(SERACH_URL % (String.Quote(metadata.id)))
    except:
      Log('*** Call to search API failed... ***')
      return None

    extras = []

    for video in json_obj['videos']:

      if 'lyric video' in video['title'].lower():
        extra_type = 'lyric_video'
      elif RE_LIVE_VIDEO.search(video['title']):
        extra_type = 'live_music'
      else:
        extra_type = 'music_video'

      extras.append({
        'type': extra_type,
        'extra': TYPE_MAP[extra_type](
          url = 'muvio://%s' % (video['url'].split('//')[-1]),
          title = video['title'],
          thumb = video['thumb_url']
        )
      })

    extras.sort(key=lambda e: TYPE_ORDER.index(e['type']))

    for extra in extras:
      metadata.extras.add(extra['extra'])

####################################################################################################
class Muvio(Agent.Album):

  name = 'MUVIO'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.lastfm']

  def search(self, results, media, lang):

    artist = ArtistName(String.Unquote(media.primary_metadata.id.split('/')[0])) # Album object doesn't have artist information(?). Grab it from the metadata id instead.

    try:
      json_obj = JSON.ObjectFromURL(SERACH_URL % (String.Quote(artist)))
    except:
      Log('*** Call to search API failed... ***')
      return None

    artist = json_obj['artist']

    results.Append(MetadataSearchResult(
      id = artist,
      score = 100
    ))

  def update(self, metadata, media, lang):

    try:
      json_obj = JSON.ObjectFromURL(SERACH_URL % (String.Quote(metadata.id)))
    except:
      return None

    for index, track in enumerate(media.children):

      for video in json_obj['videos']:

        score = 100 - (10 * abs(String.LevenshteinDistance(track.title.lower(), video['title'].lower())))
        #Log("%s vs %s --> %d" % (track.title.lower(), video['title'].lower(), score))

        if score > 80:

          music_video = MusicVideoObject(
            url = 'muvio://%s' % (video['url'].split('//')[-1]),
            title = video['title'],
            thumb = video['thumb_url']
          )

          # Add the video, and we're done (only one video per track allowed)
          #Log('Adding music video %s to track %s - %s' % (music_video.title, index, track.title))
          metadata.tracks[track.guid].extras.add(music_video)
          break
