from random import randint

NAME    = 'xkcd'
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
SEARCH_STEP_REDUCTION_FACTOR = 10
MAX_NB_ITER = 100
CACHE_1YEAR = 365 * CACHE_1DAY
JSON_LAST_ELT_URL = 'http://xkcd.com/info.0.json'
JSON_BASE_URL = 'http://xkcd.com/%s/info.0.json'
MONTHS_NAMES = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]

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
        Log.Error('Basic infos were not found, xkcd may not be available')
        return ObjectContainer(header=NAME, message=L("ErrorBasics"))

    #Create yearly subdirectories
    for i in xrange(BasicInfos['first_year'], BasicInfos['last_year']):
        first_nb, last_nb = GetYearNumbers(BasicInfos,i)
        Log.Debug('Year %d started',i)
        if not first_nb:
            continue
        name = Locale.LocalStringWithFormat('Year_Dirname', i, first_nb, last_nb)
        oc.add(DirectoryObject(
                            key = Callback(YearDirectory, year=i, binfos=BasicInfos),
                            title=name,
                            thumb =Callback(GetIcon, year=i, binfos=BasicInfos)
                            ))
    return oc

####################################################################################################
# Create monthly directories for a year as Photoalbums
@route('/photos/xkcd/yeardirectory')
def YearDirectory(binfos, year, sender=None):
    oc = ObjectContainer()
    first_nb, last_nb = GetYearNumbers(binfos, year)
    
    #Create monthly subdirectories
    for i in xrange(1, 12):
        first_nb, last_nb = GetMonthNumber(binfos, year, i)
        if not first_nb:
            continue
        name = Locale.LocalStringWithFormat('Month_Albumname', L('Month_'+i), first_nb, last_nb)
        oc.add(PhotoAlbumObject(
                                  key = Callback(GetMonthPhotos, binfos=binfos, first=first_nb, last=last_nb),
                                  title = name,
                                  thumb = Callback(GetIcon, year=year, month=i, binfos=binfos)
                                ))
    return oc

####################################################################################################
# Populate monthly directories
@route('/photos/xkcd/getmonthphotos')
def GetMonthPhotos(binfos, first, last, sender=None):
    oc = ObjectContainer()

    #Create monthly subdirectories
    for i in xrange(first, last):
        lPhoto = GetStrip(binfos, i)
        if not lPhoto:
            Log.Warn('Strip number %d was not found', i)
            continue
        oc.add(lPhoto[0])
    return oc

####################################################################################################
# Return a PhotoObject from a strip number or a list, this should absolutely be a int
@route('/photos/xkcd/getstrip')
def GetStrip(binfos, nbstrip, sender = None):
    if isinstance(nbstrip, basestring):
        infos = [GetJSON(int(nbstrip))]
    else:
        try:
            infos = [GetJSON(x) for x in GetJSON(nbstrip)]
        except:
            infos = [GetJSON(nbstrip)]

    photo_list = [PhotoObject(
                            url=x['img'],
                            title=x['title'],
                            # thumb=Callback(GetIcon, id=nbstrip, binfos=binfos),
                            thumb=x['img'],
                            summary=x['alt']
                            ) for x in infos if x]
    return photo_list

####################################################################################################
# Find and return an icon for year, month or id, basic infos are needed
@route('/photos/xkcd/geticon')
def GetIcon(binfos, year=0, month=0, id=0, sender=None):
    img = R(ICON)
    internal_id = 0
    if id:
        internal_id = id
    elif year:
        try:
            if month:
                first_nb, last_nb = GetMonthNumbers(binfos, year, month)
            else:
                first_nb, last_nb = GetYearNumbers(binfos, year)
        except:
            # Error with GetYear/Month functions
            Log.Warn('Function GetIcon defaulting due to GetYear/Month problems')
            return Redirect(img)
    else:
        # Error
        Log.Error('Function GetIcon called without correct args, defaulting...')
        return Redirect(img)

    # Choose a random img
    if not internal_id and first_nb:
        internal_id = randint(first_nb, last_nb)

    # Get image info
    if internal_id:
        StripInfos = GetJSON(internal_id)
        if StripInfos and 'img' in StripInfos and StripInfos['img']:
            img = StripInfos['img']
        else:
            Log.Warn('No image found for id=%d', internal_id)

    return Redirect(img)
