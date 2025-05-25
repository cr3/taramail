ENV := .env
SUBDIRS := backend frontend
TARGETS := setup check test coverage

-include $(ENV)

.PHONY: $(TARGETS) $(SUBDIRS)
$(TARGETS): $(SUBDIRS)
$(SUBDIRS):
	@$(MAKE) -C $@ $(MAKECMDGOALS)

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
