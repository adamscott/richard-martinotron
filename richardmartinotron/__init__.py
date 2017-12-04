import signal
import sys

from .database import connection
from .scraper import JournalDeMontreal as Scraper_JournalDeMontreal
from .analyser import JournalDeMontreal as Analyser_JournalDeMontreal

scraper_journal = Scraper_JournalDeMontreal()
analyser_journal = Analyser_JournalDeMontreal()


def init_signals():
    signal.signal(signal.SIGINT, signal_handler)


def signal_handler(signum, frame):
    if signum == signal.SIGINT.value:
        connection.close()
        sys.exit(0)


def _main():
    init_signals()
    #scraper_journal.start_multiprocess()
    #scraper_journal.start_singleprocess()
    #analyser_journal.count_words()
    analyser_journal.count_exclamation_marks()
    #article = scraper_journal.load_article("http://www.journaldemontreal.com/2014/07/26/plaignez-vous")
    #article = scraper_journal.load_article("http://www.journaldemontreal.com/2012/05/10/charest-encore-en-controle")
    #article = scraper_journal.load_article("http://www.journaldemontreal.com/2015/01/13/charlie-mensonges-et-lieux-communs")
    #article = scraper_journal.load_article("http://www.journaldemontreal.com/2010/06/23/frankenstein-sest-echappe")
    #article = scraper_journal.load_article("http://www.journaldemontreal.com/2009/12/08/les-dogmes-de-la-religion-verte")
    #print(article)
    connection.close()


if __file__ == "__main__":
    _main()
