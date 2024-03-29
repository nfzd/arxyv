import json
import os
import os.path
import re
import requests
import shutil
import subprocess
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from unidecode import unidecode


user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36'


def check_arxiv_key(key, verbose=False):
    if '.' not in key and key.count('.') == 1:
        raise ValueError('cannot interpret key: ' + key)

    sp = key.split('.')

    if not (len(sp[0]) == 4 and len(sp[1]) in [4, 5]):
        raise ValueError('cannot interpret key: ' + key)

    if not sp[0].isnumeric() and sp[1].isnumeric():
        raise ValueError('cannot interpret key: ' + key)

    if verbose:
        print('assuming key is arxiv key')

    url_base = 'https://arxiv.org'
    abs_url = url_base + '/abs/' + key
    dl_url = url_base + '/pdf/' + key

    return abs_url, dl_url


def check_url(url):
    if urlparse(url).netloc:
        return url

    url = 'https://' + url

    if urlparse(url).netloc:
        return url

    return None


def get(url, download_to=None):
    headers = {'user-agent': user_agent}

    if download_to is None:
        r = requests.get(url, headers=headers)
        r = r.text

    else:
        r = requests.get(url, headers=headers, allow_redirects=True)
        with open(download_to, 'wb') as f:
            f.write(r.content)

        # TODO: handle response

    return r


def get_meta_tag(soup, name_list, title, ind=0, max_len=None, raise_error=True):
    assert ind in [0, -1]

    for name in name_list:
        tag = soup.find_all('meta', {'name': name})

        if len(tag) > 0:
            break

        tag = soup.find_all('meta', {'property': name})

        if len(tag) > 0:
            break

    if len(tag) == 0:
        if not raise_error:
            return None

        raise ValueError('cannot find {0:s} tag'.format(title))

    if max_len is not None:
        assert len(tag) == max_len

    return tag[0].attrs['content']


def get_ieee_metadata(t, verbose=False):
    if verbose:
        print('attempting to read metadata from javascript assignment (ieee style)')

    start = 'lobal.document.metadata={'

    if start not in t:
        return None

    s0 = t.index(start) + len(start) - 1
    s1 = s0 + t[s0:].index("\n") - 1

    meta = json.loads(t[s0:s1])

    author = meta['authors'][0]['lastName']
    title = meta['title']

    if 'journalDisplayDateOfPublication' in meta:
        year = meta['journalDisplayDateOfPublication']
    else:
        year = meta['publicationDate'][-4:]
    arnumber = meta['pdfUrl'].split('=')[-1]
    dl_url = 'http://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&isnumber=&arnumber=' + arnumber

    if verbose:
        print('using download url: ' + dl_url)

    return author, title, year, dl_url


def get_author(soup):

    multi_author_str = get_meta_tag(soup, ['citation_authors'], 'author', raise_error=False)

    if multi_author_str is not None:
        if ',' in multi_author_str:
            first_author_str = multi_author_str.split(',')[0]
        elif ';' in multi_author_str:
            first_author_str = multi_author_str.split(';')[0]
        else:
            first_author_str = multi_author_str

        return first_author_str

    # science direct

    tag = soup.find_all('span', {'class': 'text surname'})

    if len(tag) > 0:
        first_author_str = tag[0].text.capitalize()

        return first_author_str

    # other

    first_author_str = get_meta_tag(soup, ['citation_author', 'dc.contributor', 'dc.Creator', 'text surname'], 'author')

    return first_author_str


