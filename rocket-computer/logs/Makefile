INTERP = python3
RDIR = ..
GEN = $(RDIR)/report_generator.py

CSV1 = 2024-02-11-Ukraine-B6.csv 2024-02-11-Ukraine-C6.csv 2024-02-11-Bert-C6.csv

CSV2 = 2024-02-25-Frankengoose-C6.csv 2024-02-25-Ukraine-B6+A8.csv

CSV3 = 2024-07-20-ukraine-C6-unstable.csv

CSV4 = 2024-08-12-UkraineII-B6.csv 2024-08-12-UkraineII-C6.csv

rock1: ../tex/2024-02-11-rockets.pdf

rock2: ../tex/2024-02-25-rockets.pdf

rock3: ../tex/2024-07-20-unstable.pdf

rock4: ../tex/2024-08-12-rockets.pdf

../tex/2024-02-11-rockets.pdf: $(CSV1)
	$(INTERP) $(GEN) -t "11 Feb 2024 Rockets" -o ../tex/2024-02-11-rockets.tex $(CSV1)
	pushd ../tex ; pdflatex 2024-02-11-rockets ; popd

../tex/2024-02-25-rockets.pdf: $(CSV2)
	$(INTERP) $(GEN) -t "25 Feb 2024 Rockets" -o ../tex/2024-02-25-rockets.tex $(CSV2)
	pushd ../tex ; pdflatex 2024-02-25-rockets ; popd

../tex/2024-07-20-unstable.pdf: $(CSV2)
	$(INTERP) $(GEN) -t "20 Jul 2024 Unstable Rocket" -o ../tex/2024-07-20-unstable.tex $(CSV3)
	pushd ../tex ; pdflatex 2024-07-20-unstable ; popd

../tex/2024-08-12-rockets.pdf: $(CSV4)
	$(INTERP) $(GEN) -t "12 Aug 2024 Rockets" -o ../tex/2024-08-12-rockets.tex $(CSV4)
	pushd ../tex ; pdflatex 2024-08-12-rockets ; popd
