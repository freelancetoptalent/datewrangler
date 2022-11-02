"""
Module for dealing with text-to-text match questions.

In principle this is stand-alone code that doesn't use Django at all, to aid testing.
"""

import re


class MatchFeature(object):
    """
    Holds the word used for identity (or thing to seek) along with
    flag for if "not" was before it and so forth
    """

    def __init__(self, word, notFlag=False, linkWord=None, passion=0 ):
        self.word = word
        self.notFlag = notFlag
        self.linkWord = linkWord
        self._passion = passion
        if not self.linkWord is None and self.linkWord in ["needs","requires","demands"]:
            self._passion += 2

    def passion(self):
        return self._passion

    def nice_string(self):
        ss = ""
        if self.notFlag:
            ss = "not %s" % (self.word )
        else:
            ss = self.word
        if self.passion():
            if self.passion() > 1:
                ss += " (" + ( "really, " * (self.passion()-2) ) + "really important)"
            else:
                ss += " (important)"

        return ss


    def __str__(self):
        if self.linkWord is None:
            if self.notFlag:
                return "MF[not %s]" % (self.word )
            else:
                return "MF[%s]" % (self.word )
        else:
            passn = ""
            if self.passion() > 0:
                passn = "!" * self.passion()
            if self.notFlag:
                return "MF[%s not %s%s]" % (self.linkWord, self.word, passn )
            else:
                return "MF[%s %s%s]" % (self.linkWord, self.word, passn)


    def __unicode__(self):
        return self.__str__()





class TextResponse(object):
    """
    A Persons recorded text response to one of the extra match questions
    """
    #owner = models.ForeignKey(Person)
    #comments = models.TextField(blank=True, verbose_name="Match Desires")


    def __init__(self, text, seek_text = None, verbose = False ):
        if verbose:
            print "Processing '%s' / '%s'" % (text, seek_text )
            
        if not seek_text is None:
            text = self.process_seek_text(text, stem = "I am" )
            text = text + self.process_seek_text( seek_text, stem = "seeks" )
        else:
            text = text.strip()
            text = re.split( '\s*[\\.,;\\n]+\s*', text )

        self.comments = "; ".join( text )
        self.processed = False
        self.identities_cac = None
        self.seeks_cac = None
        self.valid_entry = None
        self.validation_error = None
        self.fetch_info()

    def simplify_text( self, c, not_str = "# " ):
        c = c.strip()
        c = re.sub( r'\s+', ' ', c )
        c = re.sub( r'_', '-', c )
        c = c.lower()

        an_sub = re.compile( r'\b(a|an)\b', re.IGNORECASE )
        not_sub = re.compile( r'\b(not\b\s+|non\b\s+|not\-|non\-)', re.IGNORECASE )
        im_sub = re.compile( r"\b[Ii]'m\b", re.IGNORECASE )

        # print "Processing '%s'" % (c, )
        c = an_sub.sub('', c)  # to drop a's and an's
        c = not_sub.sub(not_str, c)  # to help get words to align right in the re step
        c = im_sub.sub("I am", c)

        return c

    def process_seek_text(self, text, stem="seeks" ):
        # print "Processing seek text"
        text = re.sub( r'\n', '; ', text )
        text = self.simplify_text(text, not_str = "not ")
        text = re.split( '\s*[\\.,;\\n]+\s*', text )
        # filter out empty strings. if the input is empty that might leave the empty list!
        text = [t for t in text if t]
        seek_pattern = "(I am|I'm|i am|seeks|seeking|needs|needing|demands|demanding|requires|requiring)"
        pseek = re.compile( r"\b%s\b" % (seek_pattern, ) )
            
        # add stem to anything without a stem
        for i, word in enumerate( text ):
            #print "%s  %s -> %s" % (i, word, pseek.match( word ) )
            
            if not pseek.search( word ):
                text[i] = stem + " " + word

        return text



    def fetch_info(self):
        self.valid_entry = True
        wstrip = self.simplify_text( self.comments )
        chunks = re.split( '[\\.,;\\n]+\s*', wstrip )
        self.identities_cac = {}
        self.seeks_cac = {}
        seek_pattern = "(?P<seekword>seeks|seeking|needs|needing|demands|demanding|requires|requiring)"
        pseek = re.compile( r"\b%s\b" % (seek_pattern, ) )
        p = re.compile( r"^\s*(?P<isclause>(?P<iam>I am)?\s*(?P<isnot>#)?\s*(?P<is>\b[\w\-.&]+\b))?\s*(?P<seekclause>%s\s+(?P<seeknot>#)?\s*(?P<seeks>\b[\w\-.&]+))?(?P<emphasis>!+)?\s*$" % (seek_pattern, ),
                        flags=re.IGNORECASE)
