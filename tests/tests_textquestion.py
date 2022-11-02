
from unittest import TestCase
from register.textquestion import TextResponse


class TextTestCase(TestCase):


    def test_can_calculate_matches(self):
        tr1 = TextResponse("cat seeks dog, needs cow, needs not goat, small, not grey")
        tr2 = TextResponse("grey, cow, not goat")
        match = tr1.match_quality(tr2)
        self.assertEqual(match, -200 + 6)
        match2 = tr2.match_quality(tr1)
        self.assertEqual(match2, -200)


    def test_not_word(self):
        """
        'not' works in textquestion
        """

        tr5 = TextResponse( "not tall" )
        tr6 = TextResponse( "pig" )
        self.assertEqual( tr5.match_quality( tr6 ), 0 )
        self.assertEqual( tr6.match_quality( tr5 ), 0 )

        tr5 = TextResponse( "not tall" )
        tr6 = TextResponse( "seeks not tall" )
        self.assertEqual( tr5.match_quality( tr6 ), 0 )
        self.assertEqual( tr6.match_quality( tr5 ), 1 )

        tr5 = TextResponse( "tall" )
        tr6 = TextResponse( "seeks not tall!" )
        self.assertEqual( tr5.match_quality( tr6 ), 0 )
        self.assertEqual( tr6.match_quality( tr5 ), -300 )

        tr2 = TextResponse( "grey\ncow\nnot goat!" )
        tr3 = TextResponse( "not goat" )
        self.assertEqual( tr2.match_quality( tr3 ), 2 )

    def test_double_not_word(self):
        """
        'not' works in double textquestion
        """

        tr5 = TextResponse( "not tall", "not tall" )
        tr6 = TextResponse( "pig", "pig" )
        self.assertEqual( tr5.match_quality( tr6 ), 0 )
        self.assertEqual( tr6.match_quality( tr5 ), 0 )

        tr5 = TextResponse( "not tall", "not tall" )
        tr6 = TextResponse( "", "seeks not tall" )
        self.assertEqual( tr5.match_quality( tr6 ), 0 )
        self.assertEqual( tr6.match_quality( tr5 ), 1 )

        tr5 = TextResponse( "tall", "tall" )
        tr6 = TextResponse( "", "not tall!" )
        self.assertEqual( tr5.match_quality( tr6 ), 0 )
        self.assertEqual( tr6.match_quality( tr5 ), -300 )

        tr2 = TextResponse( "grey\ncow\nnot goat!" )
        tr3 = TextResponse( "not goat" )
        tr2.print_table()
        tr3.print_table()

        tr2 = TextResponse( "grey,cow,not goat!", "grey\ncow\nnot goat!")
        tr3 = TextResponse( "not goat", "not goat" )
        print "tr2:"
        print tr2.comments
        tr2.print_table()
        tr3.print_table()
        print "end tables"
        self.assertEqual( tr2.match_quality( tr3 ), 2 )


    def test_passion(self):
        """
        Passion markers work
        """
        tr5 = TextResponse( "needs a cow; seeks a pig!!" )
        tr6 = TextResponse( "cow!!!; a pig" )
        self.assertEqual( tr5.match_quality( tr6 ), 6 )
        self.assertEqual( tr6.match_quality( tr5 ), 0 )

        # "\nPassion hate test"
        tr3 = TextResponse( "goat" )
        tr5 = TextResponse( "needs not goat!" )
        self.assertEqual( tr5.match_quality( tr3 ), -500 )

        # "\nPassion hate test"
        tr3 = TextResponse( "not goat" )
        tr5 = TextResponse( "needs goat!!!!!!" )
        self.assertEqual( tr5.match_quality( tr3 ), -1000 )


    def test_double_passion(self):
        """
        Passion markers work
        """
        tr5 = TextResponse( "needs a cow; seeks a pig!!" )
        tr5.print_table()
        tr5 = TextResponse( "", "needs a cow; seeks a pig!!" )
        tr5.print_table()

        print "---"
        tr6 = TextResponse( "cow!!!; a pig" )
        tr6.print_table()
        tr6 = TextResponse( "i'm cow!!!; a pig", "a pig, cow!!!" )
        tr6.print_table()

        self.assertEqual( tr5.match_quality( tr6 ), 6 )
        self.assertEqual( tr6.match_quality( tr5 ), 0 )

        # "\nPassion hate test"
        tr3 = TextResponse( "goat", "goat" )
        tr5 = TextResponse( "", "needs not goat!" )
        self.assertEqual( tr5.match_quality( tr3 ), -500 )

        # "\nPassion hate test"
        tr3 = TextResponse( "not goat", "not goat" )
        tr5 = TextResponse( "", "needs goat!!!!!!" )
        self.assertEqual( tr5.match_quality( tr3 ), -1000 )



    def test_translation(self):
        tdict = { 'tallish':'tall', 'piggish':'pig', 'cat-hater':'dog'}
        tr1 = TextResponse( "tallish seeks piggish; cat-hater" )
        tr2 = TextResponse( "pig seeks tall!!; not dog" )
        tr3 = TextResponse( "happy; i am dog" )

        self.assertEqual( tr1.match_quality( tr2 ), 0 )
        self.assertEqual( tr2.match_quality( tr1 ), 0 )

        # Translate!
        tr1.translate_words( tdict )
        self.assertEqual( tr1.match_quality( tr2 ), -200 + 1 )
        self.assertEqual( tr1.match_quality( tr3 ), 1 )
        self.assertEqual( tr2.match_quality( tr1 ), -200 + 3 )

        # Translate second person!
        tr2.translate_words( tdict )
        self.assertEqual( tr1.match_quality( tr2 ), -200 + 1 )
        self.assertEqual( tr2.match_quality( tr1 ), 3 - 200 )


    def test_double_translation(self):


        tdict = { 'tallish':'tall', 'piggish':'pig', 'cat-hater':'dog'}
        tr1 = TextResponse( "tallish seeks piggish; cat-hater" )
        tr2 = TextResponse( "pig seeks tall!!; not dog" )
        tr3 = TextResponse( "happy; i am dog" )

        self.assertEqual( tr1.match_quality( tr2 ), 0 )
        self.assertEqual( tr2.match_quality( tr1 ), 0 )

        # Translate!
        print tr1
        tr1.print_table()
        tr1.translate_words( tdict )
        tr1.print_table()
        print tr3.print_table()

        print tr1
        print "----"
        tr2 = TextResponse( "pig seeks tall!!; not dog" )
        self.assertEqual( tr1.match_quality( tr2 ), -200 + 1 )


        tdict = { 'tallish':'tall', 'piggish':'pig', 'cat-hater':'dog'}
        tr1 = TextResponse( "tallish; cat-hater", "piggish, cat-hater" )
        tr2 = TextResponse( "pig, not dog", "tall!!, not dog" )
        tr3 = TextResponse( "happy; i am dog", "happy" )

        self.assertEqual( tr1.match_quality( tr2 ), 0 )
        self.assertEqual( tr2.match_quality( tr1 ), 0 )

        # Translate!
        print tr1
        tr1.print_table()

        tr1.translate_words( tdict )
        tr1.print_table()

        print tr1
        print tr2
        print tr3
        print tdict
        print tr3.print_table()
        print tr3.comments

        self.assertEqual( tr1.match_quality( tr2 ), -200 + 1 )
        self.assertEqual( tr1.match_quality( tr3 ), 1 )
        self.assertEqual( tr2.match_quality( tr1 ), -200 + 3 )

        # Translate second person!
        tr2.translate_words( tdict )
        self.assertEqual( tr1.match_quality( tr2 ), -200 + 1 )
        self.assertEqual( tr2.match_quality( tr1 ), 3 - 200 )



    def test_match_scoring(self):
        tr1 = TextResponse( "dog" )
        tr2 = TextResponse( "dog" )
        self.assertEqual( tr1.match_quality( tr2 ), 1 )

        tr3 = TextResponse( "cat seeks dog" )
        tr4 = TextResponse( "dog" )
        self.assertEqual( tr3.match_quality( tr4 ), 1 )
        self.assertEqual( tr4.match_quality( tr3 ), 0 )


    def test_table_lists(self):
        tr = TextResponse( "hot-dog!" )
        self.assertEqual( tr.words(), set( ["hot-dog"] ) )

        tr = TextResponse( "not hot-dog!" )
        self.assertEqual( tr.words(), set( ["hot-dog"] ) )

        tr = TextResponse( "seeks hot-dog!" )
        self.assertEqual( tr.words(), set( ["hot-dog"] ) )

        tr = TextResponse( "non-hot-dog!" )
        self.assertEqual( tr.words(), set( ["hot-dog"] ) )


    def test_broken_catches(self):
        tr = TextResponse( "hottie seeks" )
        self.assertFalse( tr.valid_entry )

        tr = TextResponse( "big bad hottie seeks small dark duck" )
        self.assertFalse( tr.valid_entry )

        tr = TextResponse( "big ;  duck seeks ;  hamburger" )
        self.assertFalse( tr.valid_entry )
        self.assertEqual( tr.validation_error, "duck seeks" )


    def test_two_word(self):
        tr5 = TextResponse( "not really tall" )
        self.assertEqual( tr5.words(), set( ["really-tall"] ) )

        tr5 = TextResponse( "really tall!!!" )
        self.assertEqual( tr5.words(), set( ["really-tall"] ) )


    def test_underscores(self):
        tr5 = TextResponse( "really_tall seeks really_short" )
        self.assertEqual( tr5.words(), set( ["really-tall", "really-short"] ) )

        tr5 = TextResponse( "not really-tall seeks a small-pig" )
        self.assertEqual( tr5.words(), set( ["really-tall", "small-pig"] ) )


        tr5 = TextResponse( "really_tall!!!" )
        self.assertEqual( tr5.words(), set( ["really-tall"] ) )

    def test_chopup(self):
        tr5 = TextResponse( "pig\ndog\ncow\n")
        self.assertEqual( tr5.comments, "pig; dog; cow" )

        tr5 = TextResponse( "    \n\n")
        self.assertEqual( tr5.comments, "" )

        tr5 = TextResponse( "pig")
        self.assertEqual( tr5.comments, "pig" )



    def test_emptystring(self):
        tr5 = TextResponse( "" )
        self.assertEqual( tr5.words(), set( [] ) )

        tr5 = TextResponse( "    \n\n\n  " )
        self.assertEqual( tr5.words(), set( [] ) )

        tr5 = TextResponse( " " )
        self.assertEqual( tr5.words(), set( [] ) )


    def test_double_underscores(self):
        tr5 = TextResponse( "really_tall", "really_short" )
        self.assertEqual( tr5.words(), set( ["really-tall", "really-short"] ) )

        tr5 = TextResponse( "not really-tall", "a small-pig" )
        self.assertEqual( tr5.words(), set( ["really-tall", "small-pig"] ) )


        tr5 = TextResponse( "really_tall!!!", "" )
        self.assertEqual( tr5.words(), set( ["really-tall"] ) )


    def test_double_emptystring(self):
        tr5 = TextResponse( "", "" )
        self.assertEqual( tr5.words(), set( [] ) )

        tr5 = TextResponse( "    \n\n\n  ", "    ,   ")
        self.assertEqual( tr5.words(), set( [] ) )

        tr5 = TextResponse( " ", "" )
        self.assertEqual( tr5.words(), set( [] ) )
