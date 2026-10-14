#!/bin/sh
set -eu
printf '#!/usr/bin/env python3\n' > executable
cat main.py >> executable
chmod +x executable
