import os
import csv
import glob
import re
import shapefile

SRCDIR = '/osm/externaldata/nbi/2011/'
OUTDIR = os.path.join(SRCDIR,'out')
OUTCSV = 'nbi_all_viaducts.csv'
OUTCSVBAD = 'nbi_baddata.csv'
OUTSHP = 'nbi_all_viaducts'

FIELDDEF = os.path.join(os.path.dirname(__file__), './fieldnames_lengths.csv')

# Rows  in the source file that hold the lon and lat
LONROW = 19
LATROW = 20

# Rows identifying service type on and under the structure
ONSERVICEROW = 45
UNDERSERVICEROW = 46

# Rows identifying the number of lanes on and under the structure
ONROW = 27
UNDERROW = 28

# Row that holds the 'Features Intersected' information (field 6A)
FEATURESROW = 10

outshape = shapefile.Writer(shapefile.POINT)

fielddefs = csv.reader(open(FIELDDEF, 'rb'))
for row in fielddefs:
    fieldname = row[0]
    fieldlength = int(row[1]) or 50
    outshape.field(fieldname, 'C', fieldlength)

print('shapefiles initialized with %i fields' % (len(outshape.fields)))

def dmgToDecimal(dmgfield):
    try:
        leadingminus = 1 if dmgfield[0] == '-' else 0
        degslength = len(dmgfield) - (6)
        degs = dmgfield[leadingminus:degslength]
        decfraction = 0.0
        mins = dmgfield[degslength:degslength + 2]
        secs = dmgfield[degslength + 2:]
        secs = int(mins) * 60 + (float(secs) / 10 ** (len(secs) - 2))
        decfraction = secs/3600
        return int(degs) + decfraction
    except ValueError:
        print('coordinate field not valid: %s ' % dmgfield)
        return 0.0

def isActualViaduct(row):
    if len(row[ONROW]) == 0 or len(row[UNDERROW]) == 0:
        return False
    # MvE's method
    return row[ONSERVICEROW] not in ('2','9','0') and row[UNDERSERVICEROW] not in ('2','5','7','9','0')
    # PB's method
    #return  int(row[ONROW]) > 0 and int(row[UNDERROW]) > 0 and 'HILLSIDE' not in row[FEATURESROW].upper() 

if not os.path.exists(SRCDIR):
    print('ERROR: Source path %s does not exist' % SRCDIR)
    exit(1)

if not os.path.exists(OUTDIR):
    print('Creating output directory %s' % OUTDIR)
    os.makedirs(OUTDIR)
else:
    print('Output directory %s exists' % OUTDIR)

outcsv = csv.writer(open(os.path.join(OUTDIR,OUTCSV), 'wb'), delimiter = ',', quotechar = '\'', quoting = csv.QUOTE_MINIMAL)
outcsvbad = csv.writer(open(os.path.join(OUTDIR, OUTCSVBAD), 'wb'), delimiter = ',', quotechar = '\'', quoting = csv.QUOTE_MINIMAL)

for file in glob.glob(os.path.join(SRCDIR,'*.csv')):
    header = True
    viaducts = 0
    baddata = 0
    badcoorddata = 0
    total = 0
    print('Processing file %s' % file)
    statecode = os.path.split(file)[1][:2]
    csvfile = csv.reader(open(file,'rb'),delimiter=',',quotechar='\'')
    for row in csvfile:
        if header:
            header = False
            continue
        total += 1
        #row[LONROW] = row[LONROW].lstrip('-')
        #row[LATROW] = row[LATROW].lstrip('-')
        if not (re.match('\d{8}', row[LONROW].lstrip('-')) and re.match('\d{8,9}', row[LATROW].lstrip('-'))):
            baddata += 1
            outcsvbad.writerow(row)
            continue
        row[LONROW] = dmgToDecimal(row[LONROW])
        row[LATROW] = -1 * dmgToDecimal(row[LATROW])
        if row[LONROW] == 0.0 or row[LATROW] == 0.0:
            badcoorddata += 1
            outcsvbad.writerow(row)
            continue
        if (isActualViaduct(row)):
            viaducts += 1
            outcsv.writerow(row)
            outshape.point(row[LATROW], row[LONROW])
            outshape.record(*row)
    print('viaducts: %i / bad coord fields: %i / bad coord field content %i / total %i' % (viaducts,baddata, badcoorddata, total))

outshape.save(os.path.join(OUTDIR,OUTSHP))
