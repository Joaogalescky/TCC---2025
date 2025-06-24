test:
	@echo "Test Makefile realized"
all: 
	run
ambient:
	python3 -m venv VenvElectionFhe
	source VenvElectionFhe/bin/activate
install: 
	pip3 install -r requirements.txt
run:
	python3 SistemaEleicaoCriptografada/src/main.py