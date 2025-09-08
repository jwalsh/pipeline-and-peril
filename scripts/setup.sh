#!/bin/bash
# Create project structure
mkdir -p docs
mkdir -p assets/tiles
mkdir -p assets/cards
mkdir -p playtesting

# Create placeholder files
touch playtesting/session-notes.md
touch assets/tiles/service-tiles.svg
touch assets/cards/event-cards.svg

echo "Pipeline & Peril project structure created!"
echo "Run 'org-babel-tangle' in Emacs to generate all files."