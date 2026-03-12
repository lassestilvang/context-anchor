from rich.progress import Progress
import time

with Progress() as progress:
    task = progress.add_task("[cyan]Processing...", total=10)
    for i in range(10):
        time.sleep(0.1)
        progress.update(task, advance=1)
