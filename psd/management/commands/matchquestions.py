from register.matchq_models import MatchQuestion
from django_docopt_command import DocOptCommand
from .checkorganization import checkOrganization


def clearMatchQuestion(question_code, verbose=True):
    ques = MatchQuestion.objects.filter(question_code=question_code)
    if len(ques) > 0:
        print("Going to remove old Match Question '%s'" % (question_code,))
        for q in ques:
            q.delete()


def setupMatchQuestions(do_quest=None, verbose=True, trigender=False):
    """
    Make the match questions (default questions)
    :param do_quest: Name of specific question to build.
    :param verbose:
    :param trigender: Do the simpler gender question vs. the many level one.
    """

    if do_quest is None or "location" in do_quest:
        clearMatchQuestion("location", verbose)
        loc = MatchQuestion(question="Location")
        loc.ask_about_seek = False
        loc.checkbox = True
        loc.hard_match = False
        loc.strict_subset_match = False
        loc.allow_preferences = False
        loc.explanation = "Locations willing to meet folks."
        loc.internal_comment = "Warning: Do not select as extra question.  Also, most flags will not impact system."
        loc.question_code = "location"
        loc.save()
        loc.matchchoice_set.create(choice="Somewhere Else", choice_code="SE")
        loc.matchchoice_set.create(choice="Unknown", choice_code="UK")
        loc.save()

    if do_quest is None or "gender" in do_quest:
        clearMatchQuestion("gender")
        gen = MatchQuestion(question="Gender")
        gen.ask_about_seek = True
        gen.checkbox = True
        gen.hard_match = True
        gen.strict_subset_match = True
        gen.allow_preferences = True
        gen.question_code = "gender"
        gen.explanation = "Gender/Identity core matching question."
        gen.internal_comment = "Gender default question.  Do not select as extra question.  Also, most flags will not impact system."
        gen.save()
        if trigender:
            gen.matchchoice_set.create(choice="women", choice_code="W")
            gen.matchchoice_set.create(choice="men", choice_code="M")
        gen.matchchoice_set.create(choice="trans women", choice_code="TW")
        gen.matchchoice_set.create(choice="trans men", choice_code="TM")
        gen.matchchoice_set.create(choice="cis women", choice_code="CW")
        gen.matchchoice_set.create(choice="cis men", choice_code="CM")
        gen.matchchoice_set.create(choice="genderqueer, genderfluid, or gender bending people", choice_code="GQ")
        #gen.matchchoice_set.create(choice="butch people", choice_code="BU")
        #gen.matchchoice_set.create(choice="androgynous people", choice_code="AN")
        #gen.matchchoice_set.create(choice="femme people", choice_code="FE")
        #gen.matchchoice_set.create(choice="queer people", choice_code="Q")
        gen.matchchoice_set.create(choice="people who prefer to not be categorized or cannot be categorized by the above", choice_code="NA")
        gen.save()

    if do_quest is None or "kinky" in do_quest:
        clearMatchQuestion("kinky")
        kink = MatchQuestion(question="the Kinky Question")
        kink.question_code = "kinky"
        kink.explanation = "Do you identify as kinky and are you wanting to date kinky people?"
        kink.ask_about_seek = True
        kink.internal_comment = "Whether folks are kinky or not."
        kink.checkbox = True
        kink.is_YN = True
        kink.hard_match = False
        kink.include_name = True
        kink.hard_match = True
        kink.strict_subset_match = False

        kink.save()
        kink.matchchoice_set.create(choice="I strongly prefer dates with kinky people", choice_code="Y")
        kink.matchchoice_set.create(choice="I strongly prefer dates with non-kinky people", choice_code="N")
        kink.matchchoice_set.create(choice="I have no strong preference", choice_code="EI")
        kink.save()

    if do_quest is None or "primary" in do_quest:
        clearMatchQuestion("primary")
        kink = MatchQuestion(question="the Primary Question", question_code="primary", ask_about_seek=True)
        kink.explanation = "I am not currently in a primary relationship, but potentially interested in one."
        kink.checkbox = True
        kink.is_YN = True
        kink.hard_match = False
        kink.include_name = True
        kink.hard_match = True
        kink.strict_subset_match = False
        kink.save()
        kink.matchchoice_set.create(choice="I strongly prefer being matched with those open to forming a primary relationship", choice_code="Y")
        kink.matchchoice_set.create(choice="I strongly prefer not being matched with those looking for primary relationships", choice_code="N")
        kink.matchchoice_set.create(choice="I have no strong preference", choice_code="EI")
        kink.save()
        
    if do_quest is None or "spanish" in do_quest:
        clearMatchQuestion("spanish")
        kink = MatchQuestion(question="the Spanish Question", question_code="spanish", ask_about_seek=True)
        kink.explanation = "Do you speak Spanish (well enough to speed date)?"
        kink.checkbox = True
        kink.is_YN = True
        kink.hard_match = False
        kink.include_name = True
        kink.hard_match = True
        kink.strict_subset_match = False
        kink.seek_no_allowed = False
        kink.save()
        kink.matchchoice_set.create(choice="I strongly prefer being matched with those who speak Spanish.", choice_code="Y")
        kink.matchchoice_set.create(choice="Invalid response", choice_code="N")
        kink.matchchoice_set.create(choice="I have no strong preference", choice_code="EI")
        kink.save()


    if do_quest is None or "identity" in do_quest:
        clearMatchQuestion("identity")
        if verbose:
            print "Making the identity question"
        petsQ = MatchQuestion(question="the Identity Question", question_code="identity",ask_about_seek=True)
        petsQ.checkbox = True
        petsQ.hard_match = False
        petsQ.explanation = "What, if anything, do you prefer in your matches, and how do you identify?  (This question is optional and these are preferences, not hard constraints.)"
        petsQ.internal_comment = "For soft-match tweaking on identity."
        petsQ.strict_subset_match = False
        petsQ.question_code = "identity"
        petsQ.save()
        petsQ.matchchoice_set.create(choice="butch people", choice_code="BU")
        petsQ.matchchoice_set.create(choice="femme people", choice_code="FE")
        petsQ.matchchoice_set.create(choice="androgynous people", choice_code="AN")
        petsQ.matchchoice_set.create(choice="queer people", choice_code="QU")
        petsQ.save()

    if do_quest is None or "asexual" in do_quest:
        clearMatchQuestion("asexual")
        if verbose:
            print "Making the asexual question"
        petsQ = MatchQuestion(question="the Asexual Question", ask_about_seek=True)
        petsQ.checkbox = True
        petsQ.is_YN = True
        petsQ.explanation = "I prefer to have asexual relationships."
        petsQ.include_name = True
        petsQ.hard_match = True
        petsQ.internal_comment = "Augmented boston form."
        petsQ.strict_subset_match = False
        petsQ.question_code = "asexual"
        petsQ.save()
        petsQ.matchchoice_set.create(choice="I strongly prefer being matched with asexual people", choice_code="Y")
        petsQ.matchchoice_set.create(choice="I strongly prefer not being matched with asexual people", choice_code="N")
        petsQ.matchchoice_set.create(choice="I have no strong preference", choice_code="EI")
        petsQ.save()

    if do_quest is None or "monog" in do_quest:
        clearMatchQuestion("monog")
        if verbose:
            print "Making the monogomy question"
        petsQ = MatchQuestion(question="the Monogomy Question", question_code="monog",ask_about_seek=True)
        petsQ.checkbox = True
        petsQ.is_YN = True
        petsQ.explanation = "I prefer to have a relationship with only one person at a time (i.e. am monogamous)."
        petsQ.include_name = True
        petsQ.hard_match = True
        petsQ.internal_comment = "For USD/Rainbow Speed Dating."
        petsQ.strict_subset_match = False
        petsQ.question_code = "monog"
        petsQ.save()
        petsQ.matchchoice_set.create(choice="I strongly prefer those who can enjoy monogamous relationships", choice_code="Y")
        petsQ.matchchoice_set.create(choice="I strongly prefer those who do not enjoy monogamous relationships", choice_code="N")
        petsQ.matchchoice_set.create(choice="I have no strong preference", choice_code="EI")
        petsQ.save()

    if do_quest is None or "race" in do_quest:
        clearMatchQuestion("race")
        if verbose:
            print "Making the race question"
        petsQ = MatchQuestion(question="the PoC Affinity Question", question_code="race",ask_about_seek=False)
        petsQ.checkbox = True
        petsQ.is_YN = True
        petsQ.hard_match = False
        petsQ.yes_only = True
        petsQ.explanation = "I am a person of color who would prefer to be matched to other people of color."
        petsQ.include_name = True
        petsQ.internal_comment = "Equity question to help PoC match each other if so desired."
        petsQ.strict_subset_match = False
        petsQ.question_code = "race"
        petsQ.save()
        petsQ.matchchoice_set.create(choice="I would like to have dates with other PoC", choice_code="Y")
        petsQ.matchchoice_set.create(choice="I do not want to prioritize dates with other PoC", choice_code="N")
        petsQ.save()


    if do_quest is None or "tagconsent" in do_quest:
        clearMatchQuestion("tagconsent")
        if verbose:
            print "Making the text tag consent question"
        petsQ = MatchQuestion(question="the text consent question", question_code="tagconsent",ask_about_seek=False)
        petsQ.checkbox = True
        petsQ.is_YN = True
        petsQ.hard_match = False
        petsQ.explanation = "It is okay for my matches to see matching text."
        petsQ.include_name = True
        petsQ.internal_comment = "Consent for the free-text question."
        petsQ.strict_subset_match = False
        petsQ.save()
        petsQ.matchchoice_set.create(choice="It is okay for my matches to see matching free text.", choice_code="Y")
        petsQ.matchchoice_set.create(choice="It is not okay for my matches to see matching free text.", choice_code="N")
        petsQ.save()


    if not do_quest is None and "funk" in do_quest:
        clearMatchQuestion("funk")
        if verbose:
            print "Making the funkiness question"
        funkQ = MatchQuestion(question="the Funkiness Question", question_code="funk", ask_about_seek=True)
        funkQ.checkbox = True
        funkQ.explanation = "How funky are you?"
        funkQ.internal_comment = "Sample question"
        funkQ.question_code = "funk"
        funkQ.save()
        funkQ.matchchoice_set.create(choice="totally funky", choice_code="TF")
        funkQ.matchchoice_set.create(choice="kind of funky", choice_code="KF")
        funkQ.matchchoice_set.create(choice="not funky", choice_code="NF")
        funkQ.save()

    if not do_quest is None and "hot" in do_quest:
        clearMatchQuestion("hot")
        if verbose:
            print "Making the hotness question"
        hotQ = MatchQuestion(question="the Hotness Question", question_code="hot")
        hotQ.checkbox = False
        hotQ.explanation = "Are you hot?"
        hotQ.explanation = "Sample question"
        hotQ.question_code = "hot"
        hotQ.save()
        hotQ.matchchoice_set.create(choice="Yes", choice_code="Y")
        hotQ.matchchoice_set.create(choice="No", choice_code="N")
        hotQ.save()





class Command(DocOptCommand):
    docs = """Make MatchQuestions for Gender, Kinkiness, and Location so those combo boxes work right.
Also make Organization object for all Django sites for non-event links (if none found).
Note: Call without arguments when setting up a new database.
Can also add question names to reset those questions only.


Usage: matchquestions [<question_name>...]

Arguments:
    <question_name>   (optional) question name/s

Options:
    -h --help     Show this screen.
"""
    def handle_docopt(self, arguments):
        question_names = arguments['<question_name>']
        if not question_names:
            setupMatchQuestions()
            checkOrganization()
        else:
            setupMatchQuestions(set(question_names))
