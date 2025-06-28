.PHONY: run publish touch-history autoformat build-dev build shell list help

USE_HOST_NET ?= 0

help: ## This help
	@grep -F "##" $(MAKEFILE_LIST) | grep -vF '@grep -F "##" $$(MAKEFILE_LIST)' | sed -r 's/(:).*##/\1/' | sort

list: ## List all targets
	@make -qp | awk -F':' '/^[a-zA-Z0-9][^$$#\/\t=]*:([^=]|$$)/ {split($$1,A,/ /);for(i in A)print A[i]}'

shell: touch-history ## Open a shell
ifeq ($(USE_HOST_NET), 1)
	docker run --rm -it \
	    -v $$(pwd):/app \
	    -v $$(pwd)/.bash_history_krill:/home/user/.bash_history \
	    --network=host \
	    --entrypoint /bin/bash \
	    kyokley/krill-base
else
	docker run --rm -it \
	    -v $$(pwd):/app \
	    -v $$(pwd)/.bash_history_krill:/home/user/.bash_history \
	    --entrypoint /bin/bash \
	    kyokley/krill-base
endif

build: ## Build prod container
ifeq ($(USE_HOST_NET), 1)
	docker build --network=host --target=prod -t kyokley/krill-base .
else
	docker build --target=prod -t kyokley/krill-base .
endif

build-dev: ## Build dev container
ifeq ($(USE_HOST_NET), 1)
	docker build --network=host --target=dev -t kyokley/krill-base .
else
	docker build --target=dev -t kyokley/krill-base .
endif

build-base: ## Build dev container
ifeq ($(USE_HOST_NET), 1)
	docker build --network=host --target=base-builder -t kyokley/krill-base .
else
	docker build --target=base-builder -t kyokley/krill-base .
endif

autoformat: ## autoformat source code with black
	docker run --rm -v $$(pwd):/app kyokley/krill-base /bin/bash -c "find . -name '*.py' | xargs isort && find . -name '*.py' | xargs black -S"

touch-history:
	@touch ./.bash_history_krill
	@chmod 777 ./.bash_history_krill

publish: build ## Build and push docker image to dockerhub
	docker push kyokley/krill-base

run: build ## Run krill
ifeq ($(USE_HOST_NET), 1)
	docker run --rm -it --network=host -v $$(pwd):/app kyokley/krill-base
else
	docker run --rm -it -v $$(pwd):/app kyokley/krill-base
endif

tests: build-dev ## Run test cases
	docker run --rm -t -v $$(pwd):/app --entrypoint uv kyokley/krill-base run -n pytest
