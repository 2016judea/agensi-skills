#!/bin/bash
# Informational: leftover third-person references to the original owner, memory links, dates.
grep -rnwiE "he|him|his|he's|aidan's" "$@" | grep -viE "the human|the reader" | head -30
grep -rnE "\[\[|20[0-9]{2}-[0-9]{2}-[0-9]{2}|~/Desktop|~/Dropbox|grounded:" "$@" | head -30
