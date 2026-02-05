"""Textual CSS for the TUI."""

TUI_CSS = """
Screen {
    background: $surface;
}

.panel-title {
    text-style: bold;
    color: $primary;
    padding: 1 0;
    text-align: center;
}

.form-row {
    height: 3;
    margin: 0 1;
    align: center middle;
}

.form-label {
    width: 12;
    text-align: right;
    padding-right: 1;
}

.button-row {
    height: 3;
    margin: 1;
    align: center middle;
}

Button {
    margin: 0 1;
}

ProgressBar {
    margin: 1 2;
}

#stats-panel {
    height: 5;
    border: solid $primary;
    padding: 0 1;
    margin: 0 1;
}

#log-panel {
    height: 100%;
    border: solid $secondary;
    margin: 0 1;
}

#results-table {
    height: 100%;
    margin: 0 1;
}

SearchPanel, ScrapePanel, LoopPanel {
    border: solid $primary;
    margin: 1;
    padding: 1;
    height: auto;
}

TabbedContent {
    height: 1fr;
}

#main-container {
    height: 100%;
}

#left-panel {
    width: 45%;
}

#right-panel {
    width: 55%;
}

RichLog {
    height: 100%;
    scrollbar-gutter: stable;
}

DataTable {
    height: 100%;
}

#consent-dialog {
    width: 70%;
    max-width: 80;
    border: solid $warning;
    padding: 2 3;
    background: $surface;
    align: center middle;
}

.consent-buttons {
    height: 3;
    align: center middle;
    margin-top: 1;
}
"""
