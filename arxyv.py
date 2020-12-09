#!/usr/bin/env python3
#
# arxyv.py
#

from bs4 import BeautifulSoup
import click
import json
import os
import os.path
import re
import requests
import shutil
import subprocess
from urllib.parse import urlparse


default_outdir = '~/Downloads'

user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36'


def check_url(url):
    up = urlparse(url)

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

    start = 'global.document.metadata={'

    if not start in t:
        return None

    s0 = t.index(start) + len(start) - 1
    s1 = s0 + t[s0:].index("\n") - 1

    meta = json.loads(t[s0:s1])

    author = meta['authors'][0]['lastName']
    title = meta['title']
    year = meta['journalDisplayDateOfPublication']#[-4:]
    arnumber = meta['pdfUrl'].split('=')[-1]
    dl_url = 'http://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&isnumber=&arnumber=' + arnumber

    print(dl_url)

    return author, title, year, dl_url


def get_author(soup):

    multi_author_str = get_meta_tag(soup, ['citation_authors'], 'author', raise_error=False)

    if multi_author_str is not None:
        if ',' in multi_author_str:
            first_author_str = multi_author_str.split(',')[0]
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


def handle_url(abs_url, outdir, dl_url=None, supp_url=None, skip_pages=0, verbose=False):

    # get abs page

    if verbose:
        print('downloading abs page: '+abs_url)

    t = get(abs_url)

    if verbose:
        print('done')

    # get properties

    soup = BeautifulSoup(t, features='lxml')

    if 'ieeexplore.ieee.org' in abs_url:
        first_author_str, title, date_str, dl_url = get_ieee_metadata(t, verbose=verbose)
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
        print('detected first author: '+first_author)

    # year

    if not ieee:
        date_str = get_meta_tag(soup, ['citation_online_date', 'citation_year', 'citation_date', 'citation_publication_date', 'dc.date', 'dc.Date'], 'date', max_len=1)

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
        print('detected year: '+year)

    # title

    if not ieee:
        title = get_meta_tag(soup, ['citation_title', 'dc.title', 'dc.Title'], 'title', max_len=1)

    if verbose:
        print('detected title: '+title)

    fn = '_'.join([first_author, year, title])

    # make filename filesystem safe

    fn = re.sub('[^\w\-_\.]', '', fn.replace(' ', '_')).lower() + '.pdf'
    fn = os.path.join(outdir, fn)

    # download

    if dl_url is None:
        dl_url = find_download_url(soup)

        if dl_url is None:
            raise ValueError('cannot find download url')

        if dl_url[:4] != 'http':
            raise ValueError()

    if verbose:
        print('downloading pdf: '+dl_url)

    r = get(dl_url, download_to=fn)

    #response_headers = {k: v for k, v in t[1]._headers}
    #assert response_headers['Content-Type'] == 'application/pdf'
    #assert int(response_headers['Content-Length']) > 0

    # handle supplement

    if supp_url:
        fn_supp = fn[:-4] + '_supplement.pdf'

        r = get(supp_url, download_to=fn_supp)

        # join files and clean up

        c = ['pdfjam', '--rotateoversize', 'false', fn, fn_supp, '--outfile', fn]

        subprocess.run(c)

        os.remove(fn_supp)

        print('joined supplement')

    # skip pages

    if skip_pages:
        c = ['pdfjam', fn, str(skip_pages)+'-', '--outfile', fn]

        subprocess.run(c)

        print('skipped {0:d} pages'.format(skip_pages))

    if verbose:
        print('done')

    print('saved to '+fn)


def find_download_url(soup):
    # try to find download link

    # most sites

    tag_dl = soup.find_all('meta', {'name': 'citation_pdf_url'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['content']

        return dl_url

    # annual review

    tag_doi = soup.find_all('meta', {'name': 'dc.Identifier'})

    if len(tag_doi) > 0:
        assert len(tag_doi) == 1
        doi = tag_doi[0].attrs['content']

        if '/' in doi and doi.split('/')[1][:8] == 'annurev-':
            dl_url = "https://www.annualreviews.org/doi/pdf/" + doi

            return dl_url

    # elife

    tag_dl = soup.find_all('a', {'data-download-type': 'pdf-article'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['href']

        return dl_url

    # pmc

    tag_dl = soup.find_all('link', {'rel': 'alternate', 'type': 'application/pdf'})

    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['href']

        return dl_url

    # science direct

    html = str(soup)

    start_s = '"linkToPdf"'

    if start_s in html:
        html = html[html.index(start_s):]
        html = html[html.index(':'):]
        html = html[html.index('"')+1:]
        show_url = "https://sciencedirect.com" + html[:html.index('"')]

        html = get(show_url)

        start_s = 'Please wait while you are being redirected, or click <a href'

        if start_s in html:
            html = html[html.index(start_s):]
            html = html[html.index('"')+1:]
            dl_url = html[:html.index('"')]

            return dl_url

    return None


@click.command(help='Download paper defined by key (either an url or an arXiv handle).')
@click.argument('key', type=str)
@click.option('-o', '--outdir', type=click.Path(exists=True), default=None, help='output directory, default: $HOME/Downloads')
@click.option('-s', '--supplement', type=str, default=None, help='url of supplementary pdf to merge')
@click.option('--skip-pages', type=int, default=0, help='number of pages to skip')
@click.option('-v', '--verbose', is_flag=True, default=False, help='be verbose')
def main(key, outdir, supplement, skip_pages, verbose):

    # set outdir

    if outdir is None:
        outdir = default_outdir

    outdir = os.path.expanduser(outdir)

    # check if key is an url

    if verbose:
        print('passed key: '+key)

    url = check_url(key)

    if url:
        if verbose:
            print('key is url')

        if supplement:
            supp_url = check_url(supplement)

            if not supp_url:
                raise ValueError('cannot interpret supplement as url: ' + supplement)

        else:
            supp_url = None

        handle_url(url, outdir=outdir, supp_url=supp_url, skip_pages=skip_pages, verbose=verbose)

    else:  # try interpreting as arXiv key
        if verbose:
            print('cannot interpret key as url')

        if not '.' in key and key.count('.') == 1:
            raise ValueError('cannot interpret key: '+key)

        sp = key.split('.')

        if not len(sp[0]) == 4 and len(sp[1]) in [4, 5]:
            raise ValueError('cannot interpret key: '+key)

        if not sp[0].isnumeric() and sp[1].isnumeric():
            raise ValueError('cannot interpret key: '+key)

        if verbose:
            print('assuming key is arxiv key')

        if supplement:
            print('passed arxiv key, ignoring passed supplement')

        url_base = 'https://arxiv.org'
        abs_url = url_base + '/abs/' + key
        dl_url = url_base + '/pdf/' + key

        handle_url(abs_url, dl_url=dl_url, outdir=outdir, skip_pages=skip_pages, verbose=verbose)


if __name__ == '__main__':
    main()
