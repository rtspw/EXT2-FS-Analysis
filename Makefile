# NAME: Richard Tang
# EMAIL: richardcxtang@ucla.edu
# ID: 305348008

studentID = 305348008

.PHONY: clean dist default

default: lab3b

lab3b: lab3b.py
	printf '#!/usr/bin/env bash\npython3 lab3b.py $$@' > lab3b
	chmod u+x ./lab3b

clean:
	rm -f lab3b-$(studentID).tar.gz lab3b

dist: lab3b.py README Makefile
	tar -czf lab3b-$(studentID).tar.gz lab3b.py README Makefile
