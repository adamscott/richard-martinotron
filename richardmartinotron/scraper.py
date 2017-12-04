import re
import requests

from time import sleep
from lxml import html
from html import unescape
from multiprocessing import Pool

from .database import connection

def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

class Scraper:
    def __init__(self):
        self.urls = []
        self.db_table_name = ''

    def check_exists(self, url):
        cursor = connection.cursor()
        cursor.execute("""
            SELECT title FROM {} WHERE 
            url = ?;
        """.format(self.db_table_name), (url,))
        return bool(cursor.fetchone())

    def start_singleprocess(self):
        self.create_db()
        for url in self.urls:
            if not self.check_exists(url):
                result = self.load_article(url)
                self.insert_db(**result)
                connection.commit()

    def start_multiprocess(self):
        self.create_db()
        with Pool(5) as p:
            urls_chunks = chunks(list(filter(lambda x: not self.check_exists(x), self.urls)), 10)
            for urls_chunk in urls_chunks:
                results = p.map(self.load_article, urls_chunk)
                for result in filter(lambda x: x is not None, results):
                    self.insert_db(**result)
                connection.commit()

    def load_article(self, url):
        raise NotImplementedError

    def create_db(self):
        raise NotImplementedError

    def insert_db(self, **kwargs):
        raise NotImplementedError


