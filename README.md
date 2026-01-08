# pyezsh

pyezsh is a small experimental GUI application written in Python using Tkinter.

The purpose of this project is to practice building an application from scratch,
breaking a problem down into smaller pieces, and iterating based on real behavior
and feedback. This project is not intended to be production-ready software.

## Overview

The application demonstrates a simple multi-pane layout:

- A filesystem sidebar for navigating directories and files
- A content viewer that previews directories and text files
- A properties pane showing basic metadata for the selected item
- A telemetry/status area that reflects recent actions

The focus of the project is on structure, event handling, and clarity rather than
feature completeness.

## Features

- Shallow filesystem navigation with a configurable root
- Safe directory traversal with dotfile filtering
- File previews with size and line limits
- Graceful handling of binary or unreadable files
- Clear separation of UI components
- Unit tests for non-GUI logic using pytest

## How to Run

This project is run directly from the source tree.

Using `uv` (recommended):

```bash

uv run ./src/pyezsh/__main__.py

```