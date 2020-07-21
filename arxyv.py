#!/usr/bin/env python3
#
# arxyv.py
#

from bs4 import BeautifulSoup
import click
import os.path
import re
from urllib.parse import urlparse
import urllib.request


user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.92 Safari/537.36'

default_outdir = '~/Downloads'


def setup_urllib():
    opener = urllib.request.build_opener()
    openeraddheaders = [('User-Agent', user_agent)]
    urllib.request.install_opener(opener)


def get(url, download_to=None):
    if download_to is None:
        r = urllib.request.urlopen(url).read()

    else:
        r = urllib.request.urlretrieve(url, filename=download_to)

    return r


def get_meta_tag(soup, name_list, title, ind=0, max_len=None):
    assert ind in [0, -1]

    for name in name_list:
        tag = soup.find_all('meta', {'name': name})

        if len(tag) > 0:
            break

    if len(tag) == 0:
        raise ValueError('cannot find {0:s} tag'.format(title))

    if max_len is not None:
        assert len(tag) == max_len

    return tag[0].attrs['content']


def handle_url(abs_url, outdir, dl_url=None, verbose=False):

    # get abs page

    if verbose:
        print('downloading abs page: '+abs_url)

    t = get(abs_url)
    soup = BeautifulSoup(t, features='lxml')

    if verbose:
        print('done')

    # get properties

    # first author

    first_author_str = get_meta_tag(soup, ['citation_author', 'dc.contributor'], 'author')

    if ',' in first_author_str:
        first_author = first_author_str.split(',')[0]
    else:
        first_author = first_author_str.split(' ')[-1]

    if verbose:
        print('detected first author: '+first_author)

    # year

    date_str = get_meta_tag(soup, ['citation_online_date', 'citation_year', 'citation_date', 'citation_publication_date', 'dc.date'], 'date', max_len=1)

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

    title = get_meta_tag(soup, ['citation_title', 'dc.title'], 'date', max_len=1)

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

    if verbose:
        print('downloading pdf: '+abs_url)

    t = get(dl_url, download_to=fn)

    response_headers = {k: v for k, v in t[1]._headers}
    assert response_headers['Content-Type'] == 'application/pdf'
    #assert int(response_headers['Content-Length']) > 0

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

    # elife

    tag_dl = soup.find_all('a', {'data-download-type': 'pdf-article'})
    if len(tag_dl) > 0:
        assert len(tag_dl) == 1
        dl_url = tag_dl[0].attrs['href']

        return dl_url

    return None


@click.command(help='Download paper defined by key (either an url or an arXiv handle).')
@click.argument('key', type=str)
@click.option('-o', '--outdir', type=click.Path(exists=True), default=None, help='output directory, default: $HOME/Downloads')
@click.option('-v', '--verbose', is_flag=True, default=False, help='be verbose')
def main(key, outdir, verbose):

    setup_urllib()

    # set outdir

    if outdir is None:
        outdir = default_outdir

    outdir = os.path.expanduser(outdir)

    # check if key is an url

    if verbose:
        print('passed key: '+key)

    up = urlparse(key)

    if urlparse(key).netloc:  # key is url
        if verbose:
            print('key is url')
        handle_url(key, outdir=outdir, verbose=verbose)

    else:
        key_with_scheme = 'https://' + key
        if verbose:
            print('modified key is url: '+key_with_scheme)

        up = urlparse(key_with_scheme)

        if up.netloc and up.path:  # key is url without scheme
            handle_url(key_with_scheme, outdir=outdir, verbose=verbose)

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

            url_base = 'https://arxiv.org'
            abs_url = url_base + '/abs/' + key
            dl_url = url_base + '/pdf/' + key

            handle_url(abs_url, dl_url=dl_url, outdir=outdir, verbose=verbose)


if __name__ == '__main__':
    main()
