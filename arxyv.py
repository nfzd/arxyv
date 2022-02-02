#!/usr/bin/env python3
#
# arxyv.py
#

import click
import os.path

from backend import check_arxiv_key, check_url, handle_url

default_outdir = '~/Downloads'


@click.command(help='Download paper defined by key (either an url or an arXiv handle).')
@click.argument('key', type=str)
@click.option('-o', '--outdir', type=click.Path(exists=True), default=None, multiple=True, help='output directory, default: $HOME/Downloads')
@click.option('-d', '--download-url', type=str, default=None, help='download url, default: try to infer from abstract webpage')
@click.option('-s', '--supplement', type=str, default=None, help='url of supplementary pdf to merge')
@click.option('--skip-pages', type=int, default=0, help='number of pages to skip')
@click.option('-v', '--verbose', is_flag=True, default=False, help='be verbose')
def main(key, outdir, supplement, download_url, skip_pages, verbose):

    # set outdir

    if not outdir:
        outdir = [default_outdir]

    outdir = [os.path.expanduser(od) for od in outdir]

    if verbose:
        print('passed key: ' + key)

    # check if key is an arXiv key

    if verbose:
        print('try to interpret key as arXiv key')

    try:
        url, dl_url = check_arxiv_key(key, verbose=verbose)

        error = False

    except ValueError:
        error = True
        if verbose:
            print('cannot interpret key as arXiv key')

    if error:
        # check if key is an url

        if verbose:
            print('try to interpret key as url')

        url = check_url(key)

        if url:
            if verbose:
                print('key is url')

            dl_url = None

        else:
            if verbose:
                print('cannot interpret key as url')

    # handle passed download url

    if download_url is not None:
        if dl_url is not None:
            if verbose:
                print('overriding download url with argument')
        else:
            if verbose:
                print('using download url from argument')

        dl_url = download_url

    # handle supplement

    if supplement:
        supp_url = check_url(supplement)

        if not supp_url:
            raise ValueError('cannot interpret supplement as url: ' + supplement)

    else:
        supp_url = None

    handle_url(url, dl_url=dl_url, supp_url=supp_url, outdirs=outdir, skip_pages=skip_pages, verbose=verbose)


if __name__ == '__main__':
    main()
