all: doc

# doc: doc_man doc_html
doc: doc_html

doc_html: html-stamp

html-stamp: grml-live.txt
	asciidoc -b xhtml11 grml-live.txt
	touch html-stamp

doc_man: man-stamp

man-stamp: grml-live.txt
	asciidoc -d manpage -b docbook grml-live.txt
	sed -i 's/<emphasis role="strong">/<emphasis role="bold">/' grml-live.xml
	xsltproc /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl grml-live.xml
	# ugly hack to avoid duplicate empty lines in manpage
	# notice: docbook-xsl 1.71.0.dfsg.1-1 is broken! make sure you use 1.68.1.dfsg.1-0.2!
	cp grml-live.8 grml-live.8.tmp
	uniq grml-live.8.tmp > grml-live.8
	rm grml-live.8.tmp
	touch man-stamp

clean:
	rm -rf grml-live.html grml-live.xml grml-live.8 html-stamp man-stamp

online:
	scp grml-live.html grml:/var/www/grml/grml-live/index.html