#        p = re.compile( """^(?P<isclause>(?P<iam>I am)?\s*(?P<isnot>#)?\s*[\ba|an\b]*(?P<is>\b\S+\b))?\s*(?P<seekclause>(?P<seekword>\b\S+\b)\s*(?P<seeknot>#)?\s*(?P<seeks>\b[\w\-.&]+))?(?P<emphasis>!+)?$""",
#                        re.IGNORECASE | re.VERBOSE )
#        p = re.compile( """^(?P<isclause> \s* (?P<isnot>#)? \s* (?P<is>\b[\w\-.&]+\b))?
#                    \s*
#                    (?P<seekclause> (?P<seekword>\b\S+\b) \s* (?P<seeknot>#)? \s* (?P<seeks>\b[\w\-.&]+))?
#                    (?P<emphasis>!+)?$""",
#                        re.IGNORECASE | re.VERBOSE)
        p2w = re.compile( r"^\s*(?P<isnot>#)?\s*(?P<word1>[\w\-.&]+)\s+(?P<word2>[\w\-.&]+)(?P<emphasis>!+)?\s*$", flags=re.IGNORECASE )

        for c in chunks:

            #print "\tnow '%s'" % (c, )
            
            m = p.match( c )
            if m is None:

                # the two-word hack.  If it is two words, hyphenate automatically
                m2 = p2w.match( c )
                if m2 is None:
                    # print "\tskipped, bad"
                    self.valid_entry = False
                    self.validation_error = c
                else:
                    #print "no match--two word rescue?"
                    #print m2.groups()
                    passion = 0
                    if not m2.group("emphasis") is None:
                        passion += len( m2.group( "emphasis" ) )
                    isnot = m2.group( "isnot" ) != None
                    if  pseek.match( m2.group("word1") ) or pseek.match( m2.group("word2" ) ):
                        self.valid_entry = False
                        self.validation_error = c
                    else:
                        wrd = m2.group("word1") + "-" + m2.group( "word2" )

                        self.identities_cac[ wrd ] = MatchFeature( wrd, isnot )
                        self.seeks_cac[ wrd ] = MatchFeature( wrd, isnot, "seeks", passion )
            else:
                #print m.groups()
                #print "Chunked into: isclause=%s (%s %s)   seekclause=%s (%s %s %s)" % ( m.group("isclause"), m.group("isnot"), m.group("is"),
                #                                                    m.group("seekclause"), m.group("seekword"), m.group("seeknot"), m.group("seeks" ) )
                passion = 0
                if not m.group("emphasis") is None:
                    passion += len( m.group( "emphasis" ) )
                if not m.group("isclause" ) is None:
                    isnot = m.group( "isnot" ) != None
                    self.identities_cac[ m.group("is") ] = MatchFeature( m.group("is"), isnot )
                    if m.group("seekclause") is None and m.group("iam") is None:
                        # print "Simple identity: no seek"
                        self.seeks_cac[ m.group("is") ] = MatchFeature( m.group("is"), isnot, "seeks", passion )
                if not m.group("seekclause") is None:
                    seeknot = m.group( "seeknot" ) != None
                    self.seeks_cac[ m.group("seeks") ] = MatchFeature( m.group("seeks"), seeknot, m.group("seekword" ), passion )
                    # print "Added seek clause of %s" % ( m.group("seeks"), )
        self.processed = True


    def identities(self):
        if not self.processed:
            self.fetch_info()
        return self.identities_cac

    def seeks(self):
        if not self.processed:
            self.fetch_info()
        return self.seeks_cac


    def score_pair( self, seek, ident):
        """
        Take a pair of MatchQuestions and return the score of the pair.
        """
        score = 0
        if seek.word == ident.word:
            score += 1 + seek.passion()
        if seek.notFlag != ident.notFlag:
            score = -100 - 100*score
        return score


    def match_quality( self, other ):
        """
        Do we match the passed TextResponse object?
        """
        seeks = self.seeks()
        ident = other.identities()
        score = 0
        for s in seeks.keys():
            #print "Processing %s / %s" % (s, seeks[s] )
            sk = seeks.get(s)
            if ident.get(s):
                score += self.score_pair( sk, ident.get(s) )

        return score

    def match_summary(self, other):
        i_seek = self.seeks()
        u_seek = other.seeks()
        i_am = self.identities()
        u_are = other.identities()

        printables = []
        words = set(self.seeks()).union(set(self.identities()))
        for word in words:
            i_seek = self.seeks().get(word)
            u_seek = other.seeks().get(word)
            i_am = self.identities().get(word)
            u_are = other.identities().get(word)
            
            if (i_seek and u_are):
                if i_seek.notFlag or u_are.notFlag:
                    # anti-match! or agreement on negative trait.
                    # the latter case might be printable, but for now let's not.
                    continue
                printables.append(word)
            elif (u_seek and i_am):
                if u_seek.notFlag or i_am.notFlag:
                    continue
                if u_are:
                    printables.append(word)
                else:
                    printables.append("seeks %s" % word)
        return printables


    def print_table(self):
        print "TextResponse Table for %s\nIdentities:" % (self,)
        ilst = self.identities()
        for s in ilst:
            print "\t%s / %s" % (s, ilst[s] )
        print "Seeks:"
        ilst = self.seeks()
        for s in ilst:
            print "\t%s / %s" % (s, ilst[s]  )
        if not self.valid_entry:
            print "\t(Invalid entry: %s)\n" % ( self.validation_error, )


    def ident_string_list(self):
        """
        Return list of strings of what identifies as
        """
        sts = [ m.nice_string() for m in self.identities().values() ]
        return sts


    def seek_string_list(self):
        """
        Return list of strings of what looking for
        """
        sts = [ m.nice_string() for m in self.seeks().values() ]
        return sts


    def words( self ):
        st = set( self.seeks().keys() )
        st2 = set( self.identities().keys() )
        return st | st2

    def translate_words( self, word_dict ):
        """
        Given a dictionary mapping word to new word, go through and translate all words to 
        the new words in the dict
        """
        for (wrd, rec) in self.identities_cac.items():
            if wrd in word_dict:
                del self.identities_cac[wrd]
                rec.word = word_dict[wrd]
                self.identities_cac[ word_dict[ wrd ] ] = rec
        for (wrd, rec) in self.seeks_cac.items():
            if wrd in word_dict:
                del self.seeks_cac[wrd]
                rec.word = word_dict[wrd]
                self.seeks_cac[ word_dict[ wrd ] ] = rec

        
    def ident_words( self ):
        return set( self.identities().keys() )

    def seek_words( self ):
        return set( self.seeks().keys() )

    def __str__(self):
        txt = self.comments
        return "TR[%s]" % (self.comments, )

    def __unicode__(self):
        return self.__str__()


        
