help: ## This help
	@grep -F "##" $(MAKEFILE_LIST) | grep -vF '@grep -F "##" $$(MAKEFILE_LIST)' | sed -r 's/(:).*##/\1/' | sort

list: ## List all targets
	@make -qp | awk -F':' '/^[a-zA-Z0-9][^$$#\/\t=]*:([^=]|$$)/ {split($$1,A,/ /);for(i in A)print A[i]}'

shell: build-dev ## Open a shell
	docker-compose run krill /bin/bash

build: ## Build prod container
	docker-compose build

build-dev: ## Build dev container
	docker-compose build --build-arg REQS= krill

autoformat: build-dev touch-history ## autoformat source code with black
	docker-compose run --no-deps --rm krill /bin/bash -c "find . -name '*.py' | xargs isort && find . -name '*.py' | xargs black -S"

touch-history:
	@touch ~/.bash_history_krill

publish: build
	docker push kyokley/krill-base

run: build-dev ## Run krill++
	docker-compose run --rm krill
