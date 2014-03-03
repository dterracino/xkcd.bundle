from urlparse import urljoin
from math import ceil

NAME    = 'xkcd'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
CACHE_1YEAR = 365 * CACHE_1DAY
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
    nb_image = GetYearNumber(year, binfos, type='random')

    if Data.Exists(str(nb_image)):
        # Get data from the JSON cache
        StripInfos = Data.LoadObject(str(nb_image))
    else:
        # Data not available, get it from URL and cache
        try:
            StripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (nb_image,))
        except:
            return Redirect(img)
        Data.SaveObject(sapprox, StripInfos)

    if 'img' in StripInfos and StripInfos['img']:
        img = StripInfos['img']
    return Redirect(img)

####################################################################################################
# Find an image number for the year: first, last, random
@route('/photos/xkcd/getyear')
def GetYearNumber(year, binfos, nb=1, type='random', sender=None):
    img = 0
    # Get data from year cache if existing
    cache = 'year_%d' %(year,)
    if Data.Exists(cache):
        # Get data from the JSON cache
        ImgYear = Data.LoadObject(cache)
        

    if type=='random':
        approxnumber = int(binfos['last_strip_number']*\
                    (year-binfos['first_year'])/(binfos['last_year']-binfos['first_year']))
        if Data.Exists(sapprox):
                # Get data from the JSON cache
                StripInfos = Data.LoadObject(sapprox)
            else:
                # Data not available, get it from URL and cache
                try:
                    StripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (approxnumber,))
                except:
                    imageurl = ''
                    return Redirect(img)
                Data.SaveObject(sapprox, StripInfos)
        nyear = StripInfos['year']
        
        while(approxnumber!=year):
            if Data.Exists(sapprox):
                # Get data from the JSON cache
                StripInfos = Data.LoadObject(sapprox)
            else:
                # Data not available, get it from URL and cache
                try:
                    StripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (approxnumber,))
                except:
                    imageurl = ''
                    return Redirect(img)
                Data.SaveObject(sapprox, StripInfos)
            nyear = StripInfos['year']
            if nyear>year:
                

        sapprox = str(approxnumber)
        if Data.Exists(sapprox):
            # Get data from the JSON cache
            StripInfos = Data.LoadObject(sapprox)
        else:
            # Data not available, get it from URL and cache
            try:
                StripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (approxnumber,))
            except:
                imageurl = ''
                break
            Data.SaveObject('approxnumber', FirstStripInfos)
        imageurl = StripInfos['img']
    elif type=='random':

    return img

####################################################################################################
# Get basic infos before creating the structure
@route('/photos/xkcd/basicinfos')
def GetBasicInfos(sender=None):
    # Get the number of the last comic
    try:
        LastStripInfos = JSON.ObjectFromURL(JSON_LAST_ELT_URL)
    except:
        return {}
    if Data.Exists('1'):
        # Get data from the JSON cache
        FirstStripInfos = Data.LoadObject('1')
    else:
        # Data not available, get it from URL and cache
        try:
            FirstStripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (1,))
        except:
            return {}
        Data.SaveObject('1', FirstStripInfos)

    infos = {
            'first_year':int(FirstStripInfos['year']),
            'last_year':int(LastStripInfos['year']),
            'last_strip_number':int(LastStripInfos['num']),
            }
    return infos