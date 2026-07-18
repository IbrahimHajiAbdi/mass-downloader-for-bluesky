include .env
export

.PHONY: build bump-patch bump-minor bump-major

bump-patch:
	poetry version patch

bump-minor:
	poetry version minor

bump-major:
	poetry version major

build:
	rm -rf dist/ && poetry run python3 -m build && poetry run python3 -m twine upload dist/*