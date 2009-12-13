all: doc

doc: doc_man doc_html

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

online: doc_html
	scp grml-live.html grml:/var/www/grml/grml-live/index.html

clean:
	rm -rf grml-live-remaster.html grml-live-remaster.xml grml-live-remaster.8
	rm -rf grml-live.html grml-live.xml grml-live.8 html-stamp man-stamp
	rm -rf grml-live-db.html grml-live-db.xml grml-live-db.8 html-stamp man-stamp
