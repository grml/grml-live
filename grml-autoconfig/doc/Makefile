%.html : %.txt ;
	asciidoc -b xhtml11 $^

%.gz : %.txt ;
	asciidoc -d manpage -b docbook $^
	#sed -i 's/<emphasis role="strong">/<emphasis role="bold">/g' `echo $^ |sed -e 's/.txt/.xml/'`
	xsltproc -nonet /usr/share/xml/docbook/stylesheet/nwalsh/manpages/docbook.xsl `echo $^ |sed -e 's/.txt/.xml/'` > /dev/null 2>&1
	# ugly hack to avoid '.sp' at the end of a sentence or paragraph:
	sed -i 's/\.sp//' `echo $^ | sed -e 's/.txt//'`
	gzip -f --best `echo $^ |sed -e 's/.txt//'`

MANPAGES = grml-autoconfig.1 grml-autoconfig.8 grml-bootsplash.1 restore-config.1 save-config.1

all: doc

doc: doc_man doc_html
doc_html: $(addsuffix .html, $(MANPAGES))
doc_man: $(addsuffix .gz, $(MANPAGES))

clean:
	@for i in $(MANPAGES); do \
		rm -f $$i.html $$i.xml $$i.gz $$i; done