class JournalDeMontreal(Scraper):
    URL_LIST_PATH = 'data/url/jm.txt'
    TABLE_NAME = 'journal_montréal'

    def __init__(self):
        self.urls = []
        with open(JournalDeMontreal.URL_LIST_PATH) as f:
            for line in f:
                self.urls.append(line.rstrip())
        self.db_table_name = JournalDeMontreal.TABLE_NAME

    def load_article(self, url):
        m = re.search(r'journaldemontreal\.com\/(\d{4})\/(\d{2})\/(\d{2})', url)
        date = "{}-{}-{}".format(m.group(1), m.group(2), m.group(3))
        page = requests.get(url)
        sleep(0.25)
        print("Loading \"{}\" ({}): {}".format(url, date, page.status_code))
        if page.status_code == 200:
            tree = html.fromstring(page.content)

            strapline_contents = tree.xpath(
                '//article[@class="article-container"]//div[@class="strapline"]'
            )
            title_contents = tree.xpath(
                '//article[@class="article-container"]//div[contains(@class, "title-groupe")]/h1'
            )
            tagline_contents = tree.xpath(
                '//article[@class="article-container"]//div[contains(@class, "title-groupe")]/h3[@class="exergue-inf"]'
            )
            text_contents = tree.xpath(
                '//article[@class="article-container"]//div[@class="article-main-txt"]'
            )[0].xpath(
                './p'
                '|'
                './/div[not(contains(@class, "wp-comment-body") or contains(@class, "espace_210"))]/p'
                '|'
                './/div[not(contains(@class, "wp-comment-body")) and string-length(. > 0) and '
                'not(./*[not(name()="em") or not(name()="i") or not(name()="b") or not(name()="br")])]'
                '|'
                './/hr'
                '|'
                './div[@class="photo-inline"]'
            )

            if url == "http://www.journaldemontreal.com/2014/08/23/le-ice-bucket-challenge":
                strapline_contents = None
                strapline = "POUR ou CONTRE: Le « Ice Bucket Challenge » ?"

                title_contents = tree.xpath(
                    '//article[@class="article-container"]//div[@class="article-main-txt"]/div[@class="espace_210"]'
                    '/div[@class="espace"]/descendant::div[@class="espace_info"][1]/div[@class="titre2"]'
                )

                text_contents = tree.xpath(
                    '//article[@class="article-container"]//div[@class="article-main-txt"]/div[@class="espace_210"]'
                    '/div[@class="espace"]/descendant::div[@class="espace_info"][1]/div[@class="texte"]'
                )[0].xpath(
                    './p'
                    '|'
                    './div[@class="sous_titre"]'
                )

            image_contents = tree.xpath(
                '//article[@class="article-container"]//div[@class="article-main-image"]//'
                'picture/source/@srcset')
            image_credit_contents = tree.xpath(
                '//article[@class="article-container"]//div[@class="article-main-image"]//'
                'div[@class="image-information"]//span[@class="credit_photo"]')
            image_legend_contents = tree.xpath(
                '//article[@class="article-container"]//div[@class="article-main-image"]//'
                'div[@class="image-information"]//span[@class="bas_de_vignette"]')

            image = None
            credit = None
            legend = None

            if image_contents:
                image_url_pattern = re.compile(r', *\n +(http://.+) 2x')
                image_url = image_url_pattern.search(image_contents[0]).group(1)
                image = image_url

                if image_credit_contents:
                    credit = strip_and_clean(image_credit_contents[0])

                if image_legend_contents:
                    legend = strip_and_clean(image_legend_contents[0])

            if strapline_contents:
                strapline = strip_and_clean(strapline_contents[0])
            else:
                strapline = None

            if title_contents:
                title = strip_and_clean(title_contents[0])
            else:
                title = None

            if tagline_contents:
                tagline = strip_and_clean(tagline_contents[0])
            else:
                tagline = None

            text = []
            for t in text_contents:
                if t.tag == "p":
                    for p in get_clean_paragraphs(t):
                        text.append(("p", p))
                elif t.tag == "div":
                    #print(t.get('class'))
                    if t.get('class') is None:
                        for p in get_clean_paragraphs(t):
                            text.append(("p", p))
                    elif "sous_titre" in iter(t.classes):
                        print(t)
                        for p in get_clean_paragraphs(t):
                            text.append(("p", p))
                    elif "photo-inline" in iter(t.classes):
                        picture_contents = t.xpath('.//div[@class="espacePhoto"]//picture/source/@srcset')
                        if picture_contents:
                            picture_url_pattern = re.compile(r', *\n +(http://.+) 2x')
                            picture_url = picture_url_pattern.search(picture_contents[0]).group(1)
                        else:
                            picture_url = ""

                        picture_credit_contents = t.xpath('.//div[@class="credit"]')
                        if picture_credit_contents:
                            picture_credit = strip_and_clean(picture_credit_contents[0])
                        else:
                            picture_credit = ""

                        if picture_url:
                            text.append((
                                "figure",
                                """
                                <img src="{}" alt="" /><figcaption>{}</figcaption>
                                """.strip().format(
                                    picture_url,
                                    picture_credit
                                )
                            ))
                elif t.tag == "hr":
                    text.append(("hr", None))

            # text_string = "\n\n".join(
            #     ["<{0}>{1}</{0}>".format(t[0], t[1]) for t in filter(lambda x: len(x[1]) > 0, text)]
            # )

            formatted_strings = []
            for t in text:
                if t[0] == "hr":
                    formatted_strings.append("<hr>")
                else:
                    if len(t[1]) > 0:
                        html_frag = html.fromstring(t[1])
                        if len(html_frag.text_content()) > 0:
                            formatted_strings.append("<{0}>{1}</{0}>".format(t[0], t[1]))

            text_string = "\n\n".join(formatted_strings)

            return {
                'date': date,
                'strapline': strapline,
                'title': title,
                'tagline': tagline,
                'content': text_string,
                'url': url,
                'image': image,
                'credit': credit,
                'legend': legend
            }

    def create_db(self):
        cursor = connection.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master WHERE 
            type='table' AND name=?;
        """, (self.db_table_name, ))
        exists = bool(cursor.fetchone())
        if not exists:
            cursor.execute("""
                CREATE TABLE journal_montréal (
                    date text, 
                    strapline text, 
                    title text, 
                    tagline text, 
                    content text, 
                    url text, 
                    image_url text, 
                    image_credit text, 
                    image_legend text
                );
            """)
        connection.commit()

    def insert_db(self, **kwargs):
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO journal_montréal
            (date, strapline, title, tagline, content, url, image_url, image_credit, image_legend) VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (kwargs['date'],
              kwargs['strapline'],
              kwargs['title'],
              kwargs['tagline'],
              kwargs['content'],
              kwargs['url'],
              kwargs['image'],
              kwargs['credit'],
              kwargs['legend']))


def get_clean_paragraphs(element):
    if element is not None:
        clean = strip_and_clean(element)
        split_text = re.sub(r' *<br>(\W+<br>)+', '</p>\n\n<p>', clean.replace("<br>", "<br>\n"))
        if len(split_text) > 0:
            tree = html.fromstring("<div><p>{}</p></div>".format(split_text))
            paragraph_contents = tree.xpath('./p')
            paragraphs = []
            for p in paragraph_contents:
                clean = strip_and_clean(p)
                if len(clean) > 0:
                    paragraphs.append(clean)
            return paragraphs
    return []


def strip_and_clean(element):
    if element is not None:
        if element.text is not None and len(element.text.strip()) > 0:
            return unescape(element.text.strip()) + \
                unescape(b''.join(html.tostring(e) for e in element).decode('utf-8').strip())
        else:
            return unescape(b''.join(html.tostring(e) for e in element).decode('utf-8').strip())
