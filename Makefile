.PHONY: demo test package

demo:
	cd extension && npm ci && npm run demo

test:
	cd extension && npm test
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=bench python3.12 -m unittest discover -s bench -v

package:
	mkdir -p dist
	git archive --format=zip --prefix=pi-context-compression/ -o dist/pi-context-compression-source.zip HEAD