####################################################################################################
# Find boundary strip numbers for a month returned as int month_first, int month_last
@route('/photos/xkcd/getmonthnumbers')
def GetMonthNumbers(binfos, year, month, sender=None):
    # Get data from year cache if existing
    cache = 'year_%d' %(year,)
    month_boundaries = {}

    if Data.Exists(cache):
        # Get data from the JSON cache and check if month data exists
        month_boundaries = Data.LoadObject(cache)
        # We already have the year
        if len(month_boundaries)>2:
            month_first = month_boundaries.get('month_%d_first'%(int(month),),None)
            month_last = month_boundaries.get('month_%d_last'%(int(month),),None)
            #Values are there
            if month_first is not None and month_last is not None:
                if not month_last and not month_first:
                    Log.Info('No strip found for %s %d', MONTHS_NAMES[month-1], int(year))
                    return 0, 0
                elif not month_last or not month_first:
                    # Reset the cache for this month if only one strip value is found
                    Log.Debug('Error with cache for %s %d', MONTHS_NAMES[month-1], int(year))
                    month_boundaries.pop('month_%d_first'%(int(month),),None)
                    month_boundaries.pop('month_%d_last'%(int(month),),None)
                else:
                    Log.Debug('For %s, first strip number is %d and last is %d', MONTHS_NAMES[month-1], month_first, month_last)
                    return month_first, month_last

    # Look for the right values until we find them
    month_last = month_first = 0
    month_before = month_after = True

    # Special cases
    if month == 1:
        month_first = year_first
        month_before = False
    if month == 12:
        month_last = year_last
        month_after = False

    # Only 28/31 days in a month, we will go for brute force (more or less)
    year_first, year_last = GetYearNumbers(binfos, year)
    approxnumber = int(year_first + month/12*(year_last - year_first))
    infos = GetJSON(approxnumber)
    step = (infos['month'] + infos['day']/31 - month)
    step = (approxnumber - year_first)/step

    new_nb_before = max(int(approxnumber - step),year_first)
    new_nb_after = min(int(approxnumber + step),year_last)
    while((month_before or month_after) and i<MAX_NB_ITER):
        i += 1
        # First entry for the month
        if month_before:
            # go backward
            infos = GetJSON(new_nb_before)
            if infos['month'] < month:
                # We are close, now go forward
                j = 0
                while(j<MAX_NB_ITER and infos['month'] != month): 
                    new_nb_before += 1
                    j += 1
                    infos = GetJSON(new_nb_before)
                if infos['month'] == month:
                    month_first = new_nb_before
                month_before = False
            else:
                new_nb_before = max(int(new_nb_before - step), year_first)
        # Last entry for the month
        if month_after:
            infos = GetJSON(new_nb_after)
            if infos['month'] > month:
                # We are close, now go backward
                j = 0
                while(j<MAX_NB_ITER and infos['month'] != month): 
                    new_nb_after -= 1
                    j += 1
                    infos = GetJSON(new_nb_after)
                if infos['month'] == month:
                    month_last = new_nb_after
                month_after = False
            else:
                new_nb_after = min(int(new_nb_after + step),year_last)
  
    # Ok, now we handle possible errors
    if not month_first or not month_last:
        Log.Warn('Impossible to find the %s strip of the month %d',
                            'first' if not month_first else 'last', month)
    else:
        # first_label = 'month_%d_first' %(month,)
        # last_label = 'month_%d_last' %(month,)
        month_boundaries['month_%d_first' %(month,)] = month_first
        month_boundaries['month_%d_last' %(month,)] = month_last
        Log.Debug('For %d, first strip number is %d and last is %d', month, month_first, month_last)

    Data.SaveObject(cache, month_boundaries)
    return month_first, month_last

