#!/usr/bin/env python3
#
# abslist.py
#

import click
import os.path
import sys
from types import SimpleNamespace

from backend import check_arxiv_key, check_url, handle_url

default_outdir = '~/Downloads'


@click.command(help='Create a markdown-formatted paper list based on passed urls or an arXiv handles.')
@click.argument('keys', type=str, nargs=-1)
@click.option('-o', '--out', type=click.Path(exists=False), default=None, help='output file, default: print to stdout')
@click.option('--overwrite', is_flag=True, default=False, help='overwrite existing file')
#@click.option('-a', '--with-abstract', is_flag=True, default=False, help='include abstract')
@click.option('--title-prefix', type=str, default='# ', help='prefix for title lines')
@click.option('-v', '--verbose', is_flag=True, default=False, help='be verbose')
def main(keys, out, overwrite, title_prefix, verbose):

    if len(keys) == 0:
        print('nothing to do')

    if out is not None and os.path.exists(out):
        print('error: output file {out} exists (and --overwrite was not passed), aborting')
        sys.exit(1)

    absdata = []

    for key in keys:
        # check if key is an arXiv key

        if verbose:
            print(f'key: {key}')
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

        data = handle_url(url, outdirs=None, get_abstract=with_abstract, download=False, verbose=verbose)

        absdata += [data]

    # format

    abslist = ''

    for i, ad in enumerate(absdata):
        ad = SimpleNamespace(**ad)

        if i > 0:
            abslist += '\n\n'

        # TODO: dont assume et al.

        abslist += f'{title_prefix}{ad.first_author} et al. {ad.year} [{ad.title}]({ad.abs_url})\n'

    # print output or write to file

    if out:
        with open(out, 'w') as f:
            f.write(abslist)

    else:
        print(abslist)

    return

    if verbose:
        print('passed key: ' + key)


if __name__ == '__main__':
    main()
