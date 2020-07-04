.PHONY: run publish touch-history autoformat build-dev build shell list help

help: ## This help
	@grep -F "##" $(MAKEFILE_LIST) | grep -vF '@grep -F "##" $$(MAKEFILE_LIST)' | sed -r 's/(:).*##/\1/' | sort

list: ## List all targets
	@make -qp | awk -F':' '/^[a-zA-Z0-9][^$$#\/\t=]*:([^=]|$$)/ {split($$1,A,/ /);for(i in A)print A[i]}'

shell: build-dev ## Open a shell
	docker run --rm -it \
	    -v $$(pwd)/krill:/app/krill \
	    -v ~/.bash_history_krill:/root/.bash_history \
	    -v $$(pwd)/pyproject.toml:/app/pyproject.toml \
	    -v $$(pwd)/poetry.lock:/app/poetry.lock \
	    kyokley/krill-base /bin/bash

build: ## Build prod container
	docker build --target=prod -t kyokley/krill-base .

build-dev: ## Build dev container
	docker build --target=dev -t kyokley/krill-base .

autoformat: ## autoformat source code with black
	docker run --rm -v $$(pwd)/krill:/app/krill kyokley/krill-base /bin/bash -c "find . -name '*.py' | xargs isort && find . -name '*.py' | xargs black -S"

touch-history:
	@touch ~/.bash_history_krill

publish: build ## Build and push docker image to dockerhub
	docker push kyokley/krill-base

run: ## Run krill++
	docker run --rm -it -v $$(pwd)/krill:/app/krill kyokley/krill-base

tests: build-dev ## Run test cases
	docker run --rm -t -v $$(pwd)/krill:/app/krill kyokley/krill-base /bin/bash -c "pytest"
