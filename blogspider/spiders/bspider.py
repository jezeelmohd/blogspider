from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector
from scrapy.item import Item
import csv
from urlparse import urlparse
from items import BlogItem
import re
import nltk
from fuzzywuzzy import fuzz

class MySpider(CrawlSpider):

    name = 'craig'
    def __init__(self,csvfile='blogs2.csv'):
        self.csvfile=csvfile
        self.allowed_domains= self.GetAllowedDomains(csvfile)
        self.start_urls = self.GetStartUrls(csvfile)

        self.rules = (Rule(SgmlLinkExtractor(allow=('/[a-z0-9-]+-',),deny=('\?')),follow=True,callback='parse_item'),)

        super(MySpider, self).__init__()
    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)

        date=re.compile('\d+\/\d+\/\d+').findall(response.url)
        title=None
        if not date:
            date_xpath=' '.join(hxs.select('//span/text()').extract())
            date=re.compile('\w+.\d+..\d+').findall(date_xpath)
            date=date[0] if date else None

        def word_short(word):
            word_short=''.join([sl for sl in word.split() if len(sl)>3])
            return word_short

        slug=response.url.split('/')[-1]
        if slug=='':
            slug=response.url.split('/')[-2]
        else:
            slug=slug.rstrip('.html')

        slug_short=slug.lower().encode('ascii','ignore')
        slug_nonum=(''.join([i for i in word_short(' '.join(slug_short.split('-'))) if i.isalpha()])).lower()


        title_tag_dict={'a':'//h1','b':'//h2','c':'//h3','d':'//h1/a','e':'//h2/a','f':'//h3/a'}

        ar=hxs.select("//h1/text()").extract()
        br=hxs.select("//h2/text()").extract()
        cr=hxs.select("//h3/text()").extract()
        dr=hxs.select("//h1/a/text()").extract()
        er=hxs.select("//h2/a/text()").extract()
        fr=hxs.select("//h3/a/text()").extract()

        a=' '.join(ar).strip().lower().encode('ascii','ignore')
        b=' '.join(br).strip().lower().encode('ascii','ignore')
        c=' '.join(cr).strip().lower().encode('ascii','ignore')
        d=' '.join(dr).strip().lower().encode('ascii','ignore')
        e=' '.join(er).strip().lower().encode('ascii','ignore')
        f=' '.join(fr).strip().lower().encode('ascii','ignore')

        ar=ar[0] if ar else None
        br=br[0] if br else None
        cr=cr[0] if cr else None
        dr=dr[0] if dr else None
        er=er[0] if er else None
        fr=fr[0] if fr else None

        title_dict={'a':fuzz.partial_ratio(slug_short, a),
                    'b':fuzz.partial_ratio(slug_short, b),
                    'c':fuzz.partial_ratio(slug_short, c),
                    'd':fuzz.partial_ratio(slug_short, d),
                    'e':fuzz.partial_ratio(slug_short, e),
                    'f':fuzz.partial_ratio(slug_short, f),
                    }
        inverse_title_dict=dict((v,k) for k,v in title_dict.items())
        max_possible_ratio=max(title_dict.values())

        title_variable=inverse_title_dict[max_possible_ratio]
        title_xpath=title_tag_dict[title_variable]

        possible_title=eval(title_variable+'r')
        if possible_title:
            possible_title_short=(''.join([i for i in word_short(possible_title) if i.isalpha()])).replace('-','').lower()
            if slug_nonum in possible_title_short:
                title=possible_title
            else:
                title=None


        if title:
            post_text=''
            div_len=0
            post_xpaths=[title_xpath+"/following-sibling::div[1]",title_xpath+"/following-sibling::div[2]",title_xpath+"/following-sibling::div[3]"]

            for post_xpath in post_xpaths:
                div_html=hxs.select(post_xpath).extract()
                div_text=nltk.clean_html(' '.join(div_html))

                if len(div_text)>div_len:
                    if len(re.compile('\w+ \d+,.\d+').findall(div_html[0]))>10:
                        continue
                    else:
                        post_text=div_text
                        div_len=len(div_text)

            #if post is in upper /sibling div
            post_text2=''
            div_len=0
            post_xpaths2=[title_xpath+"/../following-sibling::div[1]",title_xpath+"/../following-sibling::div[2]",title_xpath+"/../following-sibling::div[3]"]

            post_div=''
            for post_xpath in post_xpaths2:
                div_html=hxs.select(post_xpath).extract()
                div_text=nltk.clean_html(' '.join(div_html))
                if len(div_text)>div_len:
                    if len(re.compile('\w+ \d+,.\d+').findall(div_html[0]))>10:
                        continue
                    else:
                        post_text2=div_text
                        div_len=len(div_text)

            if len(post_text2)>len(post_text):
                post_text=post_text2
            #if no post is found in page and post is in 2nd upper div then
            if not post_text:
                post_text=''
                div_len=0
                post_xpaths3=[title_xpath+"/../../following-sibling::div[1]",title_xpath+"/following-sibling::div[2]",title_xpath+"/following-sibling::div[3]"]

                for post_xpath in post_xpaths:
                    div_html=hxs.select(post_xpath).extract()
                    div_text=nltk.clean_html(' '.join(div_html))

                    if len(div_text)>div_len:
                        if len(re.compile('\w+ \d+,.\d+').findall(div_html[0]))>10:
                            continue
                        else:
                            post_text=div_text
                            div_len=len(div_text)

            title=self.ExtractAlphanumeric(title) if title else None
            text=self.ExtractAlphanumeric(post_text) if post_text else None
            date=date if date else None
            base_url=urlparse(response.url)


            item=BlogItem(base_url=base_url.netloc,post_url=response.url,post_date=date,post_title=title,post_text=text)
            yield item

    def ExtractAlphanumeric(self, InputString):
        from string import ascii_letters, digits
        return "".join([ch for ch in InputString if ch in (ascii_letters + digits +' '+'.')]).strip('  ')

    def GetAllowedDomains(self,outercsv):
        adomins=[]
        with open(outercsv, 'rb') as csvfile:
            blogs = csv.reader(csvfile, delimiter=',')
            for blog in blogs:
                for blo in blog:
                    bl=blo[:blo.find('.com')+4]
                    bl=bl[8:] if 'https' in bl else bl
                    bl=bl[7:] if 'http' in bl else bl
                    bl=bl[4:] if 'www' in bl else bl
                    adomins.append(bl)
                return adomins

    def GetStartUrls(self,outercsv):
        adomins=[]
        with open(outercsv, 'rb') as csvfile:
            blogs = csv.reader(csvfile, delimiter=',')
            for blog in blogs:
                for blo in blog:
                    if not 'www' in blo:
                        if 'http' in blo:
                            blo='http://www.'+blo[7:]
                        else:
                            blo='www.'+blo

                    blo=blo if 'http' in blo else 'http://'+blo
                    adomins.append(blo)

                return adomins
