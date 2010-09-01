all: doc

doc: doc_man doc_html doc_epub doc_pdf

doc_html: html-stamp

html-stamp: grml-live.txt grml-live-remaster.txt grml-live-db.txt
	asciidoc -b xhtml11 -a icons -a toc -a numbered grml-live.txt
	asciidoc -b xhtml11 -a icons grml-live-remaster.txt
	asciidoc -b xhtml11 -a icons grml-live-db.txt
	touch html-stamp

doc_man: man-stamp

man-stamp: grml-live.txt grml-live-remaster.txt
	asciidoc -d manpage -b docbook grml-live.txt
	xsltproc /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live.xml
	asciidoc -d manpage -b docbook grml-live-remaster.txt
	xsltproc /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live-remaster.xml
	asciidoc -d manpage -b docbook grml-live-db.txt
	xsltproc /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live-db.xml
	touch man-stamp

doc_epub: epub-stamp

epub-stamp:
	a2x --icons -a toc -a toclevels=3 -a docinfo -f epub grml-live.txt
	touch epub-stamp

doc_pdf: pdf-stamp

pdf-stamp:
	a2x --icons -a toc -a toclevels=3 -a docinfo -f pdf grml-live.txt
	touch pdf-stamp

online: doc_html doc_epub doc_pdf
	scp grml-live.html grml:/var/www/grml/grml-live/index.html
	scp grml-live.pdf  grml:/var/www/grml/grml-live/
	scp grml-live.epub grml:/var/www/grml/grml-live/

clean:
	rm -f grml-live-remaster.html grml-live-remaster.xml grml-live-remaster.8
	rm -f grml-live.html grml-live.xml grml-live.8 grml-live.epub grml-live.pdf
	rm -f grml-live-db.html grml-live-db.xml grml-live-db.8
	rm -f html-stamp man-stamp epub-stamp pdf-stamp
