#!/bin/sh

cleanup_and_exit()
{
  rm tmp/*.pdf
  rmdir tmp
  exit $1
}

fail()
{
  echo $1
  cleanup_and_exit 1
}

test_download()
{
  ./arxyv.py -v -o ./tmp "$1" || fail "cannot download file: $1"
  [ -f $(echo "./tmp/$2") ] || fail "cannot find output file: ./$2"
  [ "$(file -b $(echo ./tmp/$2) | cut -d, -f1)" = 'PDF document' ] || fail "bad output file type: ./$2"
}

cd $(dirname $0)

mkdir tmp

test_download 'https://www.annualreviews.org/doi/abs/10.1146/annurev-polisci-052318-025732' riedl_2020_*.pdf
test_download 'https://journals.aps.org/prx/abstract/10.1103/PhysRevX.6.011030' ansmann_2016_*.pdf
test_download 'https://arxiv.org/abs/1001.1001v1' judge_2010_*.pdf
test_download 1001.1002 hogenson_2018_*.pdf
test_download 'https://www.biorxiv.org/content/10.1101/139014v1' gabashvili_2017_*.pdf
test_download 'https://elifesciences.org/articles/03980' patterson_2014_*.pdf
test_download 'https://www.eneuro.org/content/3/4/ENEURO.0176-16.2016' bernard_2016_*.pdf
test_download 'https://www.frontiersin.org/articles/10.3389/fncom.2020.00039/full' chance_2020_*.pdf
test_download 'https://iclr.cc/virtual_2020/poster_BkxRRkSKwr.html' jin_2020_*.pdf
test_download 'https://ieeexplore.ieee.org/document/1677462' mollick_2006_*.pdf
test_download 'https://www.mitpressjournals.org/doi/abs/10.1162/neco.2007.19.10.2638' guclu_2007_*.pdf
test_download 'https://www.nature.com/articles/510218a' kutschera_2014_*.pdf
test_download 'https://openreview.net/forum?id=S1Bb3D5gg' weston_2017_*.pdf
test_download 'https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1007395' bourne_2019_*.pdf
test_download 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7604159/' chen_2021_*.pdf
test_download 'https://www.pnas.org/content/117/40/24627' swinderen_2020_*.pdf
test_download 'https://royalsocietypublishing.org/doi/10.1098/rsob.200367' wang_2021_*.pdf
test_download 'https://www.sciencedirect.com/science/article/pii/S0893608019303181?fbclid=IwAR3Zu4aj38sb4pchp-jtzaizsIYvYao-QAZpFC2Ay8Nb672fipM-TDGE9eY' taherkhani_2019_*.pdf

echo "all tests ok."

cleanup_and_exit 0
