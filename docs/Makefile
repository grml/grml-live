all: doc

doc: doc_man doc_html

doc_html: html-stamp

icons:
	mkdir -p images/icons
	cp /usr/share/asciidoc/icons/caution.png	images/icons/
	cp /usr/share/asciidoc/icons/important.png	images/icons/
	cp /usr/share/asciidoc/icons/note.png		images/icons/
	cp /usr/share/asciidoc/icons/tip.png		images/icons/

html-stamp: grml-live.txt grml-live-remaster.txt
	asciidoc -b xhtml11 -a icons -a toc -a numbered grml-live.txt
	asciidoc -b xhtml11 -a icons grml-live-remaster.txt
	touch html-stamp

doc_man: man-stamp

man-stamp: grml-live.txt grml-live-remaster.txt
	asciidoc -d manpage -b docbook grml-live.txt
	xsltproc --novalid /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live.xml
	asciidoc -d manpage -b docbook grml-live-remaster.txt
	xsltproc --novalid /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live-remaster.xml
	touch man-stamp

doc_epub: epub-stamp

epub-stamp:
	a2x --icons -a toc -a toclevels=3 -a docinfo -f epub grml-live.txt
	touch epub-stamp

doc_pdf: pdf-stamp

pdf-stamp:
	a2x --icons -a toc -a toclevels=3 -a docinfo -f pdf grml-live.txt
	touch pdf-stamp

online: icons doc_html doc_epub doc_pdf
	# this is assume that a checkout of grml.org.git is available
	# next to grml-live.git as "grml.org"
	test -d ../../grml.org/grml-live || exit 1
	cp grml-live.html	../../grml.org/grml-live/index.html
	cp grml-live.pdf	../../grml.org/grml-live/
	cp grml-live.epub	../../grml.org/grml-live/

clean:
	rm -rf images/icons
	rm -f grml-live-remaster.html grml-live-remaster.xml grml-live-remaster.8
	rm -f grml-live.html grml-live.xml grml-live.8 grml-live.epub grml-live.pdf
	rm -f html-stamp man-stamp epub-stamp pdf-stamp
