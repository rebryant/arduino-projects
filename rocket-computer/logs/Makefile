INTERP = python3
RDIR = ..
GEN = $(RDIR)/report_generator.py

CSV1 = 2024-02-11-Ukraine-B6.csv 2024-02-11-Ukraine-C6.csv 2024-02-11-Bert-C6.csv

rock1: ../tex/2024-02-11-rockets.pdf

../tex/2024-02-11-rockets.pdf: $(CSV1)
	$(INTERP) $(GEN) -t "11 Feb 2024 Rockets" -o ../tex/2024-02-11-rockets.tex $(CSV1)
	pushd ../tex ; pdflatex 2024-02-11-rockets ; popd

