<div align="center">

# herdr-agent-index

*Numbered agent rows in the [herdr](https://herdr.dev) sidebar, so `cmd+1..9` jumps where the label says*

[![herdr](https://img.shields.io/badge/herdr-%3E%3D0.9.1-3c873a?style=flat-square)](https://herdr.dev)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-3776ab?style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

[Features](#features) • [Installation](#installation) • [Configuration](#configuration) • [How it works](#how-it-works)

</div>

herdr's `focus_agent` binding jumps to the Nth agent in the sidebar panel, but the rows carry no number, so you count them by eye. This plugin writes each agent's position into a `$aidx` token you can show in the row, and makes the panel sort by those same numbers. The label on a row and the agent that `cmd+N` focuses are always the same.

```text
agents
1 · Backend · working
  Fix the flaky auth test
2 · Docs · done
  Rewrite the install guide
3 · Infra · idle
  Bump the runner image
```

## Features

- **Matches the panel order**: built for `ui.agent_panel_sort = "priority"`. With `grouped`, agents are numbered in `herdr agent list` order; that mode is untested.
- **Stays in sync**: renumbers on agent status changes, focus changes, and pane, tab and workspace moves or closes.
- **Survives restarts**: renumbers at server startup, since herdr drops pane metadata when the server restarts.
- **Manual refresh**: a *Refresh agent numbers* action for the rare case the numbers look off.

## Installation

Requirements: herdr 0.9.1 or later on macOS, and `python3` 3.11 or later on your `PATH`. No other dependencies.

```bash
herdr plugin install eleonov/herdr-agent-index
```

To hack on it, link a local clone instead:

```bash
git clone https://github.com/eleonov/herdr-agent-index.git
herdr plugin link "$PWD/herdr-agent-index"
```

> [!NOTE]
> herdr copies the manifest into its plugin registry. After editing `herdr-plugin.toml`, run `herdr plugin link` again so new events take effect. Changes to `sync.py` apply on the next run.

## Configuration

Show the number in the agent rows and bind `focus_agent` in `~/.config/herdr/config.toml`:

```toml
[keys]
focus_agent = "cmd+1..9"

[ui]
agent_panel_sort = "priority"

[ui.sidebar.agents]
rows = [["$aidx", "workspace", "state_text"], ["terminal_title_stripped"]]
```

Then run `herdr server reload-config`.

<details>
<summary>Ghostty: let <code>cmd+1..9</code> through to herdr</summary>

Ghostty binds `cmd+1..9` to `goto_tab`, and a plain `unbind` does not help: macOS terminals do not encode `cmd` in legacy key encoding, so herdr never sees the press. Send the kitty keyboard protocol sequence instead, for both the physical and the logical key:

```text
keybind = super+digit_1=csi:49;9u
keybind = super+1=csi:49;9u
# ...repeat for 2..9 with codes 50..57
```

Check the result with `ghostty +list-keybinds`.

</details>

## How it works

On every relevant event `sync.py` reads `herdr agent list`, orders the agents the way herdr orders the panel, and reports two tokens per agent pane: `aidx` for display and a zero-padded `aord` for sorting. It then sets an agent view through herdr's socket API (`agent.view.set`) that sorts the panel by `aord`.

The view is the important part. When you look at an agent that has finished, herdr turns it from `done` into `idle` and moves it down the panel, but emits no event, so the plugin cannot renumber at that moment. Returning focus to the terminal window has the same effect. Because the panel sorts by the plugin's own numbers, rows and numbers can lag together until the next event, but they never disagree.

> [!IMPORTANT]
> While the plugin's view is active, herdr disables the sort toggle in the panel header and paints its label in the accent colour. The plugin sets a blank label to keep the header quiet. To change the order, edit `ui.agent_panel_sort` instead.

> [!TIP]
> herdr keeps one agent view at a time, so another plugin that sets a view replaces this one. `herdr plugin disable herdr-agent-index` clears the view and brings back herdr's own sort.
