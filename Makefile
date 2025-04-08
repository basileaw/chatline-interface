.PHONY: serve release embedded-client embedded-client-log remote-client remote-client-log remote-same-origin remote-same-origin-log

# Define color codes
BLUE := \033[1;34m
RESET := \033[0m

# Get remaining arguments after the target
ARGS := $(wordlist 2, $(words $(MAKECMDGOALS)), $(MAKECMDGOALS))

# Define a function to execute commands with nice output and handle arguments
# Usage: $(call task,command)
define task
	@printf "Make => $(BLUE)$(1) $(ARGS)$(RESET)\n"
	@$(1) $(ARGS)
	@exit 0
endef

# Release new version
release:
	$(call task,python utilities/release.py)

# Server and client commands (from poe tasks)
serve:
	$(call task,python example/server.py)

embedded-client:
	$(call task,python example/client.py)

embedded-client-log:
	$(call task,python example/client.py --enable-logging --log-file logs/chatline_debug.log)

remote-client:
	$(call task,python example/client.py -e http://127.0.0.1:8000/chat)

remote-client-log:
	$(call task,python example/client.py -e http://127.0.0.1:8000/chat --enable-logging --log-file logs/chatline_debug.log)

remote-same-origin:
	$(call task,python example/client.py --same-origin)

remote-same-origin-log:
	$(call task,python example/client.py --same-origin --enable-logging --log-file logs/chatline_debug.log)

# Example of using with a different command
# build:
#	$(call task,npm build)

# Prevent Make from treating extra args as targets
%:
	@:
