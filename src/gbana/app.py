import asyncio
import functools
import subprocess
import json
import datetime

import dateparser
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Button, RichLog, Rule, Static
from textual.reactive import reactive


class GBanaApp(App):
    CSS_PATH = 'app.tcss'
    BINDINGS = [
        ("w", "wrap", "Toggle line wrap"),
        ("q", "show_query", "Toggle query")
    ]

    rows = reactive([])
    show_query = reactive(False)

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(' '),
            Horizontal(
                Input(id='input_search', placeholder='Search'),
                Input(id='input_from', classes='input_time', placeholder='From'),
                Input(id='input_to', classes='input_time', placeholder='To'),
                Button("Refresh", id='btn_refresh'),
                id='cnt_search_bar',
            ),
            Static(' '),
            RichLog(id='log')
        )
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'btn_refresh':
            self.run_update_worker()

    def on_key(self, event):
        if event.key == "enter":
            self.run_update_worker()

    def run_update_worker(self):
        input = self.query_one('#input_search')
        self.run_worker(self.update_log(input.value), exclusive=True)

    async def update_log(self, text):
        log = self.query_one('#log')
        log.loading = True

        query = self.build_query_string()

        loop = asyncio.get_running_loop()
        output = await loop.run_in_executor(None, functools.partial(self.search, query))

        log.loading = False
        log.clear()

        self.rows = []

        for entry in output:
            if isinstance(entry, str):
                self.rows.append(entry)
            elif 'textPayload' in entry:
                self.rows.append(entry['textPayload'])

        self.update_rows()

    def action_wrap(self):
        log = self.query_one('#log')
        log.wrap = not log.wrap
        self.update_rows()

    def action_show_query(self):
        self.show_query = not self.show_query

    def update_rows(self):
        log = self.query_one('#log')
        log.clear()
        for row in self.rows:
            log.write(row)

    def parse_date(self, string: str) -> datetime.datetime | None:
        return dateparser.parse(
            string,
            languages=['en'],
            locales=['en'],
            settings={
                'RETURN_AS_TIMEZONE_AWARE': True,
                'TO_TIMEZONE': 'UTC',
            }
        )

    def build_query_string(self):
        query = self.query_one('#input_search').value
        from_time = self.query_one('#input_from').value
        to_time = self.query_one('#input_to').value

        query_parts = []

        if query:
            query_parts.append(f'textPayload:"{query}"')

        if from_time:
            from_time = self.parse_date(from_time).isoformat(timespec='seconds')
            query_parts.append(f'timestamp>="{from_time}"')

        if to_time:
            to_time = self.parse_date(to_time).isoformat(timespec='seconds')
            query_parts.append(f'timestamp<="{to_time}"')

        query_string = ' AND '.join(query_parts)

        return query_string

    def search(self, query):
        output = []

        command = [
            'gcloud',
            'logging',
            'read',
            '--limit',
            '500',
            '--format',
            'json',
            f'{query}',
        ]

        if self.show_query:
            output.append(' '.join(command))

        completed_process = subprocess.run(
            command,
            encoding='utf-8',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if completed_process.returncode == 0:
            output.extend(json.loads(completed_process.stdout))
        else:
            output.append(completed_process.stdout)

        return output


if __name__ == "__main__":
    app = GBanaApp()
    app.run()
