help: ## This help
	@grep -F "##" $(MAKEFILE_LIST) | grep -vF '@grep -F "##" $$(MAKEFILE_LIST)' | sed -r 's/(:).*##/\1/' | sort

list: ## List all targets
	@make -qp | awk -F':' '/^[a-zA-Z0-9][^$$#\/\t=]*:([^=]|$$)/ {split($$1,A,/ /);for(i in A)print A[i]}'

shell: build-dev ## Open a shell
	docker run --rm -it -v $$(pwd):/app -v ~/.bash_history_krill:/root/.bash_history kyokley/krill-base /bin/bash

build: ## Build prod container
	docker build --target=prod -t kyokley/krill-base .

build-dev: ## Build dev container
	docker build --target=dev -t kyokley/krill-base .

autoformat: build-dev touch-history ## autoformat source code with black
	docker run --rm -v $$(pwd):/app kyokley/krill-base /bin/bash -c "find . -name '*.py' | xargs isort && find . -name '*.py' | xargs black -S"

touch-history:
	@touch ~/.bash_history_krill

publish: build ## Build and push docker image to dockerhub
	docker push kyokley/krill-base

run: build-dev ## Run krill++
	docker run --rm -it -v $$(pwd):/app kyokley/krill-base
