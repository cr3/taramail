ENV := .env
SUBDIRS := backend
TARGETS := setup check test coverage

-include $(ENV)

.PHONY: $(TARGETS) $(SUBDIRS)
$(TARGETS): $(SUBDIRS)
$(SUBDIRS):
	@$(MAKE) -C $@ $(MAKECMDGOALS)

NODE_MODULES := node_modules
TOUCH := node -e "import fs from 'fs'; const f=process.argv[1]; try{fs.utimesSync(f,new Date(),new Date())}catch{fs.closeSync(fs.openSync(f,'w'))}"

package-lock.json: package.json
	@echo Updating lock file
	@npm install --package-lock-only

# Build node_modules with deps.
$(NODE_MODULES): package-lock.json
	@echo Installing Node environment
	@npm install
	@$(TOUCH) $@

# Convenience target to build node_modules
.PHONY: setup
setup: $(NODE_MODULES)

.PHONY: check
check: $(NODE_MODULES)
	@npm run lint

.PHONY: deploy
deploy:
	@echo Deploying
	@docker compose pull
	@docker compose up --force-recreate --build -d
	@docker image prune -f

.PHONY: undeploy
undeploy:
	@echo Undeploying
	@docker compose down

.PHONY: clean
clean:
	@echo Cleaning ignored files
	@git clean -Xfd

.DEFAULT_GOAL := test
