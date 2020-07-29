# arxyv: download and rename scholarly articles

## Usage

        arxyv.py 2001.01337  # assumes input is arXiv ID

        arxyv.py https://arxiv.org/abs/2001.01337

        arxyv.py 2001.01337 -o target_directory  # otherwise $HOME/Downloads is used

PDFs are renamed as *[firstauthor]_[year]_[title].pdf*.

Works with URLs from:

* arXiv
* eLife
* eNeuro
* Frontiers
* ICLR
* IEEExplore
* Nature
* OpenReview
* PLoS

* (bioRxiv currently not working)

## Dependencies

* BeautifulSoup
* click
* requests
