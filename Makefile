help: ## This help
	@grep -F "##" $(MAKEFILE_LIST) | grep -vF '@grep -F "##" $$(MAKEFILE_LIST)' | sed -r 's/(:).*##/\1/' | sort

list: ## List all targets
	@make -qp | awk -F':' '/^[a-zA-Z0-9][^$$#\/\t=]*:([^=]|$$)/ {split($$1,A,/ /);for(i in A)print A[i]}'

up: touch-history ## Bring up all containers
	docker-compose up -d

down: ## Bring down all containers
	docker-compose down

shell: up ## Open a shell in a running container
	docker-compose exec krill /bin/bash

build: ## Build prod container
	docker-compose build

build-dev: ## Build dev container
	docker-compose build --build-arg REQS= krill

autoformat: build-dev touch-history ## autoformat source code with black
	docker-compose run --no-deps --rm krill /bin/sh -c "find . -name '*.py' | xargs isort && find . -name '*.py' | xargs black -S"

touch-history:
	@touch ~/.bash_history_krill