####################################################################################################
# Find boundary strip numbers for a year returned as int year_first, int year_last
@route('/photos/xkcd/getyearnumbers')
def GetYearNumbers(binfos, year, sender=None):
    # Get data from year cache if existing
    if not isinstance(year, int):
        year = int(year)
    cache = 'year_%d' %(year,)
    year_boundaries = {}
    # Data.Remove(cache)

    if Data.Exists(cache):
        # Get data from the JSON cache
        try:
            year_boundaries = Data.LoadObject(cache)
            year_first = year_boundaries['year_first_strip']
            year_last = year_boundaries['year_last_strip']
            Log.Debug('For %d, first strip number is %d and last is %d', year, year_first, year_last)
            return year_first, year_last
        except:
            Log.Warn('For %d, years boundaries were not correctly defined. Correcting.', year)

    # Look for the right values until we find them
    year_first = year_last = 0
    year_before = year_after = True

    # Very inefficient search algorithm for year boundaries but as cache is used not such a problem
    approxnumber = binfos['last_strip_number']*max(year - binfos['first_year'], 1)/(binfos['last_year'] - binfos['first_year'])
    infos = GetJSON(approxnumber)
    # Convert in dictionnary month & year to int
    for k in ('year','month'):
        infos[k] = int(infos[k])
    step_backward = step_forward = 0
    # Special cases
    if year == binfos['first_year']:
        year_first = 1
        year_before = False
    else:
        step_backward = max(infos['year'] + infos['month']/12 - binfos['first_year'],1)
        step_backward = approxnumber/(SEARCH_STEP_REDUCTION_FACTOR*step_backward)
    if year == binfos['last_year']:
        year_last = binfos['last_strip_number']
        year_after = False
    else:
        step_forward = max(binfos['last_year'] - infos['year'] - infos['month']/12,1)
        step_forward = (binfos['last_strip_number'] - approxnumber)/(SEARCH_STEP_REDUCTION_FACTOR*step_forward)
    Log.Debug('For Year %s, step forward is %s and backward is %s, approx number is %s',year,step_forward,step_backward,approxnumber)

    i = 0
    new_nb_before = max(int(approxnumber - step_backward),1)
    new_nb_after = min(int(approxnumber + step_forward),binfos['last_strip_number'])
    while((year_before or year_after) and i<MAX_NB_ITER):
        i = i + 1
        # First entry for the year
        if year_before:
            infos = GetJSON(new_nb_before)
            infos['year'] = int(infos['year'])
            if infos['year'] == (year - 1):
                # We are close, now go forward
                j = 0
                while(j<MAX_NB_ITER and infos['year'] != year): 
                    new_nb_before = new_nb_before + 1
                    j = j + 1
                    infos = GetJSON(new_nb_before)
                    infos['year'] = int(infos['year'])
                if infos['year'] == year:
                    year_first = new_nb_before
                year_before = False
            else:
                new_nb_before = max(int(new_nb_before - step_backward),1)
        # Last entry for the year
        if year_after:
            infos = GetJSON(new_nb_after)
            infos['year'] = int(infos['year'])
            if infos['year'] == (year + 1):
                # We are close, now go backward
                j = 0
                while(j<MAX_NB_ITER and infos['year'] != year): 
                    new_nb_after = new_nb_after - 1
                    j = j + 1
                    infos = GetJSON(new_nb_after)
                    infos['year'] = int(infos['year'])
                if infos['year'] == year:
                    year_last = new_nb_after
                year_after = False
            else:
                new_nb_after = min(int(new_nb_after + step_forward),binfos['last_strip_number'])

    # Ok, now we handle possible errors
    if not year_first or not year_last:
        year_type = 'first' if not year_first else 'last'
        Log.Critical('Impossible to find the %s strip of the year %d', year_type, year)
    else:
        year_boundaries = {'year_first_strip':year_first, 'year_last_strip':year_last}
        Data.SaveObject(cache, year_boundaries)
        Log.Debug('For %d, first strip number is %d and last is %d', year, year_first, year_last)

    return (year_first, year_last)

####################################################################################################
# Get basic infos (dict with 'first_year', 'last_year' and 'last_strip_number')
# before creating the structure
@route('/photos/xkcd/basicinfos')
def GetBasicInfos(sender=None):
    # Get the number of the last comic
    try:
        LastStripInfos = JSON.ObjectFromURL(JSON_LAST_ELT_URL)
    except:
        Log.Error('JSON not available for the last strip')
        return {}
    FirstStripInfos = GetJSON('1')

    if FirstStripInfos is None:
        return {}

    infos = {
            'first_year':int(FirstStripInfos['year']),
            'last_year':int(LastStripInfos['year']),
            'last_strip_number':int(LastStripInfos['num']),
            }
    Log.Debug('Basic infos are: %s', repr(infos)[1:-1])
    return infos

####################################################################################################
# Get JSON info from URL or cache
@route('/photos/xkcd/getjson')
def GetJSON(id, sender=None):
    # Get the number of the last comic
    if not isinstance(id, str):
        id = str(id)

    # Get data from URL or cache
    try:
        StripInfos = JSON.ObjectFromURL(JSON_BASE_URL % (id,), cacheTime=CACHE_1YEAR)
    except:
        Log.Debug('JSON not available for id=%s', id)
        return None

    return StripInfos