def alt_test():

        cases = """
nerd; geek; runner; not smoker; not kinky
not asexual; casual; married
vegan!!; vegetarian!; bicycler; not smoker; educator; economics; liberal; not libertarian; cats
kinky; nerd; Somerville; Cambridge; Boston; tattoos; body piercings; medicine; healthcare; extrovert; social; parties; dancing; trivia; poker
not smoker!!; musician!; not kinky
solo poly; solo-poly; grad student; not smoker; kinky; ballroom-dancing; top seeks bottom; butch seeks femme
bondage bdsm kinky childfree top dominant dom nerd seeks submissive seeks sub seeks bottom

nerd
man seeks woman or couple seeking to form a ltr!
tattoos; fitness; not kinky; monogamy-friendly; not asexual
solo poly; not smoker;
kinky!!!; not unicorn seeks bartender; masochist seeks not submissive; math-nerd; science-nerd; movie-lover; film-buff; sex-positive!!; slut; scientist; mathematician; trekkie; queer; not monogamy-friendly; not asexual!!!; not monogamous!!; nonmonogamous; sexual; adventures; introvert seeks extrovert; cocktail-drinker; burlesque-lover; foodie; experiments; cocktails; sex-nerd; friends-with-benefits; fwb; sexy-dates
nerd!; cuddles; kinky
Strong femme seeks femme women and masculine men; Sailor; surfer; hiker; Singer; Sexual; Spanko; Theatre lover; NOT sports;
kinky!!; switch seeks dominant;
not smoker; kinky; poly seeking poly; geek seeking geeks; nerd seeking nerds;
not asexual
dancer!; nerd; programmer; cuddler
kinky!!!; agender!; radical!; femme!; feminist!; earnest; masochist seeks sadist!!; bottom seeks top!!; sub seeks dom; seeking not sub; seeking not submissive; submissive seeks dominant; nerd; reader; creative; not asexual;
asexual
Geek; bear-cub seeks bear; switch seeks daddy
geek
pagan
kinky!; sub seeks dom; gamer
kinky; opinionated; passionate; andro; musician seeks similar
kinky; nerd; androgynous!
kinky; sensual; not smoker
kinky!!!; top seeks bottom; dom seeks sub; nerd
seeks andro; geek!; submissive seeks not sadist; not asshole
hot; sexy; happy;
hot seeks naughty; smarter!!!!!; not mean!
bear seeks lawyer; not boring!
Not smoker; Light-drinker; Smart!; Parent; Kind!; Funny!
tall; androgyny; bisexual; kinky; switch; nerd; gamer; programmer; science!; foodie; not asexual; not monogamy-friendly!!!!!; seeks one-night-stand
nerd; kinky
not smoker!!!; cuddly; nerd; not asexual; dancer; high-sex-drive
kinky femme seeks queer!! nerds for love!! and long term relationship; not asexual
monogamy-friendly; musician; programmer; geek; cuddler
kinky; submissive seeks switch; nerd; geek; queer
not smoker!!!!
not smoker; not asexual; cat person; switch; sub; dom; geek seeks scientist
nerd non-smoker gourmet swinger cis male seeks non-smoker gourmet swinger cis female
nerd; not smoker
feminist!!; anti-racist!!; anti-oppression!!; fire-spinner; hooper; dancer; mountain-climber; storm-chaser; cook; masochist seeks sadist!!; seeks not dominant!!; artist; writer; reader; dreamer; nerd; science-nerd; astronomy-nerd; bicyclist; nature-worshiper; riot-grrrl
artist; dancer
not smoker; kinky!!; submissive seeks dominant; seeks sadist!!
Nerd; scientist!; feminist!; gamer; programmer; loves music; loves animals
Genderfluid switch; kinkster slut witch; eeking advanced communicators; interested in consensual reasonable madness and romance; adventure!!; music!!
not smoker; kinky; oral; daddy seeks daughter; married; parent; pervert
"""
        cases = cases.split( "\n" )
        words = {}

        for c in cases:
            tr5 = TextResponse( c )

            if not tr5.valid_entry:
                print( "\n" )
                tr5.print_table()
            for wr in tr5.identities().values():
                w = wr.word
                dd = words.get( w, [0,0,0,0] )
                if wr.notFlag:
                    dd[1] += 1
                else:
                    dd[0] += 1
                words[w] = dd
            for wr in tr5.seeks().values():
                w = wr.word
                dd = words.get( w, [0,0,0,0] )
                dd[2 + wr.notFlag] += 1
                words[w] = dd

        print "\n\n\nList of Words:"
        print "Is\tIsNot\tSeek\tSeekNot\tWord\n"
        for (w, cnt) in words.iteritems():
            print "%d\t%d\t%d\t%d\t%s" % ( cnt[0], cnt[1], cnt[2], cnt[3], w )





