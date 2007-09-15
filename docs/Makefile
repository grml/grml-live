all: doc

doc: doc_man doc_html

doc_html: html-stamp

html-stamp: grml-live.txt
	asciidoc -b xhtml11 grml-live.txt
	touch html-stamp

doc_man: man-stamp

man-stamp: grml-live.txt
	asciidoc -d manpage -b docbook grml-live.txt
	xsltproc /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live.xml
	touch man-stamp

online: doc_html
	scp grml-live.html grml:/var/www/grml/grml-live/index.html

clean:
	rm -rf grml-live.html grml-live.xml grml-live.8 html-stamp man-stamp
