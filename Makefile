.PHONY: help install start stop restart status logs dev test clean

PORT ?= 8000
HOST ?= 127.0.0.1
RUN_DIR := .run
PID := $(RUN_DIR)/server.pid
LOG := $(RUN_DIR)/server.log

help:                                   ## Show targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

install:                                ## Install deps + chromium
	uv sync
	uv run playwright install chromium

start:                                  ## Start uvicorn in background on :$(PORT)
	@mkdir -p $(RUN_DIR); \
	if [ -f $(PID) ] && kill -0 `cat $(PID)` 2>/dev/null; then \
	  echo "already running (pid `cat $(PID)`)"; \
	else \
	  nohup uv run uvicorn app.main:app --host $(HOST) --port $(PORT) >> $(LOG) 2>&1 & echo $$! > $(PID); \
	  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
	    curl -sf http://$(HOST):$(PORT)/ -o /dev/null && break; sleep 1; \
	  done; \
	  echo "started pid `cat $(PID)` on http://$(HOST):$(PORT)  (logs: $(LOG))"; \
	fi

stop:                                   ## Stop background uvicorn
	@if [ -f $(PID) ] && kill -0 `cat $(PID)` 2>/dev/null; then \
	  kill `cat $(PID)` && echo "stopped pid `cat $(PID)`"; \
	else echo "not running"; fi
	@rm -f $(PID)

restart: stop start                     ## Restart background uvicorn

status:                                 ## Show running pid + port
	@if [ -f $(PID) ] && kill -0 `cat $(PID)` 2>/dev/null; then \
	  echo "running pid `cat $(PID)` on $(HOST):$(PORT)"; \
	else echo "stopped"; fi

logs:                                   ## Tail server log
	@touch $(LOG); tail -f $(LOG)

dev:                                    ## Foreground uvicorn with --reload on :$(PORT)
	uv run uvicorn app.main:app --host $(HOST) --port $(PORT) --reload

test:                                   ## Run pytest
	uv run pytest

clean:                                  ## Remove pycache + .pytest_cache + .run
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache $(RUN_DIR)