if __name__ == "__main__":
        print "\nSimple test"
        tr1 = TextResponse( "dog" )
        tr2 = TextResponse( "dog" )
        print "quality: %s -> %s = %s" % ( tr1, tr2, tr1.match_quality( tr2 ) )
        print "quality: %s -> %s = %s" % ( tr2, tr1, tr2.match_quality( tr1 ) )

        print "\nSeek test"
        tr3 = TextResponse( "cat seeks dog" )
        tr3.print_table()

        tr4 = TextResponse( "dog" )
        tr4.print_table()


        print "%s -> %s = %s" % ( tr3, tr4, tr3.match_quality( tr4 ) )
        print "%s -> %s = %s" % ( tr3, tr4, tr3.match_quality( tr4 ) )

        print "\n**\n** Text Response Tables"

        print( "\n" )
        tr5 = TextResponse( "hot-dog!" )
        tr5.print_table()

        print( "\n" )
        tr5 = TextResponse( "dog seeks cat!!!" )
        tr5.print_table()

        print( "\n" )
        tr5 = TextResponse( "a dog!" )
        tr5.print_table()

        print( "\n" )
        tr5 = TextResponse( "dog needs cat!!!" )
        tr5.print_table()

        print( "\n" )
        tr6 = TextResponse( "I am a smoker" )
        tr6.print_table()

        print( "\n" )
        tr6 = TextResponse( "i'm smoker" )
        tr6.print_table()

        print( "\n" )
        tr6 = TextResponse( "I am a non smoker" )
        tr6.print_table()

        print( "\n" )
        tr6 = TextResponse( "I am a smoker" )
        tr6.print_table()

        print( "\n" )
        tr6 = TextResponse( "I'm not a smoker" )
        tr6.print_table()
        import ipdb;

        ipdb.set_trace()

        print( "\n" )
        tr6 = TextResponse( "I am a smoker seeking dogs!" )
        tr6.print_table()


        print "\n**\n** Text Response Tables"
        print( "\n" )
        tr6 = TextResponse( "I am an igloo seeking a duck!" )
        tr6.print_table()


        print "\n**\n** Crazy test"
        tr1 = TextResponse( "cat seeks dog, needs cow, needs not goat, small, not grey" )
        tr2 = TextResponse( "grey\ncow\nnot goat!" )
        print "%s -> %s = %s" % ( tr1, tr2, tr1.match_quality( tr2 ) )
        print "%s -> %s = %s" % ( tr2, tr1, tr2.match_quality( tr1 ) )
        tr1.print_table()
        tr2.print_table()

        print "\n**\n** Double word trick test"
        tr5 = TextResponse( "really tall" )
        print "\n"
        tr5.print_table()

        tr5 = TextResponse( "not really tall" )
        print "\n"
        tr5.print_table()

        tr5 = TextResponse( "really tall!!!" )
        print "\n"
        tr5.print_table()

        print "\n**\n** hypens and underscores test"
        tr5 = TextResponse( "really_tall seeks really_short" )
        print "\n"
        tr5.print_table()

        tr5 = TextResponse( "not really-tall seeks a small-pig" )
        print "\n"
        tr5.print_table()

        tr5 = TextResponse( "really_tall!!!" )
        print "\n"
        tr5.print_table()


        tr5 = TextResponse( "Monogamy!!!; educator seeks educator!!; switch!; non-bdsm; femme seeks femme; femme seeks man; educator seeks nerd; fat-positive; extrovert seeks ")
        tr5.print_table()
        
        tr5 = TextResponse( "non-bdsm; extrovert seeks ")
        tr5.print_table()
        
        tr5 = TextResponse( "non-bdsm; extrovert", "dog, cat, not pig" )
        tr5.print_table()
        
        tr5 = TextResponse( "non-bdsm; extrovert", "", verbose=True )
        tr5.print_table()

        tr5 = TextResponse( "non-bdsm; extrovert", "dog seeks cat; hamster", verbose=True )
        tr5.print_table()




