
from register.models import *

def getRR( event, psdid ):
    return RegRecord.objects.get( event=event, psdid=psdid )


a = getRR( 'mg2012', 'TN103' )
b = getRR( 'mg2012', 'SW104' )

a.interest_score(b)
b.interest_score(a)


from register.matchmaker import *

updateMatchRecords( 'mg2012', verbose=True )
