.PHONY: install test lint clean release-macos release-macos-swift macos-project test-swift run-macos

install:
	pip install -r requirements.txt

test:
	pytest sisr/tests/

test-swift:
	cd macos/Packages/SISRKit && swift test

macos-project:
	python3 macos/scripts/generate_xcodeproj.py

# Build the native SwiftUI app and launch it (no Xcode GUI required).
run-macos:
	@chmod +x macos/scripts/run-app.sh
	@./macos/scripts/run-app.sh

lint:
	flake8 .
	black --check .

format:
	black .

release-macos:
	chmod +x scripts/release/macos-build-sign-notarize.sh
	./scripts/release/macos-build-sign-notarize.sh

release-macos-swift:
	chmod +x scripts/release/macos-swift-build-sign-notarize.sh
	./scripts/release/macos-swift-build-sign-notarize.sh

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	find . -type d -name "dist" -exec rm -r {} +
	find . -type d -name "build" -exec rm -r {} + 