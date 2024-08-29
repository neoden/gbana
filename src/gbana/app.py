import asyncio
import functools
import subprocess
import json

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Input, Button, RichLog
from textual.reactive import reactive


class GBanaApp(App):
    CSS_PATH = 'app.tcss'
    BINDINGS = [
        ("w", "wrap", "Toggle line wrap"),
    ]

    rows = reactive([])

    def compose(self) -> ComposeResult:
        yield Vertical(
            Horizontal(
                Input(id='input_search'),
                Button("Refresh", id='btn_refresh'),
                id='cnt_search_bar',
            ),
            RichLog(id='log')
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'btn_refresh':
            input = self.query_one('#input_search')
            self.run_worker(self.update_log(input.value), exclusive=True)

    async def update_log(self, text):
        log = self.query_one('#log')
        log.loading = True

        loop = asyncio.get_running_loop()
        output = await loop.run_in_executor(None, functools.partial(self.search, text))

        log.loading = False
        log.clear()

        self.rows = []

        for entry in output:
            if 'textPayload' in entry:
                self.rows.append(entry['textPayload'])

        self.update_rows()

    def action_wrap(self):
        log = self.query_one('#log')
        log.wrap = not log.wrap
        self.update_rows()

    def update_rows(self):
        log = self.query_one('#log')
        log.clear()
        for row in self.rows:
            log.write(row)

    def search(self, text):
        completed_process = subprocess.run(
            [
                'gcloud',
                'logging',
                'read',
                '--limit',
                '500',
                '--format',
                'json',
                f'"{text}"',
            ],
            encoding='utf-8',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if completed_process.returncode != 0:
            raise Exception('Error while searching logs')

        output = json.loads(completed_process.stdout)

        return output


if __name__ == "__main__":
    app = GBanaApp()
    app.run()
