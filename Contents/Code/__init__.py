from urlparse import urljoin
from math import ceil

NAME    = 'xkcd'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
CACHE_1YEAR = 365 * CACHE_1DAY
####################################################################################################
def Start():
    # Set the default ObjectContainer attributes
    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME

    # Default icons for DirectoryObject
    DirectoryObject.thumb = R(ICON)
    DirectoryObject.art = R(ART)

    # Set the default cache time
    HTTP.CacheTime = CACHE_1HOUR

####################################################################################################
@handler('/photos/xkcd', NAME, art = ART, thumb = ICON)
def XKCDMenu():
    oc = ObjectContainer()
    StripsList = GetStripList()
    nb_images = int(Prefs['nbimgindir'])
    
    if len(StripsList) < nb_images:
        #will never happen
        imgXpath = '//div[@id="comic"]//img'
        for comicURL in GetStripList():
            imgs = HTML.ElementFromURL(comicURL, cacheTime=CACHE_1YEAR).xpath(imgXpath)[0]
            img = imgs.get('src')
            resume = imgs.get('title')
            titre = imgs.get('alt')
            oc.add(PhotoObject(url=comicURL, title=titre, thumb=Callback(GetIcon, stripURL=comicURL), summary=resume))
    else:
        #Create subdirectories containing a fixed number of images
        nbdir = ceil(float(len(StripsList))/nb_images)
        for i in xrange(1,nbdir+1):
            firstelt = (i-1)*nb_images
            lastelt = i*nb_images
            if i == nbdir:
                lastelt = len(StripsList)
            name = '%d - %d' % (firstelt+1, lastelt)
            oc.add(DirectoryObject(key = Callback(StripDirectory, stripsstart=firstelt, stripsstop=lastelt),
                    title=name, thumb =Callback(GetIcon, stripURL=StripsList[firstelt])))
    return oc

####################################################################################################
@route('/photos/xkcd/stripdir')
def StripDirectory(stripsstart, stripsstop, sender = None):
    imgXpath = '//div[@id="comic"]//img'
    oc = ObjectContainer()

    for comicURL in GetStripList()[int(stripsstart):int(stripsstop)]:
        imgs = HTML.ElementFromURL(comicURL, cacheTime=CACHE_1YEAR).xpath(imgXpath)[0]
        img = imgs.get('src')
        resume = imgs.get('title')
        titre = imgs.get('alt')
        oc.add(PhotoObject(url=comicURL, title=titre, thumb=Callback(GetIcon, stripURL=comicURL), summary=resume))
    return oc

####################################################################################################
@route('/photos/xkcd/geticon')
def GetIcon(stripURL, sender=None):
    imgXpath = '//div[@id="comic"]//img'
    imgs = HTML.ElementFromURL(stripURL, cacheTime=CACHE_1YEAR).xpath(imgXpath)
    img = R(ICON)
    if len(imgs):
        img = imgs[0].get('src')
    return Redirect(img)

####################################################################################################
@route('/photos/xkcd/getstriplist')
def GetStripList(sender=None):
    archiveURL = 'http://xkcd.com/archive/'
    archiveXPath = '//div[@id="middleContainer"]/a'
    # Get all the elements needed to determine the number of entries and how to sectionize them
    StripsMainPage = HTML.ElementFromURL(archiveURL).xpath(archiveXPath)
    StripsList = [urljoin(archiveURL, comic.get('href')) for comic in StripsMainPage]
    StripsList.reverse()
    return StripsList