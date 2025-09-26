MANPAGES = grml-autoconfig.1 grml-autoconfig.8 restore-config.1 save-config.1 grml-live.8 grml-live-fai.5 grml-live-remaster.8

all: doc

doc: doc_man doc_html

doc_html: $(addsuffix .html, $(MANPAGES))
doc_man: $(addsuffix .gz, $(MANPAGES))

%.html : %.adoc ;
	asciidoc -b xhtml11 -a icons $^

%.gz : %.adoc ;
	asciidoc -d manpage -b docbook $^
	#sed -i 's/<emphasis role="strong">/<emphasis role="bold">/g' `echo $^ |sed -e 's/.adoc/.xml/'`
	xsltproc -nonet /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl `echo $^ |sed -e 's/.adoc/.xml/'` > /dev/null 2>&1
	gzip -f --best `echo $^ |sed -e 's/.adoc//'`

grml-live.8.html: grml-live.8.adoc
	asciidoc -b xhtml11 -a icons -a toc -a numbered $^

icons:
	mkdir -p images/icons
	cp /usr/share/asciidoc/icons/caution.png	images/icons/
	cp /usr/share/asciidoc/icons/important.png	images/icons/
	cp /usr/share/asciidoc/icons/note.png		images/icons/
	cp /usr/share/asciidoc/icons/tip.png		images/icons/

doc_epub: epub-stamp

epub-stamp:
	a2x --icons -a toc -a toclevels=3 -a docinfo -f epub grml-live.8.adoc
	touch epub-stamp

doc_pdf: pdf-stamp

pdf-stamp:
	a2x --icons -a toc -a toclevels=3 -a docinfo -f pdf grml-live.8.adoc
	touch pdf-stamp

clean:
	rm -rf images/icons
	for i in $(MANPAGES); do \
		rm -f $$i.html $$i.xml $$i.gz $$i.pdf $$i.epub $$i; done
	rm -f html-stamp man-stamp epub-stamp pdf-stamp