def handle_url(abs_url, outdirs, dl_url=None, supp_url=None, download=True, get_abstract=False, skip_pages=0, verbose=False):

    base_url = urlparse(abs_url).scheme + '://' + urlparse(abs_url).netloc

    # get abs page

    if verbose:
        print('downloading abs page: ' + abs_url)

    t = get(abs_url)

    if verbose:
        print('done')

    # get properties

    soup = BeautifulSoup(t, features='lxml')

    if 'ieeexplore.ieee.org' in abs_url:
        first_author_str, title, date_str, dl_url0 = get_ieee_metadata(t, verbose=verbose)

        if dl_url is None:
            dl_url = dl_url0

        ieee = True

    else:
        ieee = False

    # first author

    if not ieee:
        first_author_str = get_author(soup)

    if ',' in first_author_str:
        first_author = first_author_str.split(',')[0]
    else:
        first_author = first_author_str.split(' ')[-1]

    if verbose:
        print('detected first author: ' + first_author)

    # year

    if not ieee:
        date_str = get_meta_tag(soup, ['citation_online_date', 'citation_year', 'citation_date', 'citation_publication_date', 'dc.date', 'dc.Date', 'og:updated_time'], 'date', max_len=1)

    if ' ' in date_str:
        sp = date_str.split(' ')
        year = None
        for s in sp:
            s = s.strip()
            if len(s) == 4:
                year = s
        assert year is not None
        assert year.isnumeric()
        assert float(year).is_integer()
    elif '/' in date_str:
        year = date_str.split('/')[0]
    elif '-' in date_str:
        assert '-' in date_str
        year = date_str.split('-')[0]
    else:
        assert len(date_str) == 4
        year = date_str

    assert len(year) == 4

    if verbose:
        print('detected year: ' + year)

    # title

    if not ieee:
        title = get_meta_tag(soup, ['citation_title', 'dc.title', 'dc.Title', 'og:title'], 'title', max_len=1)

    if verbose:
        print('detected title: ' + title)

    # download or return data

    if download:

        fn = '_'.join([first_author, year, title])

        # make filename filesystem safe

        fn = unidecode(fn)
        fn = re.sub(r'[^\w\-_\.]', '', fn.replace(' ', '_')).lower() + '.pdf'

        if verbose:
            print('generated filename: '+fn)

        fn_list = [os.path.join(outdir, fn) for outdir in outdirs]
        fn = fn_list[0]

        # download file

        if dl_url is None:
            dl_url = find_download_url(soup, base_url)

            if dl_url is None:
                raise ValueError('cannot find download url')

            if dl_url[:4] != 'http':
                raise ValueError()

        if verbose:
            print('downloading pdf: ' + dl_url)

        get(dl_url, download_to=fn)  # TODO: handle response

        # handle supplement

        if supp_url:
            fn_supp = fn[:-4] + '_supplement.pdf'

            get(supp_url, download_to=fn_supp)  # TODO: handle response

            # join files and clean up

            c = ['pdfjam', '--rotateoversize', 'false', fn, fn_supp, '--outfile', fn]

            subprocess.run(c)

            os.remove(fn_supp)

            print('joined supplement')

        # skip pages

        if skip_pages:
            c = ['pdfjam', fn, str(skip_pages + 1) + '-', '--outfile', fn]

            subprocess.run(c)

            print('skipped {0:d} pages'.format(skip_pages))

        if verbose:
            print('done')

        print('saved to ' + fn)

        for fn1 in fn_list[1:]:
            shutil.copyfile(fn, fn1)
            # TODO: check return / catch errors

            print('saved to ' + fn1)

    else:
        # get data and return

        data = dict(abs_url=abs_url, first_author=first_author, year=year, title=title, abstract=abstract if get_abstract else None)

        return data


def find_download_url(soup, base_url):
    # try to find download link
    #
    # TODO: convert all instances to using passed base url

    # most sites

    tag_dl = soup.find_all('meta', {'name': 'citation_pdf_url'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['content']

        return dl_url

    # acs

    tag_dl = soup.find_all('a', {'class': 'pdf-button'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = base_url + tag_dl[0].attrs['href']

        return dl_url

    # annual review

    tag_doi = soup.find_all('meta', {'name': 'dc.Identifier', 'scheme': 'doi'})

    if len(tag_doi) > 0:
        assert len(tag_doi) == 1
        doi = tag_doi[0].attrs['content']

        if '/' in doi and doi.split('/')[1][:8] == 'annurev-':
            dl_url = base_url + doi

            return dl_url

    # elife

    tag_dl = soup.find_all('a', {'data-download-type': 'pdf-article'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['href']

        return dl_url

    # neco

    tag_dl = soup.find_all('a', {'class': 'show-pdf'})

    if len(tag_dl) > 0:
        #assert len(tag_dl) == 1
        dl_url = base_url + tag_dl[0].attrs['href']

        return dl_url

    # pmc

    tag_dl = soup.find_all('link', {'rel': 'alternate', 'type': 'application/pdf'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['href']

        if dl_url[:4] != 'http':
            dl_url = base_url + dl_url

        return dl_url

    # royal society publishing

    tag_dl = soup.find_all('div', {'class': 'download_transportable'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = [*tag_dl[0].children][0]['href']
        dl_url = base_url + dl_url

        return dl_url

    # science direct

    tag_json_data = soup.find_all('script', {'type': 'application/json'})

    if len(tag_json_data) > 0:
        assert len(tag_json_data) == 1
        json_data = json.loads(str(tag_json_data[0].contents[0]))

        dl_data = json_data['article']['pdfDownload']
        assert dl_data['linkType'] == 'DOWNLOAD'

        url_data = dl_data['urlMetadata']
        assert url_data['path'] == 'science/article/pii'

        query = 'pdfft?md5=' + url_data['queryParams']['md5'] + '&pid=' + url_data['queryParams']['pid']
        show_url = '/'.join(['https://www.sciencedirect.com', url_data['path'], url_data['pii'], query])

        html = get(show_url)

        start_s = 'Please wait while you are being redirected, or click <a href'

        if start_s in html:
            html = html[html.index(start_s):]
            html = html[html.index('"') + 1:]
            dl_url = html[:html.index('"')]

            return dl_url

    return None
