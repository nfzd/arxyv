# arxyv: download and rename scholarly articles

## Usage

        arxyv.py 2001.01337  # assumes input is arXiv ID

        arxyv.py https://arxiv.org/abs/2001.01337

        arxyv.py 2001.01337 -o target_directory  # otherwise $HOME/Downloads is used

PDFs are renamed as *[firstauthor]\_[year]\_[title].pdf*. Non-ascii characters in names and titles are replaced with the closest matching ascii equivalent.

Works with URLs from:

* Annual Reviews
* APS
* arXiv
* bioRxiv
* eLife
* eNeuro
* Frontiers
* ICLR
* IEEExplore
* MITP journals
* Nature
* OpenReview
* PLoS
* PMC
* PNAS
* ScienceDirect

## Dependencies

* BeautifulSoup
* click
* requests
* unidecode
