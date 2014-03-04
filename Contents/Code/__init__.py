from random import randint

NAME    = 'xkcd'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
SEARCH_STEP_REDUCTION_FACTOR = 10
MAX_NB_ITER = 100
JSON_LAST_ELT_URL = 'http://xkcd.com/info.0.json'
JSON_BASE_URL = 'http://xkcd.com/%d/info.0.json'

####################################################################################################
def Start():
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    Plugin.AddViewGroup("Pictures", viewMode="Pictures", mediaType="photos")

    # Set the default ObjectContainer attributes
    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    ObjectContainer.view_group = "List"

    # Default icons for DirectoryObject
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)

    # Set the default cache time
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler('/photos/xkcd', NAME, art = ART, thumb = ICON)
def XKCDMenu():
    oc = ObjectContainer()
    BasicInfos = GetBasicInfos()

    if not BasicInfos:
        # Not able to get even basic infos, aborting
        Log.Error('Basic infos where not found, xkcd may not be available')
        return ObjectContainer(header=NAME, message=L("ErrorBasics"))

    #Create yearly subdirectories
    for i in xrange(BasicInfos['first_year'], BasicInfos['last_year']):
        name = '%d' % (i,)
        oc.add(DirectoryObject(key = Callback(YearDirectory, year=i, binfos=BasicInfos),
                    title=name, thumb =Callback(GetYearIcon, year=i, binfos=BasicInfos)))
    return oc

####################################################################################################
@route('/photos/xkcd/stripdir')
def StripDirectory(stripsstart, stripsstop, sender = None):
    imgXpath = '//div[@id="comic"]//img'
    oc = ObjectContainer(view_group="Pictures")

    for comicURL in GetStripList()[int(stripsstart):int(stripsstop)]:
        imgs = HTML.ElementFromURL(comicURL, cacheTime=CACHE_1YEAR).xpath(imgXpath)[0]
        img = imgs.get('src')
        resume = imgs.get('title')
        titre = imgs.get('alt')
        oc.add(PhotoObject(url=comicURL, title=titre, thumb=Callback(GetIcon, stripURL=comicURL), summary=resume))
    return oc

####################################################################################################
# Find and return an icon in this year
@route('/photos/xkcd/getyearicon')
def GetYearIcon(year, binfos, sender=None):
    img = R(ICON)
    first_nb, last_nb = GetYearNumber(year, binfos)

    # Choose a random img
    if first_nb:
         nb_image = randint(first_nb, last_nb)
         StripInfos = GetJSON(nb_image)
        if StripInfos and 'img' in StripInfos and StripInfos['img']:
            img = StripInfos['img']

    return Redirect(img)

####################################################################################################
# Find boundary numbers for a year
@route('/photos/xkcd/getyearnumbers')
def GetYearNumbers(year, binfos, sender=None):
    # Get data from year cache if existing
    cache = 'year_%d' %(year,)
    year_boundaries = {}

    if Data.Exists(cache):
        # Get data from the JSON cache
        year_boundaries = Data.LoadObject(cache)
        return 

    if not year_boundaries:
        # Very inefficient search algorithm for year boundaries but as cache is used not such a problem
        approxnumber = int(binfos['last_strip_number']*\
                (year-binfos['first_year'])/(binfos['last_year']-binfos['first_year']))
        infos = GetJSON(approxnumber)
        step_backward = (infos['year']) + infos['month']/12 - binfos['first_year'])
        step_backward = approxnumber/(SEARCH_STEP_REDUCTION_FACTOR*step_backward)
        step_forward = (infos['year']) + infos['month']/12 - binfos['last_year'])
        step_forward = (binfos['last_strip_number']-approxnumber)/(SEARCH_STEP_REDUCTION_FACTOR*step_forward)

        # Look for the right values until we find them
        year_first = year_last = 0
        year_before = year after = True

        # Special cases
        if year == binfos['first_year']:
            year_first = 1
            year_before = False
        if year == binfos['last_year']:
            year_last = binfos['last_strip_number']
            year after = False

        i = 0
        while((year_before or year after) and i<MAX_NB_ITER):
            i += 1
            # First entry for the year
            if year_before:
                new_nb = max(int(approxnumber - step_backward),1)
                infos = GetJSON(new_nb)
                if infos['year'] == (year - 1):
                    # We are close, now go forward
                    j = 0
                    while(j<MAX_NB_ITER and infos['year'] != year): 
                        new_nb += 1
                        j += 1
                        infos = GetJSON(new_nb)
                    if infos['year'] == year:
                        year_first = new_nb
                    year_before = False
            # Last entry for the year
            if year after:
                new_nb = min(int(approxnumber + step_forward),binfos['last_strip_number'])
                infos = GetJSON(new_nb)
                if infos['year'] == (year + 1):
                    # We are close, now go backward
                    j = 0
                    while(j<MAX_NB_ITER and infos['year'] != year): 
                        new_nb -= 1
                        j += 1
                        infos = GetJSON(new_nb)
                    if infos['year'] == year:
                        year_last = new_nb
                    year_after = False

    # Ok, now we handle possible errors
    if not year_first or not year_last:
        Log.Critical('Impossible to find the %s strip of the year %d',
                            'first' if not year_first else 'last', year)
    else:
        year_boundaries = {'year_first_strip':year_first, 'year_last_strip':year_last}
        Data.SaveObject(cache, year_boundaries)

    return year_first, year_last

####################################################################################################
# Get basic infos before creating the structure
@route('/photos/xkcd/basicinfos')
def GetBasicInfos(sender=None):
    # Get the number of the last comic
    try:
        LastStripInfos = JSON.ObjectFromURL(JSON_LAST_ELT_URL)
    except:
        Log.Debug('JSON not available for the last strip', iid)
        return {}
    FirstStripInfos = GetJSON('1')

    if FirstStripInfos is None:
        return {}

    infos = {
            'first_year':int(FirstStripInfos['year']),
            'last_year':int(LastStripInfos['year']),
            'last_strip_number':int(LastStripInfos['num']),
            }
    return infos

####################################################################################################
# Get JSON info from URL or cache & cache it
@route('/photos/xkcd/getjson')
def GetJSON(id, sender=None):
    # Get the number of the last comic
    sid = str(id)
    iid = int(id)
    if Data.Exists(sid):
        # Get data from the JSON cache
        StripInfos = Data.LoadObject(sid)
    else:
        # Data not available, get it from URL and cache
        try:
            StripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (iid,))
        except:
            Log.Debug('JSON not available for id=%d', iid)
            return None
        Data.SaveObject(sid, StripInfos)
    return StripInfos
